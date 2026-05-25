from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import (
    CardBodyUpdateRequest,
    CardBodyUpdateResponse,
    ExportCardsRequest,
    ExportCardsResponse,
    FolderImportPreviewRequest,
    FolderImportPreviewResponse,
    FolderImportRequest,
    FolderImportResponse,
    ImportCardRequest,
    ImportCardResponse,
    KnowledgeCommunitiesResponse,
    LibraryCardDetailResponse,
    LibraryCardsResponse,
    LibraryStatsResponse,
    ProvenanceTrailResponse,
    WorkflowSummaryResponse,
)
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/workflow/summary", response_model=WorkflowSummaryResponse)
def workflow_summary(facade: WebFacade = Depends(get_facade)) -> WorkflowSummaryResponse:
    return facade.workflow_summary()


@router.get("/library/stats", response_model=LibraryStatsResponse)
def library_stats(facade: WebFacade = Depends(get_facade)) -> LibraryStatsResponse:
    return facade.library_cards().stats


@router.get("/library/cards", response_model=LibraryCardsResponse)
def library_cards(facade: WebFacade = Depends(get_facade)) -> LibraryCardsResponse:
    return facade.library_cards()


@router.get(
    "/library/card",
    response_model=LibraryCardDetailResponse,
    response_model_exclude_none=True,
)
def library_card(
    ref: str = Query(..., description="Card id, filename, absolute path, or vault-relative path"),
    show_content: bool = Query(True, description="Show card body; source body is never returned."),
    facade: WebFacade = Depends(get_facade),
) -> LibraryCardDetailResponse:
    detail = facade.library_card_detail(ref, show_content=show_content)
    if detail is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    return detail


@router.get("/library/trail", response_model=ProvenanceTrailResponse)
def provenance_trail(
    ref: str = Query(..., description="Card id, filename, absolute path, or vault-relative path"),
    facade: WebFacade = Depends(get_facade),
) -> ProvenanceTrailResponse:
    trail = facade.provenance_trail(ref)
    if trail is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    return trail


@router.patch("/library/card", response_model=CardBodyUpdateResponse)
def update_library_card(
    payload: CardBodyUpdateRequest,
    ref: str = Query(..., description="Card id, filename, absolute path, or vault-relative path"),
    facade: WebFacade = Depends(get_facade),
) -> CardBodyUpdateResponse:
    result = facade.update_library_card_body(ref, payload.body)
    if result is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    if not result.ok:
        raise user_error(400, "card_save_failed", result.message, "重新打开 card detail 后再保存。")
    return result


@router.post("/knowledge/export", response_model=ExportCardsResponse)
def export_cards(
    payload: ExportCardsRequest,
    facade: WebFacade = Depends(get_facade),
) -> ExportCardsResponse:
    """导出选中卡片为 Markdown / JSON / OPML 格式（白名单过滤）。"""
    from datetime import datetime, timezone
    from xml.etree.ElementTree import Element, SubElement, tostring

    export_format = payload.format or "markdown"

    # Gather card data (safe fields only)
    cards: list[dict] = []
    for card_id in payload.card_ids:
        detail = facade.library_card_detail(card_id, show_content=True)
        if detail is None:
            continue
        card = detail.card
        body = detail.body or ""
        status_label = "已确认" if card.status == "human_approved" else card.status
        created = card.created_at[:10] if card.created_at else "未知"
        source = card.source_title or "-"
        cards.append({
            "title": card.title or "未命名卡片",
            "status": status_label,
            "status_raw": card.status,
            "created_at": created,
            "source_title": source,
            "body": body,
        })

    # Markdown format
    parts: list[str] = []
    for c in cards:
        parts.append(
            f"# {c['title']}\n\n"
            f"状态: {c['status']} | 创建: {c['created_at']} | 来源: {c['source_title']}\n\n"
            f"{c['body']}\n"
        )
    markdown = "\n---\n\n".join(parts)

    # JSON format
    import json
    json_output = json.dumps({
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format": "json",
        "card_count": len(cards),
        "cards": [
            {k: v for k, v in c.items() if k != "status_raw"}
            for c in cards
        ],
    }, ensure_ascii=False, indent=2)

    # OPML format
    opml_el = Element("opml", version="2.0")
    head = SubElement(opml_el, "head")
    SubElement(head, "title").text = "MindForge Export"
    SubElement(head, "dateCreated").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    body_el = SubElement(opml_el, "body")
    for c in cards:
        outline = SubElement(body_el, "outline", text=c["title"], type="card")
        outline.set("status", c["status_raw"])
        outline.set("source", c["source_title"])
        outline.set("created", c["created_at"])
        # Store body as _note attribute (OPML convention)
        outline.set("_note", c["body"][:500])
    opml = tostring(opml_el, encoding="unicode")

    return ExportCardsResponse(
        markdown=markdown,
        json_data=json_output,
        opml=opml,
        format=export_format,
        card_count=len(cards),
    )


@router.post("/knowledge/export/download")
def export_cards_download(
    payload: ExportCardsRequest,
    facade: WebFacade = Depends(get_facade),
):
    """导出选中卡片为 ZIP 文件下载（包含 cards.md + manifest.json）。

    v2.4 U6：v1.5 I4 后续 —— zip 导出。
    """
    import io
    import json
    import zipfile
    from datetime import datetime, timezone

    cards: list[dict] = []
    for card_id in payload.card_ids:
        detail = facade.library_card_detail(card_id, show_content=True)
        if detail is None:
            continue
        card = detail.card
        body = detail.body or ""
        cards.append({
            "title": card.title or "Untitled",
            "status": card.status,
            "created_at": card.created_at or "unknown",
            "source_title": card.source_title or "-",
            "body": body,
        })

    parts: list[str] = []
    for c in cards:
        parts.append(
            f"# {c['title']}\n\n"
            f"Status: {c['status']} | Created: {c['created_at']} | Source: {c['source_title']}\n\n"
            f"{c['body']}\n"
        )
    cards_md = "\n---\n\n".join(parts)

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format": "zip",
        "card_count": len(cards),
        "cards": [{k: v for k, v in c.items() if k != "body"} for c in cards],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("cards.md", cards_md)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    buf.seek(0)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"mindforge-export-{timestamp}.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/knowledge/import", response_model=ImportCardResponse)
def import_card(
    payload: ImportCardRequest,
    facade: WebFacade = Depends(get_facade),
) -> ImportCardResponse:
    """从 Markdown 内容导入新卡片（ai_draft 状态，不调用 LLM）。"""
    if not payload.title.strip():
        raise user_error(400, "import_title_required", "请输入卡片标题。", "标题不能为空。")
    if not payload.body.strip():
        raise user_error(400, "import_body_required", "请输入卡片内容。", "内容不能为空。")
    return facade.import_card(payload.title, payload.body, payload.source_name)


# ── v2.4 U1 Folder Import ──────────────────────


@router.post("/knowledge/import/folder-preview", response_model=FolderImportPreviewResponse)
def folder_import_preview(
    payload: FolderImportPreviewRequest,
    facade: WebFacade = Depends(get_facade),
) -> FolderImportPreviewResponse:
    """扫描文件夹中的 .md 文件，dry-run 预览（不写入任何卡片）。"""
    if not payload.folder_path.strip():
        raise user_error(400, "folder_path_required", "请输入文件夹路径。", "文件夹路径不能为空。")
    return facade.preview_folder_import(payload.folder_path)


@router.post("/knowledge/import/folder", response_model=FolderImportResponse)
def folder_import(
    payload: FolderImportRequest,
    facade: WebFacade = Depends(get_facade),
) -> FolderImportResponse:
    """批量导入文件夹中指定索引的 .md 文件为 ai_draft 卡片。"""
    if not payload.folder_path.strip():
        raise user_error(400, "folder_path_required", "请输入文件夹路径。", "文件夹路径不能为空。")
    if not payload.indices:
        raise user_error(400, "indices_required", "请选择要导入的文件。", "至少选择一个文件。")
    return facade.import_from_folder(payload.folder_path, payload.indices)


@router.get("/knowledge/communities", response_model=KnowledgeCommunitiesResponse)
def knowledge_communities(
    facade: WebFacade = Depends(get_facade),
) -> KnowledgeCommunitiesResponse:
    """获取知识社区列表（按 source/tag/wiki_section 分组的卡片群）。"""
    return facade.knowledge_communities()
