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


def _extract_keywords(title: str, max_keywords: int = 8) -> list[str]:
    """从 title 中提取有意义的关键词作为 fake tags/summary 的素材。

    中文学习型说明：fake provider 的 distill 输出被 BM25 索引用于召回。
    如果所有 body 字段都是 ``[fake]`` 占位符，BM25 只靠 title 匹配，
    recall hit rate 会很低。这个函数从 title 中提取真实关键词注入到
    tags 和 summary bullets 中，让 fake dogfood 的 recall 更接近真实场景。

    规则（确定性、零网络、零 LLM）：
    - ASCII 单词（>=3 字符，非停用词）→ lowercase keywords
    - CJK 连续片段 → 按 2-gram 切分作为关键词
    - 去重，限制数量
    """
    if not title:
        return ["fake"]

    keywords: list[str] = []
    # ASCII words >= 3 chars, filtered for common stop words
    ascii_words = re.findall(r"[A-Za-z]{3,}", title)
    STOP = {
        "the", "and", "for", "with", "this", "that", "from", "are", "was",
        "not", "you", "all", "can", "has", "had", "its", "use",
    }
    for w in ascii_words:
        low = w.lower()
        if low not in STOP:
            keywords.append(low)

    # CJK bigrams as keywords
    cjk_chars = re.findall(r"[一-鿿぀-ゟ゠-ヿ가-힯]+", title)
    for segment in cjk_chars:
        for i in range(0, len(segment) - 1, 2):
            bigram = segment[i:i + 2]
            if len(bigram) == 2:
                keywords.append(bigram)

    # Deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            deduped.append(kw)

    if not deduped:
        return ["fake"]

    return deduped[:max_keywords]


def _extract_var(prompt: str, name: str) -> str | None:
    """从渲染后的 prompt 中抽取变量值。

    中文学习型说明：fake provider 是本地 smoke 和 CI 的离线替身，不应
    模拟真实模型能力，但它应该让 demo 产物看起来像真实产品。早期只识别
    ``title: foo`` 这种测试短格式；真实 prompt 模板会把变量渲染进
    ``- `foo` — 素材标题`` 这样的说明行，导致 demo 卡片标题退化成
    ``Untitled``。这里只补最小解析规则，仍然不读取原文、不联网、不调用
    真实 LLM。
    """
    m = re.search(rf"^\s*{re.escape(name)}\s*:\s*(.+)$", prompt, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()

    rendered_labels = {
        "title": "素材标题",
        "track": "Triager 已分流",
    }
    label = rendered_labels.get(name)
    if label:
        m = re.search(
            rf"^\s*-\s*`([^`]*)`\s+—\s*{re.escape(label)}",
            prompt,
            flags=re.MULTILINE,
        )
        if m:
            value = m.group(1).strip()
            return value or None
    return None


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
            keywords = _extract_keywords(title)
            payload = {
                "track": track_hint,
                "value_score": 7,
                "should_process": True,
                "reason": "[fake] schema-only triage stub",
                "topic_keywords": keywords,
            }
        elif stage == "distill":
            slug = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-") or f"fake-{digest}"
            keywords = _extract_keywords(title)
            payload = {
                "title": title[:80],
                "slug": slug[:60],
                "tags": keywords,
                "confidence": 0.6,
                "source_excerpt": f"[fake] excerpt from source containing: {', '.join(keywords[:4])}",
                "ai_summary_bullets": [
                    f"[fake] Key insight about {kw}" for kw in keywords[:3]
                ] or ["[fake] core takeaway"],
                "ai_inference_bullets": [
                    f"[fake] inference related to {keywords[0]}" if keywords else "[fake] low-confidence inference"
                ],
                "reusable_prompts_or_principles": [
                    f"[fake] principle derived from {kw}" for kw in keywords[:2]
                ] or ["[fake] principle: never trust the fake"],
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
        elif stage == "wiki_synthesis":
            payload = {
                "overview": "[fake] 基于提供的 approved cards 生成的知识总览。",
                "sections": [
                    {
                        "title": "[fake] Section 1",
                        "body": "[fake] section body with Markdown content.",
                        "card_ids": [],
                    },
                    {
                        "title": "[fake] Section 2",
                        "body": "[fake] another section body.",
                        "card_ids": [],
                    },
                ],
                "open_questions": [
                    {
                        "question": "[fake] 待确认的问题？",
                        "card_ids": [],
                    }
                ],
            }
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
