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
    ) -> None:
        self.client = client
        self.logger = logger
        self.prompts_dir = prompts_dir
        self.prompt_versions = prompt_versions
        self.triage_threshold = triage_threshold
        self.learning_tracks_text = learning_tracks_text

    # --------------------------------------------------------------------- run
    def run(self, doc: SourceDocument) -> PipelineOutcome:
        outcome = PipelineOutcome(status="failed")
        ifh = doc.content_hash

        # ------------------------------------------------------------- triage
        try:
            triage = run_stage(
                client=self.client,
                logger=self.logger,
                stage="triage",
                prompts_dir=self.prompts_dir,
                prompt_version=self.prompt_versions.for_stage("triage"),
                input_file_hash=ifh,
                variables={
                    "title": doc.title or "",
                    "source_type": doc.source_type,
                    "source_url": doc.source_url or "",
                    "tags": ", ".join(doc.tags),
                    "tracks_yaml": self.learning_tracks_text,
                    "excerpt": _excerpt(doc.raw_text, 4000),
                },
            )
            outcome.triage = triage
            self._record_stage(outcome, triage, status="ok")
        except StageError as e:
            outcome.error_message = str(e)
            outcome.error_stage = "triage"
            return outcome

        track = str(triage.parsed.get("track") or "unrouted")
        value_score = int(triage.parsed.get("value_score") or 0)
        should_process = bool(triage.parsed.get("should_process"))
        if not should_process or value_score < self.triage_threshold:
            outcome.status = "skipped"
            outcome.skip_reason = (
                f"triage value_score={value_score} should_process={should_process}"
            )
            return outcome

        # ------------------------------------------------------------ distill
        try:
            distill = run_stage(
                client=self.client,
                logger=self.logger,
                stage="distill",
                prompts_dir=self.prompts_dir,
                prompt_version=self.prompt_versions.for_stage("distill"),
                input_file_hash=ifh,
                variables={
                    "title": doc.title or "",
                    "source_type": doc.source_type,
                    "source_url": doc.source_url or "",
                    "track": track,
                    "output_focus": "",
                    "value_score": str(value_score),
                    "topic_keywords": ", ".join(triage.parsed.get("topic_keywords") or []),
                    "raw_text": _excerpt(doc.raw_text, 12000),
                },
            )
            outcome.distill = distill
            self._record_stage(outcome, distill, status="ok")
        except StageError as e:
            outcome.error_message = str(e)
            outcome.error_stage = "distill"
            return outcome

        ai_summary = distill.parsed.get("ai_summary_bullets") or []

        # ----------------------------------------------------- link_suggestion
        try:
            ls = run_stage(
                client=self.client,
                logger=self.logger,
                stage="link_suggestion",
                prompts_dir=self.prompts_dir,
                prompt_version=self.prompt_versions.for_stage("link_suggestion"),
                input_file_hash=ifh,
                variables={
                    "card_title": distill.parsed.get("title") or "",
                    "track": track,
                    "tags": ", ".join(distill.parsed.get("tags") or []),
                    "ai_summary_bullets": "\n".join(f"- {b}" for b in ai_summary),
                    "candidate_cards": "",
                    "candidate_projects": "",
                },
            )
            outcome.link_suggestion = ls
            self._record_stage(outcome, ls, status="ok")
        except StageError as e:
            outcome.error_message = str(e)
            outcome.error_stage = "link_suggestion"
            return outcome

        # ---------------------------------------------------- review_questions
        try:
            rq = run_stage(
                client=self.client,
                logger=self.logger,
                stage="review_questions",
                prompts_dir=self.prompts_dir,
                prompt_version=self.prompt_versions.for_stage("review_questions"),
                input_file_hash=ifh,
                variables={
                    "card_title": distill.parsed.get("title") or "",
                    "track": track,
                    "ai_summary_bullets": "\n".join(f"- {b}" for b in ai_summary),
                    "ai_inference_bullets": "\n".join(
                        f"- {b}" for b in (distill.parsed.get("ai_inference_bullets") or [])
                    ),
                    "reusable_prompts_or_principles": "\n".join(
                        f"- {b}" for b in (distill.parsed.get("reusable_prompts_or_principles") or [])
                    ),
                    "source_excerpt": distill.parsed.get("source_excerpt") or "",
                },
            )
            outcome.review_questions = rq
            self._record_stage(outcome, rq, status="ok")
        except StageError as e:
            outcome.error_message = str(e)
            outcome.error_stage = "review_questions"
            return outcome

        # --------------------------------------------------- action_extraction
        try:
            ae = run_stage(
                client=self.client,
                logger=self.logger,
                stage="action_extraction",
                prompts_dir=self.prompts_dir,
                prompt_version=self.prompt_versions.for_stage("action_extraction"),
                input_file_hash=ifh,
                variables={
                    "card_title": distill.parsed.get("title") or "",
                    "track": track,
                    "ai_summary_bullets": "\n".join(f"- {b}" for b in ai_summary),
                    "reusable_prompts_or_principles": "\n".join(
                        f"- {b}" for b in (distill.parsed.get("reusable_prompts_or_principles") or [])
                    ),
                    "candidate_projects": "",
                },
            )
            outcome.action_extraction = ae
            self._record_stage(outcome, ae, status="ok")
        except StageError as e:
            outcome.error_message = str(e)
            outcome.error_stage = "action_extraction"
            return outcome

        # ---------------------------------------------- 组装 card payload
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
    def _record_stage(self, outcome: PipelineOutcome, sr: StageResult, *, status: str) -> None:
        outcome.stages_meta[sr.stage] = {
            "model_alias": sr.model_alias,
            "provider": sr.provider,
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
    return {
        "strategy_id": "five_stage",
        "strategy_version": "0.10.0",
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
