"""Main Wiki service —— 从 approved cards 确定性地生成派生 Wiki 视图。

中文学习型说明：Wiki 是 approved cards 的只读派生视图，不是 source、不是
审批入口、不是唯一知识源。rebuild 总是从 approved card 集合重新生成，使用
确定性模板（不调 LLM）。provenance 由代码自动追加，不会被 LLM 删除。

Wiki 文件放在 ``30-Wiki/Main-Wiki.md``，与 cards(20-Knowledge-Cards) 分开。
写入使用 atomic write（先写 .tmp 再 replace），失败时旧 Wiki 保持不变。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from .cards import CardSummary, extract_section, iter_cards, read_card_body
from .config import MindForgeConfig


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


class WikiError(ValueError):
    """Wiki 操作失败；message 可安全返回给 Web/CLI。"""


def _wiki_root(cfg: MindForgeConfig) -> Path:
    return cfg.vault.root / "30-Wiki"


def _wiki_path(cfg: MindForgeConfig) -> Path:
    return _wiki_root(cfg) / "Main-Wiki.md"


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

    return WikiStatus(
        wiki_path=str(path),
        exists=True,
        last_rebuilt_at=last_rebuilt,
        approved_card_count=approved_count,
        wiki_card_count=wiki_cards,
    )


def _append_card_section(lines: list[str], card: CardSummary) -> None:
    """追加单张 approved card 的 Wiki section。"""
    title = card.title or card.id or "Untitled"
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
    if card.source_title:
        lines.append(f"- **Original source**: {card.source_title}\n")
    elif card.source_path:
        lines.append(f"- **Original source**: `{card.source_path}`\n")
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
        approved_at=card.created_at.isoformat() if card.created_at else None,
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

    # 1) 解析 model
    model_id = cfg.wiki.model or cfg.llm.default_model
    if not model_id or model_id not in {m.alias for m in cfg.llm.models.values()}:
        raise WikiError(f"wiki.model={model_id!r} 不在 llm.models 中。请在 Setup 中配置模型或设置 wiki.model。")

    # 2) 构建 CardDigest
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
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
    from .llm.factory import build_providers
    from .llm.client import LLMClient
    from .prompts_runtime import load_prompt, render

    prompts_root = Path(prompts_dir) if prompts_dir else asset_root("prompts")
    prompt_text = load_prompt(prompts_root, "wiki_synthesis", "v1")
    rendered = render(prompt_text, {"approved_cards": digest_json, "card_count": str(len(digests))})

    # 5) 构建 provider + client
    providers = build_providers(cfg.llm)
    model_config = cfg.llm.models[model_id]
    provider = providers.get(model_config.alias)
    if provider is None:
        raise WikiError(f"模型 {model_id!r} 的 provider 不可用")

    client = LLMClient(cfg.llm, providers)
    result = client.generate(stage="wiki_synthesis", prompt=rendered)

    # 6) 解析 JSON
    try:
        output = _json.loads(result.result.text)
    except (ValueError, _json.JSONDecodeError):
        # 尝试 extract first JSON object
        import re
        m = re.search(r'\{[\s\S]*\}', result.result.text)
        if m:
            try:
                output = _json.loads(m.group(0))
            except _json.JSONDecodeError:
                raise WikiError("LLM 返回了无效 JSON。旧 Wiki 保持不变。")
        else:
            raise WikiError("LLM 返回了无效 JSON。旧 Wiki 保持不变。")

    if not isinstance(output, dict):
        raise WikiError("LLM 输出不是 JSON 对象。旧 Wiki 保持不变。")

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
            md_lines.append(f"### {sec.get('title', 'Untitled')}\n\n")
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


__all__ = [
    "WikiRebuildResult",
    "WikiStatus",
    "WikiError",
    "CardDigest",
    "LLMWikiResult",
    "rebuild_main_wiki",
    "llm_rebuild_wiki",
    "read_main_wiki",
    "get_wiki_status",
    "CardDigest",
    "LLMWikiResult",
]
