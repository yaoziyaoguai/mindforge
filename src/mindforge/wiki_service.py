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
    """从 approved cards 重建 Main Wiki（deterministic template，不调 LLM）。

    只包含 human_approved 卡片，排除 ai_draft 和 trashed cards。
    """
    wiki_dir = _wiki_root(cfg)
    wiki_path = _wiki_path(cfg)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # 收集 approved cards（排除 ai_draft）
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = [c for c in scan.cards if c.status == "human_approved"]

    # 排除 trashed cards（不在 cards_dir 中 = 已被 trash）
    # iter_cards 只扫描 cards_dir，trashed 在 90-Archive/ 不被扫到，
    # 所以 approved card 列表已天然排除 trashed cards。
    # 仅记录 card 数量。
    trashed_excluded = 0  # 本轮不追踪，后续可接入 trash_service

    # 按 track 分组
    by_track: dict[str, list[CardSummary]] = {}
    for c in approved:
        track = c.track or "unrouted"
        by_track.setdefault(track, []).append(c)

    # 生成 Wiki
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    lines: list[str] = []
    lines.append("# MindForge Main Wiki\n")
    lines.append("<!-- Wiki generated from approved knowledge cards. Do not edit directly. -->\n")
    lines.append("> This wiki is generated from human-approved knowledge cards.\n")
    lines.append("> It is a derived view. Source files are not copied into this wiki.\n")
    lines.append(f"> Last rebuilt: {now}\n")
    lines.append(f"> Cards included: {len(approved)}\n\n")

    lines.append("## Overview\n\n")
    lines.append(f"- **Cards included**: {len(approved)}\n")
    lines.append(f"- **Last rebuilt**: {now}\n\n")

    for track, cards in sorted(by_track.items()):
        lines.append(f"## {track}\n\n")
        for card in cards:
            _append_card_section(lines, card)
        lines.append("")

    content = "".join(lines)

    # M2: 追加 Wiki Quality Report appendix
    quality_appendix = _generate_quality_report_appendix(content, approved)
    content += quality_appendix

    # Atomic write
    tmp = wiki_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(wiki_path))

    return WikiRebuildResult(
        wiki_path=str(wiki_path),
        included_cards=len(approved),
        excluded_trashed=trashed_excluded,
        last_rebuilt_at=now,
        card_count=len(approved),
    )


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
        lines.append(f"**Principles:**\n{principles}\n\n")
    if actions:
        lines.append(f"**Action Items:**\n{actions}\n\n")

    # Provenance（代码自动追加）
    lines.append("**Provenance:**\n\n")
    lines.append(f"- **Source card**: [{title}](../20-Knowledge-Cards/{card.rel_path.rsplit('/', 1)[-1] if '/' in card.rel_path else card.rel_path})\n")
    lines.append(f"- **Card path**: `{card.rel_path}`\n")
    # 中文学习型说明：原 source_path 不能直接嵌入 wiki content；
    # 优先用 source_title，fallback 到 source_path 的 basename。
    provenance_label = card.source_title
    if not provenance_label and card.source_path:
        provenance_label = Path(card.source_path).name
    if provenance_label:
        lines.append(f"- **Original source**: {provenance_label}\n")
    if card.strategy_id:
        lines.append(f"- **Strategy**: {card.strategy_id} v{card.strategy_version or '?'}\n")
    if card.tags:
        lines.append(f"- **Tags**: {', '.join(card.tags)}\n")
    if card.value_score is not None:
        lines.append(f"- **Value score**: {card.value_score}\n")

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
    """用 configured model 合成 Main Wiki（LLM synthesis）。

    中文学习型说明：LLM 只负责内容合成（overview + sections），不负责 provenance。
    Provenance 由代码根据 card_ids 映射追加。JSON 解析失败或 LLM 调用失败时不破坏旧 Wiki。
    """
    import json as _json

    wiki_dir = _wiki_root(cfg)
    wiki_path = _wiki_path(cfg)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # 1) 解析 Wiki 专属 model。Wiki synthesis 是 approved cards 的派生视图，
    # 不属于 processing pipeline 的五阶段 routing。
    model_id = cfg.wiki.model or cfg.llm.default_model
    if not model_id:
        raise WikiError(
            _wiki_error_message(
                "wiki.mode=llm requires wiki.model or llm.default_model. Complete model setup first.",
                "wiki.mode=llm 需要配置 wiki.model 或 llm.default_model。请先在 Setup 中添加模型。",
            )
        )
    if model_id not in cfg.llm.models:
        raise WikiError(
            _wiki_error_message(
                f"wiki.model={model_id!r} is not configured in llm.models. Configure the model or update wiki.model.",
                f"wiki.model={model_id!r} 不在 llm.models 中。请在 Setup 中配置模型或设置 wiki.model。",
            )
        )

    # 2) 构建 CardDigest
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved_cards = [c for c in scan.cards if c.status == "human_approved"]
    digests: list[CardDigest] = []
    for c in scan.cards:
        d = _build_card_digest(c, max_body_chars=max_digest_chars)
        if d:
            digests.append(d)

    # 3) 序列化为 LLM input
    digest_list = [
        {
            "card_id": d.card_id,
            "title": d.title,
            "track": d.track,
            "tags": d.tags,
            "summary": d.summary,
            "principles": d.principles,
            "actions": d.actions,
            "value_score": d.value_score,
            "approved_at": d.approved_at,
        }
        for d in digests
    ]
    digest_json = _json.dumps(digest_list, ensure_ascii=False, indent=2)

    # 4) 加载 prompt + 调用 LLM
    from .assets_runtime import asset_root
    from .prompts_runtime import load_prompt, render

    prompts_root = Path(prompts_dir) if prompts_dir else asset_root().joinpath("prompts")
    prompt_text = load_prompt(prompts_root, "wiki_synthesis", "v1")
    rendered = render(prompt_text, {"approved_cards": digest_json, "card_count": str(len(digests))})

    # 5) Wiki 专属 provider 调用；不经过 LLMClient 的 processing stage 路由。
    result_text = _generate_wiki_synthesis(cfg, model_id, rendered)

    # 6) 解析 JSON
    try:
        output = _json.loads(result_text)
    except (ValueError, _json.JSONDecodeError):
        # 尝试 extract first JSON object
        import re
        m = re.search(r'\{[\s\S]*\}', result_text)
        if m:
            try:
                output = _json.loads(m.group(0))
            except _json.JSONDecodeError:
                raise WikiError(
                    _wiki_error_message(
                        "The LLM returned invalid JSON. The previous Wiki was kept unchanged.",
                        "LLM 返回了无效 JSON。旧 Wiki 保持不变。",
                    )
                )
        else:
            raise WikiError(
                _wiki_error_message(
                    "The LLM returned invalid JSON. The previous Wiki was kept unchanged.",
                    "LLM 返回了无效 JSON。旧 Wiki 保持不变。",
                )
            )

    if not isinstance(output, dict):
        raise WikiError(
            _wiki_error_message(
                "The LLM output was not a JSON object. The previous Wiki was kept unchanged.",
                "LLM 输出不是 JSON 对象。旧 Wiki 保持不变。",
            )
        )

    # 7) 构建 card_id -> CardDigest 索引
    digest_index: dict[str, CardDigest] = {d.card_id: d for d in digests}
    warnings: list[str] = []
    cited_ids: set[str] = set()

    # 8) 验证 card_ids
    sections = output.get("sections") or []
    if not isinstance(sections, list):
        sections = []

    valid_sections = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        card_ids = sec.get("card_ids") or []
        if not isinstance(card_ids, list):
            card_ids = []
        valid_ids = []
        for cid in card_ids:
            cid_str = str(cid)
            if cid_str in digest_index:
                valid_ids.append(cid_str)
                cited_ids.add(cid_str)
            else:
                warnings.append(f"LLM 引用了未知 card_id={cid_str!r}，已安全剔除")
        if valid_ids:
            sec["card_ids"] = valid_ids
            valid_sections.append(sec)
        else:
            warnings.append(f"section '{sec.get('title', '?')}' 无有效 card_id，已丢弃")

    # 9) 构建 uncited appendix
    uncited = [d for d in digests if d.card_id not in cited_ids]

    # 10) 渲染 Markdown + 原子写入
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    md_lines: list[str] = []
    md_lines.append("# MindForge Main Wiki\n")
    md_lines.append(f"> LLM synthesis · Model: {model_id} · Last rebuilt: {now}\n")
    md_lines.append(f"> Cards included: {len(digests)}\n\n")

    overview = output.get("overview") or ""
    if isinstance(overview, str) and overview:
        md_lines.append("## Overview\n\n")
        md_lines.append(f"{overview}\n\n")

    if valid_sections:
        md_lines.append("## Knowledge Sections\n\n")
        for sec in valid_sections:
            card_ids = sec.get("card_ids", [])
            md_lines.append(f"<!-- WIKI_SECTION_START card_ids={','.join(card_ids)} -->\n")
            md_lines.append(
                f"### {normalize_wiki_title(sec.get('title'))}\n\n"
            )
            md_lines.append(f"{sec.get('body', '')}\n\n")
            md_lines.append("**Related approved cards:**\n\n")
            for cid in card_ids:
                d = digest_index.get(cid)
                if d:
                    fname = d.card_rel_path.rsplit('/', 1)[-1] if '/' in d.card_rel_path else d.card_rel_path
                    md_lines.append(f"- [{d.title}](../20-Knowledge-Cards/{fname})\n")
                    if d.source_title:
                        md_lines.append(f"  - Original source: {d.source_title}\n")
            md_lines.append("\n<!-- WIKI_SECTION_END -->\n")
            md_lines.append("---\n\n")

    if uncited:
        md_lines.append("## Additional Approved Cards\n\n")
        md_lines.append("以下 approved cards 未被 LLM section 引用，但保留在 Wiki 中作为参考。\n\n")
        for d in uncited:
            fname = d.card_rel_path.rsplit('/', 1)[-1] if '/' in d.card_rel_path else d.card_rel_path
            md_lines.append(f"- [{d.title}](../20-Knowledge-Cards/{fname})\n")
            if d.source_title:
                md_lines.append(f"  - Original source: {d.source_title}\n")
            if d.summary:
                md_lines.append(f"  - {d.summary[:200]}\n")
        md_lines.append("")

    open_qs = output.get("open_questions") or []
    if isinstance(open_qs, list) and open_qs:
        md_lines.append("## Open Questions\n\n")
        for q in open_qs:
            if isinstance(q, dict):
                md_lines.append(f"- **{q.get('question', '?')}**\n")

    content = "".join(md_lines)

    # M2: 追加 Wiki Quality Report appendix
    quality_appendix = _generate_quality_report_appendix(content, approved_cards)
    content += quality_appendix

    # Atomic write
    tmp = wiki_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(wiki_path))

    return LLMWikiResult(
        wiki_path=str(wiki_path),
        included_cards=len(digests),
        section_count=len(valid_sections),
        additional_cards=len(uncited),
        warnings=warnings,
        model_id=model_id,
        last_rebuilt_at=now,
    )


def _generate_wiki_synthesis(cfg: MindForgeConfig, model_id: str, prompt: str) -> str:
    """调用 Wiki 专属 model 并返回文本，不复用 processing stage routing。

    中文学习型说明：``llm.routing`` 只描述 triage/distill/link/review/action 五个
    processing step。Wiki synthesis 的输入、失败语义和 provenance 边界都不同，
    因此在 Wiki service 内按 ``wiki.model`` / ``llm.default_model`` 选择单个
    provider。这样既复用 provider 抽象，也避免给 processing pipeline 增加伪 stage。
    """

    from .llm.base import LLMRequest, ProviderError
    from .llm.factory import build_provider_for_model
    from .secret_store import resolve_project_root_from_config

    model_config = cfg.llm.models[model_id]
    try:
        provider = build_provider_for_model(
            model_config,
            project_root=resolve_project_root_from_config(cfg),
        )
    except ProviderError as exc:
        raise WikiError(str(exc)) from exc

    actual_model = model_config.model
    if model_config.model_env:
        override = os.environ.get(model_config.model_env)
        if override:
            actual_model = override
    if not actual_model:
        raise WikiError(
            _wiki_error_message(
                f"wiki.model={model_id!r} has no resolved model name. Configure model or model_env.",
                f"wiki.model={model_id!r} 没有可用的 model 名称。请配置 model 或 model_env。",
            )
        )

    request = LLMRequest(
        prompt=prompt,
        stage="wiki_synthesis",
        model=actual_model,
        response_format="json_object",
    )
    attempts = max(1, model_config.max_retries + 1)
    last_error: ProviderError | None = None
    for attempt in range(attempts):
        try:
            return provider.generate(request).text
        except ProviderError as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.2 * (attempt + 1))
    assert last_error is not None
    raise WikiError(f"LLM Wiki synthesis failed: {last_error}") from last_error


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
    "rebuild_main_wiki",
    "llm_rebuild_wiki",
    "read_main_wiki",
    "get_wiki_status",
    "CardDigest",
    "LLMWikiResult",
]
