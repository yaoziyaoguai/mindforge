"""Main Wiki service —— 从 approved cards 确定性地生成派生 Wiki 视图。

中文学习型说明：Wiki 是 approved cards 的只读派生视图，不是 source、不是
审批入口、不是唯一知识源。rebuild 总是从 approved card 集合重新生成，使用
确定性模板（不调 LLM）。provenance 由代码自动追加，不会被 LLM 删除。

Wiki 文件放在 ``30-Wiki/Main-Wiki.md``，与 cards(20-Knowledge-Cards) 分开。
写入使用 atomic write（先写 .tmp 再 replace），失败时旧 Wiki 保持不变。
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .cards import CardSummary, extract_section, iter_cards, read_card_body
from .config import MindForgeConfig
from .wiki.wiki_quality import (
    compute_coverage,
    compute_faithfulness_score,
    compute_knowledge_gaps,
    detect_stale_sections,
)


@dataclass(frozen=True)
class WikiRebuildResult:
    wiki_path: str
    included_cards: int
    excluded_trashed: int
    last_rebuilt_at: str
    card_count: int


@dataclass(frozen=True)
class WikiStatus:
    wiki_path: str
    exists: bool
    last_rebuilt_at: str | None = None
    approved_card_count: int = 0
    wiki_card_count: int = 0
    is_stale: bool = False
    new_approved_count: int = 0


class WikiError(ValueError):
    """Wiki 操作失败；message 可安全返回给 Web/CLI。"""


def _wiki_error_message(english: str, chinese: str) -> str:
    """组合用户可见双语 Wiki 错误，不引入完整 i18n 系统。

    中文学习型说明：WikiError 会被 CLI/Web 直接展示。这里保持单一 message
    contract，只补英文可理解句子，避免为了小范围错误文案制造新的翻译层。
    """

    return f"{english} / {chinese}"


def _wiki_root(cfg: MindForgeConfig) -> Path:
    return cfg.vault.root / "30-Wiki"


def _wiki_path(cfg: MindForgeConfig) -> Path:
    return _wiki_root(cfg) / "Main-Wiki.md"


def _generate_quality_report_appendix(
    wiki_content: str,
    approved_cards: list[CardSummary],
) -> str:
    """从已生成的 Wiki 内容 + approved cards 生成 quality report appendix。

    解析 WIKI_SECTION_START 标记提取 used card ids，计算 coverage、
    faithfulness、staleness，生成 markdown appendix + 嵌入式 JSON。
    """
    import json as _json

    # 解析 used card IDs
    used_ids: list[str] = []
    section_card_map: dict[str, list[str]] = {}
    section_title_map: dict[int, str] = {}
    sec_idx = 0

    for line in wiki_content.split("\n"):
        m = re.search(r"<!-- WIKI_SECTION_START card(_ids)?=(.+?) -->", line)
        if m:
            ids_str = m.group(2)
            ids = [cid.strip() for cid in ids_str.split(",") if cid.strip()]
            used_ids.extend(ids)
            sec_title = f"Section {sec_idx + 1}"
            section_card_map[sec_title] = ids
            # 尝试从下一行读取 section 标题
            section_title_map[sec_idx] = sec_title
            sec_idx += 1
        # 检测 heading 作为 section title
        if sec_idx > 0 and line.startswith("### "):
            title = line[4:].strip()
            section_title_map[sec_idx - 1] = title

    # 全部 approved card IDs
    all_approved_ids = [c.id for c in approved_cards if c.id]

    # 去重 used_ids
    used_ids_unique = list(dict.fromkeys(used_ids))

    # Reason map（简单版）
    reason_map: dict[str, str] = {}
    for cid in all_approved_ids:
        if cid not in used_ids_unique:
            reason_map[cid] = "Not included in any Wiki section"

    # Coverage
    unused_ids, reasons = compute_coverage(all_approved_ids, used_ids_unique, reason_map)

    # Faithfulness per section
    faithfulness_scores: dict[str, float] = {}
    faithfulness_issues: list[str] = []
    for sec_title, card_ids in section_card_map.items():
        bodies: dict[str, str] = {}
        for cid in card_ids:
            card = next((c for c in approved_cards if c.id == cid), None)
            if card:
                try:
                    bodies[cid] = read_card_body(card.path) or ""
                except Exception:
                    bodies[cid] = ""
        if bodies:
            # 从 wiki content 提取 section body text
            score = _compute_section_faithfulness(wiki_content, sec_title, bodies)
            faithfulness_scores[sec_title] = score
            if score < 0.3:
                faithfulness_issues.append(f"{sec_title}: faithfulness {score:.2f}")
        else:
            faithfulness_scores[sec_title] = 1.0

    # Staleness
    topic_keywords = _derive_topic_keywords(section_card_map, approved_cards)
    stale = detect_stale_sections(
        [type("_SR", (), {"section_title": t, "card_ids": tuple(ids), "relevance": "primary"})()
         for t, ids in section_card_map.items()],
        new_card_titles={c.title or "" for c in approved_cards},
        topic_keywords=topic_keywords,
    )

    # Knowledge gaps
    used_tags: set[str] = set()
    for cid in used_ids_unique:
        card = next((c for c in approved_cards if c.id == cid), None)
        if card:
            used_tags.update(card.tags)
    gaps = compute_knowledge_gaps(
        list(section_title_map.values()),
        used_tags,
        topic_keywords,
    )

    # 构造 Quality Report
    cov_pct = round((len(used_ids_unique) / max(len(all_approved_ids), 1)) * 100)
    faith_avg = (
        round(sum(faithfulness_scores.values()) / max(len(faithfulness_scores), 1), 2)
        if faithfulness_scores else 0
    )

    quality_json = {
        "coverage": {
            "used": len(used_ids_unique),
            "unused": len(unused_ids),
            "total": len(all_approved_ids),
            "rate": round(len(used_ids_unique) / max(len(all_approved_ids), 1), 2),
        },
        "unused_cards": [
            {"id": cid, "title": next((c.title for c in approved_cards if c.id == cid), ""), "reason": reasons.get(cid, "")}
            for cid in unused_ids
        ],
        "used_cards": used_ids_unique,
        "faithfulness": {
            "average": faith_avg,
            "by_section": faithfulness_scores,
        },
        "faithfulness_issues": faithfulness_issues,
        "stale_sections": stale,
        "knowledge_gaps": gaps,
        "conflicting_claims": [],
        "section_count": len(section_card_map),
    }

    json_str = _json.dumps(quality_json, ensure_ascii=False, indent=2)

    appendix = (
        f"\n\n## Wiki Quality Report\n\n"
        f"<!-- WIKI_QUALITY_REPORT_START -->\n"
        f"- **Coverage**: {len(used_ids_unique)}/{len(all_approved_ids)} approved cards used ({cov_pct}%)\n"
        f"- **Faithfulness**: avg {faith_avg}\n"
    )
    if unused_ids:
        appendix += f"- **Unused cards**: {len(unused_ids)} cards not referenced in any section\n"
    if stale:
        appendix += f"- **Stale sections**: {len(stale)} sections may need review\n"
    if gaps:
        appendix += f"- **Knowledge gaps**: {len(gaps)} topics not covered\n"
    if faithfulness_issues:
        appendix += f"- **Faithfulness issues**: {len(faithfulness_issues)} sections below threshold\n"
    appendix += (
        f"<!-- WIKI_QUALITY_REPORT_END -->\n"
        f"\n<!-- WIKI_QUALITY_JSON\n{json_str}\n-->"
    )

    return appendix


def _compute_section_faithfulness(
    wiki_content: str,
    section_title: str,
    card_bodies: dict[str, str],
) -> float:
    """计算单个 wiki section 的 faithfulness score。"""
    # 从 wiki content 提取该 section 的 body text
    pattern = rf"### {re.escape(section_title)}\n(.*?)(?=\n### |\n<!-- WIKI_SECTION_END|\Z)"
    m = re.search(pattern, wiki_content, re.DOTALL)
    if not m:
        return 1.0
    section_text = m.group(1).strip()
    if not section_text:
        return 1.0
    return compute_faithfulness_score(section_text, card_bodies)


def _derive_topic_keywords(
    section_card_map: dict[str, list[str]],
    approved_cards: list[CardSummary],
) -> dict[str, set[str]]:
    """从 section → card 映射中推导 topic keywords。"""
    keywords: dict[str, set[str]] = {}
    for sec_title, card_ids in section_card_map.items():
        kw_set: set[str] = set()
        for cid in card_ids:
            card = next((c for c in approved_cards if c.id == cid), None)
            if card:
                if card.title:
                    for word in card.title.lower().split():
                        word = word.strip(".,;:!?()[]{}'\"")
                        if len(word) > 2:
                            kw_set.add(word)
                for tag in card.tags:
                    kw_set.add(tag.lower())
        if kw_set:
            keywords[sec_title] = kw_set
    return keywords


def rebuild_main_wiki(cfg: MindForgeConfig) -> WikiRebuildResult:
    """(Deprecated) 从 approved cards 重建 Main Wiki（deterministic template，不调 LLM）。"""
    raise WikiError("rebuild_main_wiki is deprecated in v0.5. Wiki is now a runtime View, not a persisted Markdown document.")

def read_main_wiki(cfg: MindForgeConfig) -> str | None:
    """读 Main Wiki 内容。不存在时返回 None。"""
    path = _wiki_path(cfg)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def get_wiki_status(cfg: MindForgeConfig) -> WikiStatus:
    """返回 Main Wiki 状态摘要。"""
    path = _wiki_path(cfg)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved_count = sum(1 for c in scan.cards if c.status == "human_approved")

    if not path.is_file():
        return WikiStatus(
            wiki_path=str(path),
            exists=False,
            approved_card_count=approved_count,
        )

    # 从 Wiki 内容中提取 last_rebuilt_at 和 card_count
    text = path.read_text(encoding="utf-8")
    last_rebuilt = None
    wiki_cards = 0
    for line in text.split("\n"):
        if "Last rebuilt:" in line:
            last_rebuilt = line.split("Last rebuilt:")[-1].strip()
        if "Cards included:" in line:
            try:
                wiki_cards = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    new_approved = max(0, approved_count - wiki_cards)
    return WikiStatus(
        wiki_path=str(path),
        exists=True,
        last_rebuilt_at=last_rebuilt,
        approved_card_count=approved_count,
        wiki_card_count=wiki_cards,
        is_stale=approved_count > wiki_cards,
        new_approved_count=new_approved,
    )


def _append_card_section(lines: list[str], card: CardSummary) -> None:
    """追加单张 approved card 的 Wiki section。"""
    # 中文学习型说明：使用 normalize_wiki_title 确保 heading 不为 "?" /
    # 纯标点 / 空字符串。fallback 链：card.title → card.id → 源文件名 → Untitled。
    title = normalize_wiki_title(
        card.title,
        card.id,
        card.path.stem if card.path else None,
    )
    lines.append(f"<!-- WIKI_SECTION_START card={card.id} -->\n")
    lines.append(f"### {title}\n\n")

    # 读 body 提取摘要
    try:
        body = read_card_body(card.path)
    except Exception:
        body = ""
    summary = extract_section(body, "AI Summary") if body else ""
    principles = extract_section(body, "Principles") if body else ""
    actions = extract_section(body, "Action Items") if body else ""

    if summary:
        lines.append(f"{summary}\n\n")
    if principles:
        lines.append(f"**核心原则:**\n{principles}\n\n")
    if actions:
        lines.append(f"**行动项:**\n{actions}\n\n")

    # Provenance（代码自动追加）
    lines.append("**来源追溯:**\n\n")
    lines.append(f"- **源卡片**: [{title}](../20-Knowledge-Cards/{card.rel_path.rsplit('/', 1)[-1] if '/' in card.rel_path else card.rel_path})\n")
    lines.append(f"- **卡片路径**: `{card.rel_path}`\n")
    # 中文学习型说明：原 source_path 不能直接嵌入 wiki content；
    # 优先用 source_title，fallback 到 source_path 的 basename。
    provenance_label = card.source_title
    if not provenance_label and card.source_path:
        provenance_label = Path(card.source_path).name
    if provenance_label:
        lines.append(f"- **原始来源**: {provenance_label}\n")
    if card.strategy_id:
        lines.append(f"- **策略**: {card.strategy_id} v{card.strategy_version or '?'}\n")
    if card.tags:
        lines.append(f"- **标签**: {', '.join(card.tags)}\n")
    if card.value_score is not None:
        lines.append(f"- **价值评分**: {card.value_score}\n")

    lines.append("\n<!-- WIKI_SECTION_END -->\n")
    lines.append("---\n\n")


# ============================================================================
# CardDigest — LLM input 构建
# ============================================================================


@dataclass(frozen=True)
class CardDigest:
    """单张 approved card 的安全摘要 —— 供 LLM synthesis 使用。

    raw source 全文不进入 digest。provenance 由代码追加，不进入 LLM 输入。
    """
    card_id: str
    title: str
    track: str | None
    tags: list[str]
    summary: str        # from AI Summary
    principles: str         # from Principles
    actions: str            # from Action Items
    value_score: int | None
    approved_at: str | None
    card_rel_path: str
    source_title: str | None


def _build_card_digest(card: CardSummary, max_body_chars: int = 2000) -> CardDigest | None:
    """从单张 approved card 构建安全摘要。ai_draft/trashed 不应传入。"""
    if card.status != "human_approved":
        return None
    try:
        body = read_card_body(card.path)
    except Exception:
        body = ""
    summary = (extract_section(body, "AI Summary") or "")[:max_body_chars]
    principles = (extract_section(body, "Principles") or "")[:max_body_chars]
    actions = (extract_section(body, "Action Items") or "")[:max_body_chars]
    return CardDigest(
        card_id=card.id or str(card.path.stem),
        title=card.title or "Untitled",
        track=card.track,
        tags=list(card.tags),
        summary=summary,
        principles=principles,
        actions=actions,
        value_score=card.value_score,
        approved_at=card.approved_at.isoformat() if card.approved_at else None,
        card_rel_path=card.rel_path,
        source_title=card.source_title,
    )


# ============================================================================
# LLM Wiki synthesis
# ============================================================================


@dataclass(frozen=True)
class LLMWikiResult:
    wiki_path: str
    included_cards: int
    section_count: int
    additional_cards: int
    warnings: list[str]
    model_id: str
    mode: str = "llm"
    last_rebuilt_at: str = ""


def llm_rebuild_wiki(
    cfg: MindForgeConfig,
    *,
    prompts_dir: str | None = None,
    max_digest_chars: int = 2000,
) -> LLMWikiResult:
    """(Deprecated) 用 configured model 合成 Main Wiki（LLM synthesis）。"""
    raise WikiError("llm_rebuild_wiki is deprecated in v0.5 to enforce strict approval boundaries. LLM summaries must now be generated as AI drafts and explicitly approved.")


# v0.5: _generate_wiki_synthesis removed.
# Wiki 现在是 runtime View（TopicPresenter），不再需要 LLM synthesis 路径。


# ---------------------------------------------------------------------------
# Wiki Related Sections (v0.4 U1)
# ---------------------------------------------------------------------------


def compute_wiki_related_sections(
    section_card_map: dict[str, list[str]],
    *,
    top_n: int = 3,
) -> dict[str, list[dict[str, object]]]:
    """计算每个 Wiki section 的 related sections（基于共享 card 的 Jaccard overlap）。

    Args:
        section_card_map: section_title → card_id 列表的映射
        top_n: 每个 section 最多返回的 related section 数量

    Returns:
        section_title → related section 列表，每项包含 title、overlap、shared_count
    """
    sections = list(section_card_map.keys())
    if len(sections) <= 1:
        return {}

    # 预计算每个 section 的 card_id 集合
    card_sets: dict[str, set[str]] = {
        title: set(card_ids) for title, card_ids in section_card_map.items()
    }

    result: dict[str, list[dict[str, object]]] = {}
    for sec_a in sections:
        set_a = card_sets[sec_a]
        if not set_a:
            result[sec_a] = []
            continue

        scored: list[tuple[str, float, int]] = []
        for sec_b in sections:
            if sec_b == sec_a:
                continue
            set_b = card_sets[sec_b]
            if not set_b:
                continue
            intersection = len(set_a & set_b)
            if intersection == 0:
                continue
            union = len(set_a | set_b)
            jaccard = intersection / union if union > 0 else 0.0
            scored.append((sec_b, jaccard, intersection))

        scored.sort(key=lambda x: x[1], reverse=True)
        result[sec_a] = [
            {"title": title, "overlap": round(ov, 3), "shared_cards": shared}
            for title, ov, shared in scored[:top_n]
        ]

    return result


# ---------------------------------------------------------------------------
# Wiki heading normalization
#
# 中文学习型说明：Wiki heading 可能来自 card.title（确定性模板）或 LLM
# synthesis 输出。无论来源，heading 都不应出现 "?" / 纯标点 / 纯空白。
# 本 helper 覆盖 deterministic card section、LLM markdown parsed heading、
# view model、anchor generation 四层。
# ---------------------------------------------------------------------------


def normalize_wiki_title(
    raw: str | None,
    *fallbacks: str | None,
) -> str:
    """把 raw title 归一化成安全的 Wiki heading / TOC anchor 源。

    Args:
        raw: 原始 title（可能为 None / 空字符串 / "?" / 纯标点）。
        *fallbacks: 按优先级排列的 fallback 候选（如 card.id、源文件名等）。

    Returns:
        归一化后的 title。永远不会返回 "?" / 纯标点 / 空字符串。
    """
    if raw and raw.strip():
        stripped = raw.strip()
        # 拒绝 "?" 和纯标点（不含任何字母/数字/CJK 字符）
        if stripped != "?" and _HAS_CONTENT_RE.search(stripped):
            return stripped
    # fallback 链：依次尝试非空且非纯标点的候选
    for fb in fallbacks:
        if fb and fb.strip():
            fb_stripped = fb.strip()
            if fb_stripped != "?" and _HAS_CONTENT_RE.search(fb_stripped):
                return fb_stripped
    return "Untitled"


# 与 pipeline.py 的 _RE_HAS_CONTENT 同语义：包含至少一个有意义字符。
_HAS_CONTENT_RE = re.compile(
    r"[A-Za-z0-9"
    r"぀-ヿ"  # 日文
    r"㐀-䶿一-鿿"  # 中日韩统一表意文字
    r"가-힯"  # 韩文
    r"]",
)


__all__ = [
    "WikiRebuildResult",
    "WikiStatus",
    "WikiError",
    "CardDigest",
    "LLMWikiResult",
    "normalize_wiki_title",
    "read_main_wiki",
    "get_wiki_status",
]
