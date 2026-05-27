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


# 停用词集合 — 对 ASCII 关键词和 CJK bigram 都做过滤
_STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are", "was",
    "not", "you", "all", "can", "has", "had", "its", "use",
}
# CJK bigram 停用词 — 高频但无语义的 2-gram，不应作为检索关键词
_CJK_STOP_BIGRAMS = {
    "这是", "一个", "可以", "我们", "他们", "不是", "什么", "怎么",
    "如何", "这个", "那个", "其中", "所有", "每个", "任何", "其他",
    "对于", "关于", "以及", "或者", "但是", "因为", "所以", "因此",
    "如果", "虽然", "而且", "然后", "之后", "之前", "已经", "还有",
    "没有", "是否", "需要", "应该", "可能", "能够", "不能", "不会",
    "进行", "使用", "通过", "根据", "作为", "主要", "一些", "一种",
    "不同", "一样", "包括", "这些", "那些", "问题", "情况", "方式",
    "部分", "内容", "结果", "过程", "其中", "非常", "比较",
}


def _extract_keywords_from_text(
    text: str, max_keywords: int = 8, *, source_label: str = ""
) -> list[str]:
    """从任意文本中提取关键词（确定性、零网络、零 LLM）。

    中文学习型说明：这是 ``_extract_keywords(title)`` 的通用版本，
    对 title 和 raw_text 都适用。提取规则完全一致：
    - ASCII 单词（>=3 字符，非停用词）→ lowercase keywords
    - CJK 连续片段 → 按 2-gram 切分，过滤无语义高频 bigram
    - 去重，限制数量
    """
    if not text:
        return []

    keywords: list[str] = []
    # ASCII words >= 3 chars, filtered for common stop words
    ascii_words = re.findall(r"[A-Za-z]{3,}", text)
    for w in ascii_words:
        low = w.lower()
        if low not in _STOP_WORDS:
            keywords.append(low)

    # CJK bigrams as keywords, filtered for non-semantic high-frequency bigrams
    cjk_chars = re.findall(r"[一-鿿぀-ゟ゠-ヿ가-힯]+", text)
    for segment in cjk_chars:
        for i in range(0, len(segment) - 1, 2):
            bigram = segment[i:i + 2]
            if len(bigram) == 2 and bigram not in _CJK_STOP_BIGRAMS:
                keywords.append(bigram)

    # Deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            deduped.append(kw)

    return deduped[:max_keywords]


def _extract_keywords(title: str, max_keywords: int = 8) -> list[str]:
    """从 title 中提取有意义的关键词作为 fake tags/summary 的素材。

    中文学习型说明：fake provider 的 distill 输出被 BM25 索引用于召回。
    如果所有 body 字段都是 ``[fake]`` 占位符，BM25 只靠 title 匹配，
    recall hit rate 会很低。这个函数从 title 和 prompt 中的 raw_text
    提取真实关键词注入到 tags 和 summary bullets 中，让 fake dogfood
    的 recall 更接近真实场景。

    规则（确定性、零网络、零 LLM）：
    - ASCII 单词（>=3 字符，非停用词）→ lowercase keywords
    - CJK 连续片段 → 按 2-gram 切分作为关键词，过滤无语义高频 bigram
    - 去重，限制数量
    """
    if not title:
        return ["fake"]

    result = _extract_keywords_from_text(title, max_keywords, source_label="title")
    if not result:
        return ["fake"]
    return result


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
            # 从 title 提取关键词（优先级更高，排在前面）
            title_keywords = _extract_keywords(title)
            # 从 prompt 全文提取关键词 — prompt 中包含 raw_text（真实原文
            # 最多 12000 字符），这比 title 提供更丰富的检索素材。
            # 中文说明：fake provider 的 distill output 会被 BM25 索引，
            # 如果只有 title 关键词，recall hit rate 极低（~33%）。
            # prompt 中已包含完整原文 raw_text，从这里提取关键词
            # 不需要 LLM、不需要网络、不需要 secrets。
            prompt_keywords = _extract_keywords_from_text(
                request.prompt, max_keywords=20, source_label="prompt"
            )
            # 合并：title 关键词优先 + prompt 中不在 title 里的补充关键词
            title_lower = {k.lower() for k in title_keywords}
            combined = list(title_keywords)
            for kw in prompt_keywords:
                if kw.lower() not in title_lower:
                    combined.append(kw)
                    title_lower.add(kw.lower())
            keywords = combined[:15] if len(combined) >= 15 else combined
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
