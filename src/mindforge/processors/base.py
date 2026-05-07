"""processor 通用能力 — 每个 stage 共享的"调 LLM + 解析 JSON + emit llm_call"。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..llm import LLMClient, ProviderError
from ..prompts_runtime import load_prompt, render
from ..run_logger import RunLogger


class StageError(RuntimeError):
    """processor 层错误（prompt 渲染 / LLM / JSON 解析 / schema）。

    ``message`` 会被写进 state.json 与 runs jsonl 的 ``error_message``。
    """


@dataclass(frozen=True)
class StageResult:
    """单个 stage 的对外结果。"""

    stage: str
    parsed: dict[str, Any]
    prompt_version: str            # 形如 "triage@v1"
    model_alias: str
    provider: str
    provider_type: str
    actual_model: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None


def _extract_first_json_object(text: str) -> dict[str, Any]:
    """从 LLM 文本中抽出第一个 ``{...}`` JSON 对象。

    真实 LLM（尤其本地模型）经常会在 JSON 前后裹一段 prose；这里做最小
    容错，避免一遇到 prose 前缀就整批失败。失败抛 ``StageError``。
    """
    text = text.strip()
    # 优先尝试整段 parse
    try:
        v = json.loads(text)
        if isinstance(v, dict):
            return v
    except json.JSONDecodeError:
        pass
    # 退化：找第一个 { 与匹配的 }
    m = re.search(r"\{", text)
    if not m:
        raise StageError("响应中未找到 JSON 对象起始 {")
    start = m.start()
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                snippet = text[start : i + 1]
                try:
                    v = json.loads(snippet)
                except json.JSONDecodeError as e:
                    raise StageError(f"截取的 JSON 仍解析失败：{e}") from e
                if not isinstance(v, dict):
                    raise StageError("解析结果不是 JSON object")
                return v
    raise StageError("响应中 JSON 大括号不闭合")


def run_stage(
    *,
    client: LLMClient,
    logger: RunLogger,
    stage: str,
    prompts_dir: Any,
    prompt_version: str,
    variables: dict[str, Any],
    input_file_hash: str,
    response_format: str | None = "json_object",
) -> StageResult:
    """跑一个 stage：渲染 prompt → 调 LLM → 解析 JSON → emit llm_call。"""
    prompt_text = load_prompt(prompts_dir, stage, prompt_version)
    rendered = render(prompt_text, variables)
    prompt_version_tag = f"{stage}@{prompt_version}"

    try:
        call = client.generate(
            stage=stage,
            prompt=rendered,
            options={"response_format": response_format} if response_format else None,
        )
    except ProviderError as e:
        # 解析路由信息以便日志归因
        resolved = client.resolve_model_for_stage(stage)
        logger.emit(
            "llm_call",
            stage=stage,
            model_alias=resolved.model_alias,
            provider=resolved.provider,
            provider_type=resolved.type,
            actual_model=resolved.actual_model,
            prompt_version=prompt_version_tag,
            input_file_hash=input_file_hash,
            status="failed",
            error_message=str(e),
        )
        raise StageError(f"LLM 调用失败：{e}") from e

    try:
        parsed = _extract_first_json_object(call.result.text)
    except StageError as e:
        logger.emit(
            "llm_call",
            stage=stage,
            model_alias=call.resolved.model_alias,
            provider=call.resolved.provider,
            provider_type=call.resolved.type,
            actual_model=call.resolved.actual_model,
            prompt_version=prompt_version_tag,
            input_file_hash=input_file_hash,
            status="failed",
            error_message=str(e),
            tokens_in=call.result.tokens_in,
            tokens_out=call.result.tokens_out,
            latency_ms=call.result.latency_ms,
        )
        raise

    logger.emit(
        "llm_call",
        stage=stage,
        model_alias=call.resolved.model_alias,
        provider=call.resolved.provider,
        provider_type=call.resolved.type,
        actual_model=call.resolved.actual_model,
        prompt_version=prompt_version_tag,
        input_file_hash=input_file_hash,
        status="ok",
        tokens_in=call.result.tokens_in,
        tokens_out=call.result.tokens_out,
        latency_ms=call.result.latency_ms,
    )

    return StageResult(
        stage=stage,
        parsed=parsed,
        prompt_version=prompt_version_tag,
        model_alias=call.resolved.model_alias,
        provider=call.resolved.provider,
        provider_type=call.resolved.type,
        actual_model=call.resolved.actual_model,
        tokens_in=call.result.tokens_in,
        tokens_out=call.result.tokens_out,
        latency_ms=call.result.latency_ms,
    )


def utc_now() -> datetime:
    return datetime.now()


__all__ = ["StageError", "StageResult", "run_stage", "utc_now"]
