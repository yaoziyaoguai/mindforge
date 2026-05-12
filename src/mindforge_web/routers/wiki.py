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
    """返回 Main Wiki 状态摘要。"""
    from mindforge.model_setup_readiness import model_setup_readiness
    from mindforge.wiki_service import get_wiki_status
    status = get_wiki_status(facade.cfg)
    readiness = model_setup_readiness(facade.cfg)
    return {
        "wiki_path": status.wiki_path,
        "exists": status.exists,
        "last_rebuilt_at": status.last_rebuilt_at,
        "approved_card_count": status.approved_card_count,
        "wiki_card_count": status.wiki_card_count,
        "model_ready": readiness.ready,
        "model_ready_label": readiness.label,
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
    """从 approved cards 重建 Main Wiki。主路径为 LLM synthesis，需要 model setup ready。"""
    from mindforge.model_setup_readiness import model_setup_readiness
    from mindforge.wiki_service import rebuild_main_wiki, llm_rebuild_wiki, WikiError

    requested_mode = payload.mode if payload and payload.mode else None
    effective_mode = requested_mode or facade.cfg.wiki.mode

    if effective_mode == "llm":
        readiness = model_setup_readiness(facade.cfg)
        if not readiness.ready:
            return {
                "ok": False,
                "mode": "llm",
                "error": f"LLM-first wiki rebuild requires model setup ready ({readiness.label}). Complete model setup first.",
            }
        try:
            result = llm_rebuild_wiki(facade.cfg)
            return {
                "ok": True,
                "mode": "llm",
                "wiki_path": result.wiki_path,
                "included_cards": result.included_cards,
                "section_count": result.section_count,
                "additional_cards": result.additional_cards,
                "model_id": result.model_id,
                "warnings": result.warnings,
                "last_rebuilt_at": result.last_rebuilt_at,
            }
        except WikiError as e:
            return {"ok": False, "mode": "llm", "error": str(e)}

    if effective_mode == "deterministic":
        # deterministic template rebuild 仅保留为内部 Troubleshooting 回退，
        # 不在 Web UI 普通用户路径中暴露。
        result = rebuild_main_wiki(facade.cfg)
        return {
            "ok": True,
            "mode": "deterministic",
            "wiki_path": result.wiki_path,
            "included_cards": result.included_cards,
            "last_rebuilt_at": result.last_rebuilt_at,
        }

    return {
        "ok": False,
        "mode": effective_mode or "unknown",
        "error": f"Unknown wiki mode: {effective_mode!r}. Use llm or deterministic（Troubleshooting fallback）.",
    }
