"""M4 Provenance API router — SDD §8。

GET /api/provenance/cards/{card_id}/location → SourceLocationResponse
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import SourceLocationResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["provenance"])


@router.get(
    "/provenance/cards/{card_id}/location",
    response_model=SourceLocationResponse,
)
def get_card_location(
    card_id: str,
    facade: WebFacade = Depends(get_facade),
) -> SourceLocationResponse:
    """获取卡片内容在源文件中的精确位置。

    根据 source_type 返回不同字段：
    - plain_markdown: heading_path + line range
    - txt: line range
    - html: heading_path + css_selector
    - pdf: page number
    - docx: paragraph range

    不执行文件内容读取，仅返回位置元数据。
    """
    loc = facade.compute_card_location(card_id)
    if loc is None:
        raise user_error(
            404, "card_not_found",
            f"未找到卡片 {card_id}。",
            "检查卡片 ID 是否正确，或卡片是否已被删除。",
        )

    return SourceLocationResponse(
        source_type=loc.source_type,
        heading_path=list(loc.heading_path) if loc.heading_path else None,
        line_start=loc.line_start,
        line_end=loc.line_end,
        page_number=loc.page_number,
        paragraph_start=loc.paragraph_start,
        paragraph_end=loc.paragraph_end,
        css_selector=loc.css_selector,
        display=loc.to_display(),
    )
