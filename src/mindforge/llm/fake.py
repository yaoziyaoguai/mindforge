"""离线确定性 provider — 测试与 ``--profile fake`` 用。

为什么需要 FakeProvider
=======================

1. **测试不依赖网络**：M2 起 process 链路必须能在 CI / 本地无 key 环境跑通。
2. **schema 稳定性**：FakeProvider 永远按 prompts/<stage>/manifest.yaml
   声明的 ``expected_output_schema`` 给出合规 JSON，把"接线问题"和
   "模型质量问题"分开。
3. **可重放**：同一份输入永远得到同一份输出（基于 prompt 的 sha1 派生）。

它**不**模拟真实模型的语言能力；只保证数据形状正确。
"""

from __future__ import annotations

import hashlib
import json
import re
import time

from .base import LLMProvider, LLMRequest, LLMResult


def _digest(prompt: str, length: int = 6) -> str:
    return hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:length]


def _extract_var(prompt: str, name: str) -> str | None:
    """从渲染后的 prompt 中抽取 ``<name>: <value>`` 行。"""
    m = re.search(rf"^\s*{re.escape(name)}\s*:\s*(.+)$", prompt, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


class FakeProvider(LLMProvider):
    """根据 stage 返回 schema-conformant 的占位 JSON。"""

    name = "fake"
    type = "fake"

    def generate(self, request: LLMRequest) -> LLMResult:
        start = time.perf_counter()
        stage = request.stage
        digest = _digest(request.prompt)
        title = _extract_var(request.prompt, "title") or "Untitled"
        track_hint = _extract_var(request.prompt, "track") or "agent-runtime"

        if stage == "triage":
            payload = {
                "track": track_hint,
                "value_score": 7,
                "should_process": True,
                "reason": "[fake] schema-only triage stub",
                "topic_keywords": ["fake", "stub", digest],
            }
        elif stage == "distill":
            slug = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-") or f"fake-{digest}"
            payload = {
                "title": title[:80],
                "slug": slug[:60],
                "tags": ["fake", "stub"],
                "confidence": 0.6,
                "source_excerpt": "[fake] excerpt placeholder",
                "ai_summary_bullets": [
                    "[fake] core takeaway A",
                    "[fake] core takeaway B",
                ],
                "ai_inference_bullets": ["[fake] low-confidence inference"],
                "reusable_prompts_or_principles": [
                    "[fake] principle: never trust the fake"
                ],
            }
        elif stage == "link_suggestion":
            payload = {"suggested_links": [], "project_hooks": []}
        elif stage == "review_questions":
            payload = {
                "review_questions": [
                    {
                        "angle": "principle",
                        "question": "[fake] What is the underlying principle?",
                        "expected_points": ["point1", "point2"],
                    },
                    {
                        "angle": "application",
                        "question": "[fake] How would you apply this?",
                        "expected_points": ["apply1", "apply2"],
                    },
                    {
                        "angle": "reflection",
                        "question": "[fake] What did you learn?",
                        "expected_points": ["reflect1", "reflect2"],
                    },
                ]
            }
        elif stage == "action_extraction":
            payload = {"action_items": []}
        else:
            raise ValueError(f"FakeProvider 不识别的 stage: {stage}")

        text = json.dumps(payload, ensure_ascii=False)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return LLMResult(
            text=text,
            tokens_in=max(1, len(request.prompt) // 4),
            tokens_out=max(1, len(text) // 4),
            latency_ms=latency_ms,
            raw={"fake": True, "digest": digest},
        )


__all__ = ["FakeProvider"]
