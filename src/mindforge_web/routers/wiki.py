"""Wiki API —— 只读展示 Main Wiki 内容。

中文学习型说明：Wiki 是 approved cards 的派生视图。API 只返回 Wiki 内容、
status summary，不返回 source 全文、不返回 secret、不调 LLM。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import WikiRebuildRequest
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/status")
def wiki_status(facade: WebFacade = Depends(get_facade)):
    """返回 Main Wiki 状态摘要。

    中文学习型说明：返回三层 mode 语义：
    - configured_mode: 用户配置想用什么
    - effective_generation_mode: rebuild 时实际会用哪种生成方式
    - content_mode: 当前 wiki 内容的实际来源（从 header 解析）
    """
    from mindforge.model_setup_readiness import model_setup_readiness
    from mindforge.wiki_service import get_wiki_status, read_main_wiki
    status = get_wiki_status(facade.cfg)
    readiness = model_setup_readiness(facade.cfg)

    # effective_generation_mode：rebuild 时实际会用的生成方式
    configured = facade.cfg.wiki.mode
    if configured == "llm" and not readiness.ready:
        effective_generation_mode = "deterministic"
        fallback_reason = f"LLM not ready ({readiness.label}). Would fallback to deterministic."
    elif configured == "llm":
        effective_generation_mode = "llm"
        fallback_reason = None
    elif configured == "deterministic":
        effective_generation_mode = "deterministic"
        fallback_reason = None
    else:
        effective_generation_mode = None
        fallback_reason = f"Unknown configured mode: {configured!r}"

    # content_mode：从已存在的 wiki header 解析
    content_mode: str | None = None
    if status.exists:
        markdown = read_main_wiki(facade.cfg)
        if markdown:
            meta = _wiki_markdown_metadata(markdown, configured_mode=configured)
            content_mode = meta.get("content_mode")

    return {
        "wiki_path": status.wiki_path,
        "exists": status.exists,
        "last_rebuilt_at": status.last_rebuilt_at,
        "approved_card_count": status.approved_card_count,
        "wiki_card_count": status.wiki_card_count,
        "is_stale": status.is_stale,
        "new_approved_count": status.new_approved_count,
        "configured_mode": configured,
        "effective_generation_mode": effective_generation_mode,
        "content_mode": content_mode,
        "fallback_reason": fallback_reason,
        "model_ready": readiness.ready,
        "model_ready_label": readiness.label,
        "model_id": _wiki_configured_model_id(facade),
    }


@router.get("/content")
def wiki_content(facade: WebFacade = Depends(get_facade)):
    """返回 Main Wiki 当前内容（只读）。"""
    from mindforge.wiki_service import read_main_wiki
    content = read_main_wiki(facade.cfg)
    if content is None:
        return {"content": None, "exists": False}
    return {"content": content, "exists": True}


@router.post("/rebuild")
def wiki_rebuild(
    payload: WikiRebuildRequest | None = None,
    facade: WebFacade = Depends(get_facade),
):
    """(Deprecated) From v0.5, direct LLM Wiki rebuild is disabled to enforce approval boundaries."""
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        status_code=410,
        content={
            "ok": False,
            "mode": payload.mode if payload else facade.cfg.wiki.mode,
            "error": "Direct LLM Wiki rebuild is deprecated in v0.5 to enforce strict approval boundaries. LLM summaries must now be generated as AI drafts and explicitly approved."
        }
    )


@router.get("/page")
def wiki_page(view: str | None = None, facade: WebFacade = Depends(get_facade)):
    """返回结构化 WikiPageViewModel JSON。

    从已有的 wiki Markdown 文件 + approved cards 构建。
    section.body 为 canonical Markdown text（非 HTML）。

    Query params:
        view=graph → 400 in v0.2（graph view 未实现）

    RFC_0002 §5.2 / SDD_WIKI_PRESENTATION_V2 §4.4。
    """
    # v0.2 graph view 未实现
    if view == "graph":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={
                "error": "graph view not implemented in v0.2",
                "message": "Graph renderer is a future extension point. "
                "Use the default markdown view instead.",
            },
        )

    from mindforge.wiki_service import read_main_wiki, _build_card_digest, iter_cards
    from mindforge.wiki_view_model import WikiPageViewModel

    # 读取 wiki Markdown
    markdown = read_main_wiki(facade.cfg)
    if markdown is None:
        # 中文学习型说明：Wiki 不存在时使用 configured_mode，不再硬编码
        # "deterministic"。content_mode 为 None 表示尚无内容。
        configured = facade.cfg.wiki.mode
        return {
            "exists": False,
            "title": "MindForge Main Wiki",
            "configured_mode": configured,
            "content_mode": None,
            "mode": None,
            "model_id": None,
            "last_rebuilt_at": None,
            "fallback_reason": "Wiki 尚未生成。请先 Rebuild。",
            "sections": [],
            "overview": "Wiki 尚未生成。请先 Rebuild。",
        }

    # 构建 CardDigest（通过 scanner 读取 approved cards）
    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    digests: list = []
    for c in scan.cards:
        d = _build_card_digest(c)
        if d:
            digests.append(d)

    # 构建 ViewModel
    wiki_meta = _wiki_markdown_metadata(markdown, configured_mode=facade.cfg.wiki.mode)
    vm = WikiPageViewModel.build_from_wiki_markdown(
        markdown_content=markdown,
        digests=digests,
        wiki_metadata=wiki_meta,
    )

    from dataclasses import asdict
    result = asdict(vm)
    # 中文学习型说明：注入三层 mode 语义。
    # - configured_mode: 用户配置
    # - content_mode: 当前 wiki 内容实际来源（从 header 解析，不 fallback）
    # - mode: legacy alias for content_mode
    result["configured_mode"] = facade.cfg.wiki.mode
    result["content_mode"] = wiki_meta.get("content_mode")
    result["mode"] = wiki_meta.get("content_mode")  # legacy alias
    return result


def _wiki_markdown_metadata(
    markdown: str,
    *,
    configured_mode: str = "llm",
) -> dict:
    """从已生成 Wiki header 提取 API metadata，不重新调用生成器。

    中文学习型说明：content_mode 只能从 wiki header 明确标记推导。
    - "LLM synthesis" 明确标记 → content_mode="llm"
    - "generated from human-approved knowledge cards" → content_mode="deterministic"
    - 其他情况 → content_mode=None（不 fallback 到 configured_mode）
    这避免 configured=llm 时把 deterministic wiki 误报为 llm 产物。
    configured_mode 单独传递，不与 content_mode 混用。

    Args:
        markdown: Wiki Markdown 全文。
        configured_mode: 用户配置的 wiki.mode（仅用于返回，不参与 content_mode 推断）。
    """

    model_id: str | None = None
    last_rebuilt_at: str | None = None
    content_mode: str | None = None  # 从 header 明确推导，不 fallback

    for line in markdown.splitlines():
        text = line.strip()
        if not text.startswith(">"):
            continue
        body = text.lstrip(">").strip()
        if body.startswith("LLM synthesis"):
            content_mode = "llm"
            for part in body.split("·"):
                part = part.strip()
                if part.startswith("Model:"):
                    model_id = part.split("Model:", 1)[1].strip() or None
                elif part.startswith("Last rebuilt:"):
                    last_rebuilt_at = part.split("Last rebuilt:", 1)[1].strip() or None
        elif body.startswith("This wiki is generated from human-approved knowledge cards"):
            if content_mode is None:
                content_mode = "deterministic"
        elif body.startswith("Last rebuilt:") and last_rebuilt_at is None:
            last_rebuilt_at = body.split("Last rebuilt:", 1)[1].strip() or None

    return {
        "content_mode": content_mode,
        "mode": content_mode,  # legacy alias for content_mode
        "model_id": model_id,
        "last_rebuilt_at": last_rebuilt_at,
        "configured_mode": configured_mode,
    }


def _wiki_configured_model_id(facade: WebFacade) -> str | None:
    """返回 Wiki rebuild 配置的模型 id，不表达当前 Wiki 内容来源。

    中文学习型说明：`/api/wiki/status` 不再返回 legacy `mode`，避免把用户配置、
    实际 rebuild 模式和当前内容来源混成一个字段。model_id 只说明下一次 LLM
    rebuild 会参考哪个配置模型；当前内容是否由 LLM 生成仍看 content_mode。
    """

    return facade.cfg.wiki.model or facade.cfg.llm.default_model


@router.get("/sections")
def wiki_sections(facade: WebFacade = Depends(get_facade)):
    """返回所有 WikiSectionView 列表（JSON）。"""
    from mindforge.wiki_service import read_main_wiki, _build_card_digest, iter_cards
    from mindforge.wiki_view_model import WikiPageViewModel

    markdown = read_main_wiki(facade.cfg)
    if markdown is None:
        return []

    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    digests = [d for c in scan.cards if (d := _build_card_digest(c))]

    vm = WikiPageViewModel.build_from_wiki_markdown(
        markdown_content=markdown,
        digests=digests,
        wiki_metadata=_wiki_markdown_metadata(markdown, configured_mode=facade.cfg.wiki.mode),
    )
    from dataclasses import asdict
    return [asdict(s) for s in vm.sections]


@router.get("/references")
def wiki_references(facade: WebFacade = Depends(get_facade)):
    """返回所有 WikiReferenceView 列表（JSON）。"""
    from mindforge.wiki_service import read_main_wiki, _build_card_digest, iter_cards
    from mindforge.wiki_view_model import WikiPageViewModel

    markdown = read_main_wiki(facade.cfg)
    if markdown is None:
        return []

    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    digests = [d for c in scan.cards if (d := _build_card_digest(c))]

    vm = WikiPageViewModel.build_from_wiki_markdown(
        markdown_content=markdown,
        digests=digests,
        wiki_metadata=_wiki_markdown_metadata(markdown, configured_mode=facade.cfg.wiki.mode),
    )
    from dataclasses import asdict
    result: list = [asdict(r) for r in vm.additional_cards]
    for s in vm.sections:
        result.extend(asdict(r) for r in s.card_refs)
    return result


@router.get("/quality")
def wiki_quality(facade: WebFacade = Depends(get_facade)):
    """返回 Wiki Quality Report 结构化数据。

    从已生成 Wiki markdown 的 <!-- WIKI_QUALITY_JSON --> comment 中解析。
    无 quality report 时返回 {"exists": false}。
    """
    import json as _json
    import re as _re

    from mindforge.wiki_service import read_main_wiki

    markdown = read_main_wiki(facade.cfg)
    if markdown is None:
        return {"exists": False}

    m = _re.search(r"<!-- WIKI_QUALITY_JSON\n(.*?)\n-->", markdown, _re.DOTALL)
    if not m:
        return {"exists": False}

    try:
        data = _json.loads(m.group(1))
    except _json.JSONDecodeError:
        return {"exists": False, "error": "Failed to parse quality report JSON"}

    return {"exists": True, **data}


@router.get("/related-sections")
def wiki_related_sections(facade: WebFacade = Depends(get_facade)):
    """返回每个 Wiki section 的 related sections（基于共享 card 的 Jaccard overlap）。

    v0.4 U1: Wiki Related Sections — 从 Wiki markdown 解析 section→card 映射，
    计算 section 间 Jaccard overlap，每个 section 返回 top 3 related sections。
    """
    from mindforge.wiki_service import read_main_wiki, compute_wiki_related_sections
    from mindforge.wiki_view_model import _parse_wiki_marker_card_ids
    import re as _re

    markdown = read_main_wiki(facade.cfg)
    if markdown is None:
        return {"exists": False, "sections": {}}

    # 解析 section→card_ids 映射
    section_card_map: dict[str, list[str]] = {}
    pattern = (
        r"<!--\s*WIKI_SECTION_START\s+(?:card_ids|card)=([^>]+?)\s*-->\s*\n"
        r"###\s+(.+?)\n"
    )
    for m in _re.finditer(pattern, markdown, _re.DOTALL):
        card_ids_str = m.group(1).strip()
        title = m.group(2).strip()
        card_ids = _parse_wiki_marker_card_ids(card_ids_str)
        if card_ids:
            section_card_map[title] = card_ids

    related = compute_wiki_related_sections(section_card_map)
    return {"exists": True, "sections": related}
