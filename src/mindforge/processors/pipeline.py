"""pipeline — 把五个 stage 串成一条对单文件的 process 链。

调用顺序（v0.1，固定）：

1. ``triage``               ← decides track / value_score / should_process
2. （可能 short-circuit 为 status="skipped"）
3. ``distill``              ← 主体内容
4. ``link_suggestion``      ← 双链与 project_hooks 候选
5. ``review_questions``     ← 复习题
6. ``action_extraction``    ← 行动项
7. writer 渲染 + 落盘 Card

约定
----

- 任一 stage 抛 :class:`StageError` → 整条 pipeline 终止，整个 item 标 failed；
  已 emit 的 ``llm_call`` 事件保留为审计证据。
- triage short-circuit 不算失败；item.status = "skipped"，不写 Card。
- 本 pipeline **不知道** state.json 与 cli 的存在；调用方负责把 :class:`PipelineOutcome`
  反映到 checkpoint 与日志。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..llm import LLMClient
from ..run_logger import RunLogger
from ..sources.base import SourceDocument
from .base import StageError, StageResult, run_stage


@dataclass
class PipelineOutcome:
    """五 stage + 可选 short-circuit 的总结。"""

    status: str                                  # "processed" | "skipped" | "failed"
    triage: StageResult | None = None
    distill: StageResult | None = None
    link_suggestion: StageResult | None = None
    review_questions: StageResult | None = None
    action_extraction: StageResult | None = None
    error_message: str | None = None
    error_stage: str | None = None
    skip_reason: str | None = None
    card_payload: dict[str, Any] | None = None   # 已组装好的 card 字典；交给 writer
    stages_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    """``stage -> {model_alias, provider, actual_model, prompt_version, status, ...}``，
    供 checkpoint 写入 ``ItemState.stages``。"""


class Pipeline:
    """单文件多 stage 编排器。"""

    def __init__(
        self,
        *,
        client: LLMClient,
        logger: RunLogger,
        prompts_dir: Any,
        prompt_versions: Any,        # PromptVersions
        triage_threshold: int,
        learning_tracks_text: str,
        bypass_triage_gate: bool = False,
    ) -> None:
        self.client = client
        self.logger = logger
        self.prompts_dir = prompts_dir
        self.prompt_versions = prompt_versions
        self.triage_threshold = triage_threshold
        self.bypass_triage_gate = bypass_triage_gate
        self.learning_tracks_text = learning_tracks_text

    # --------------------------------------------------------------------- run
    def run(self, doc: SourceDocument) -> PipelineOutcome:
        outcome = PipelineOutcome(status="failed")
        ifh = doc.content_hash

        triage = self._run_stage_or_fail(outcome, "triage", ifh, _triage_vars(doc, self.learning_tracks_text))
        if triage is None:
            return outcome

        track = str(triage.parsed.get("track") or "unrouted")
        value_score = int(triage.parsed.get("value_score") or 0)
        should_process = bool(triage.parsed.get("should_process"))
        if (
            not self.bypass_triage_gate
            and (not should_process or value_score < self.triage_threshold)
        ):
            outcome.status = "skipped"
            outcome.skip_reason = (
                f"triage value_score={value_score} threshold={self.triage_threshold} "
                f"should_process={should_process}"
            )
            return outcome

        distill = self._run_stage_or_fail(
            outcome,
            "distill",
            ifh,
            _distill_vars(doc, triage=triage, track=track, value_score=value_score),
        )
        if distill is None:
            return outcome

        ai_summary = distill.parsed.get("ai_summary_bullets") or []

        ls = self._run_stage_or_fail(
            outcome,
            "link_suggestion",
            ifh,
            _link_suggestion_vars(distill=distill, track=track, ai_summary=ai_summary),
        )
        if ls is None:
            return outcome

        rq = self._run_stage_or_fail(
            outcome,
            "review_questions",
            ifh,
            _review_question_vars(distill=distill, track=track, ai_summary=ai_summary),
        )
        if rq is None:
            return outcome

        ae = self._run_stage_or_fail(
            outcome,
            "action_extraction",
            ifh,
            _action_extraction_vars(distill=distill, track=track, ai_summary=ai_summary),
        )
        if ae is None:
            return outcome

        outcome.card_payload = _build_card_payload(
            doc=doc,
            track=track,
            value_score=value_score,
            distill=distill.parsed,
            link_suggestion=ls.parsed,
            review_questions=rq.parsed,
            action_extraction=ae.parsed,
        )
        outcome.status = "processed"
        return outcome

    # ------------------------------------------------------- internal helpers
    def _run_stage_or_fail(
        self,
        outcome: PipelineOutcome,
        stage: str,
        input_file_hash: str,
        variables: dict[str, Any],
    ) -> StageResult | None:
        try:
            result = run_stage(
                client=self.client,
                logger=self.logger,
                stage=stage,
                prompts_dir=self.prompts_dir,
                prompt_version=self.prompt_versions.for_stage(stage),
                input_file_hash=input_file_hash,
                variables=variables,
            )
            setattr(outcome, stage, result)
            self._record_stage(outcome, result, status="ok")
            return result
        except StageError as e:
            outcome.error_message = str(e)
            outcome.error_stage = stage
            return None

    def _record_stage(self, outcome: PipelineOutcome, sr: StageResult, *, status: str) -> None:
        outcome.stages_meta[sr.stage] = {
            "model_alias": sr.model_alias,
            "provider": sr.provider,
            "type": sr.provider_type,
            "actual_model": sr.actual_model,
            "prompt_version": sr.prompt_version,
            "status": status,
            "tokens_in": sr.tokens_in,
            "tokens_out": sr.tokens_out,
            "latency_ms": sr.latency_ms,
        }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _excerpt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...truncated for prompt budget...]"


def _bullet_lines(items: Any) -> str:
    return "\n".join(f"- {item}" for item in (items or []))


def _triage_vars(doc: SourceDocument, learning_tracks_text: str) -> dict[str, str]:
    return {
        "title": doc.title or "",
        "source_type": doc.source_type,
        "source_url": doc.source_url or "",
        "tags": ", ".join(doc.tags),
        "tracks_yaml": learning_tracks_text,
        "excerpt": _excerpt(doc.raw_text, 4000),
    }


def _distill_vars(
    doc: SourceDocument,
    *,
    triage: StageResult,
    track: str,
    value_score: int,
) -> dict[str, str]:
    return {
        "title": doc.title or "",
        "source_type": doc.source_type,
        "source_url": doc.source_url or "",
        "track": track,
        "output_focus": "",
        "value_score": str(value_score),
        "topic_keywords": ", ".join(triage.parsed.get("topic_keywords") or []),
        "raw_text": _excerpt(doc.raw_text, 12000),
    }


def _link_suggestion_vars(
    *,
    distill: StageResult,
    track: str,
    ai_summary: Any,
) -> dict[str, str]:
    return {
        "card_title": distill.parsed.get("title") or "",
        "track": track,
        "tags": ", ".join(distill.parsed.get("tags") or []),
        "ai_summary_bullets": _bullet_lines(ai_summary),
        "candidate_cards": "",
        "candidate_projects": "",
    }


def _review_question_vars(
    *,
    distill: StageResult,
    track: str,
    ai_summary: Any,
) -> dict[str, str]:
    return {
        "card_title": distill.parsed.get("title") or "",
        "track": track,
        "ai_summary_bullets": _bullet_lines(ai_summary),
        "ai_inference_bullets": _bullet_lines(distill.parsed.get("ai_inference_bullets")),
        "reusable_prompts_or_principles": _bullet_lines(
            distill.parsed.get("reusable_prompts_or_principles")
        ),
        "source_excerpt": distill.parsed.get("source_excerpt") or "",
    }


def _action_extraction_vars(
    *,
    distill: StageResult,
    track: str,
    ai_summary: Any,
) -> dict[str, str]:
    return {
        "card_title": distill.parsed.get("title") or "",
        "track": track,
        "ai_summary_bullets": _bullet_lines(ai_summary),
        "reusable_prompts_or_principles": _bullet_lines(
            distill.parsed.get("reusable_prompts_or_principles")
        ),
        "candidate_projects": "",
    }


def _build_card_payload(
    *,
    doc: SourceDocument,
    track: str,
    value_score: int,
    distill: dict[str, Any],
    link_suggestion: dict[str, Any],
    review_questions: dict[str, Any],
    action_extraction: dict[str, Any],
) -> dict[str, Any]:
    """组装五段策略的 ``ai_draft`` envelope。

    v0.10 Slice 5 起，本函数返回**公共 envelope**而非历史扁平
    ``{"card": {...}}``。设计意图：

    - 让 writer / presenter / approval 只需理解 envelope 顶层 + 公共
      ``review_hints``，**不需要**理解 five_stage 17 字段细节；
    - 让 ``DefaultKnowledgeCardStrategy`` 与 ``five_stage`` 共用同一条
      下游链路；
    - 为未来 v0.11 StrategyRegistry / v0.12 custom strategy 留出向后
      兼容入口（任何新策略只需产出同形 envelope）。

    五段卡片 17 字段全部装入 ``structured_payload.card``；这条嵌套路
    径是 writer 模板与 envelope 的稳定 contact point。
    """
    card = {
        "id": distill.get("slug") or "untitled",
        "title": distill.get("title") or doc.title or "Untitled",
        "track": track,
        "projects": [],
        "tags": distill.get("tags") or [],
        "value_score": value_score,
        "confidence": distill.get("confidence", 0.0),
        "source_excerpt": distill.get("source_excerpt") or "",
        "ai_summary_bullets": distill.get("ai_summary_bullets") or [],
        "ai_inference_bullets": distill.get("ai_inference_bullets") or [],
        "reusable_prompts_or_principles": distill.get("reusable_prompts_or_principles") or [],
        "project_hooks": link_suggestion.get("project_hooks") or [],
        "review_questions": review_questions.get("review_questions") or [],
        "action_items": action_extraction.get("action_items") or [],
        "suggested_links": link_suggestion.get("suggested_links") or [],
    }
    summary_bullets = card["ai_summary_bullets"]
    one_line = (
        str(summary_bullets[0]) if summary_bullets else (distill.get("source_excerpt") or "")
    )
    # 中文学习型注释：这里写入用户可见 canonical strategy id。五段 pipeline
    # 仍是内部实现细节，但新卡 provenance 应回答“使用了 Knowledge Card
    # Strategy”，而不是把 five_stage 这个历史实现名继续暴露成产品能力。
    # 使用函数内 lazy import 是为了打破 strategies.knowledge_card →
    # processors.pipeline 的循环 import。
    from ..strategies import knowledge_card as _knowledge_card_meta

    return {
        "strategy_id": _knowledge_card_meta.STRATEGY_ID,
        "strategy_version": _knowledge_card_meta.STRATEGY_VERSION,
        "schema_version": "1",
        "status": "ai_draft",
        "source_evidence": {
            "source_id": doc.source_id,
            "source_type": doc.source_type,
            "content_hash": doc.content_hash,
            "source_path": doc.source_path,
            "adapter_name": doc.adapter_name or "",
        },
        "structured_payload": {"card": card},
        "review_hints": {
            "title": card["title"],
            "one_line": one_line,
        },
    }


__all__ = ["Pipeline", "PipelineOutcome"]
