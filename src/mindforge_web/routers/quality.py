"""M1 Quality API router — SDD §4.1。

GET /api/quality/cards/{card_id} → CardQualityResponse
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import (
    CardQualityResponse,
    QualityRubricScoreResponse,
    QualityWarningResponse,
)
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["quality"])


@router.get("/quality/cards/{card_id}", response_model=CardQualityResponse)
def get_card_quality(
    card_id: str,
    facade: WebFacade = Depends(get_facade),
) -> CardQualityResponse:
    """获取单张卡片的 quality metadata。

    不修改卡片文件，不调用 LLM / API。
    quality score 仅供审批和维护参考，不自动决定卡片状态。
    """
    quality = facade.compute_card_quality(card_id)
    if quality is None:
        raise user_error(
            404, "card_not_found",
            f"未找到卡片 {card_id}。",
            "检查卡片 ID 是否正确，或卡片是否已被删除。",
        )

    return CardQualityResponse(
        card_id=card_id,
        overall_level=quality.overall_level.value,
        overall_level_label=quality.level_label,
        overall_score=quality.overall_score,
        rubric_scores=[
            QualityRubricScoreResponse(
                dimension=rs.dimension,
                score=rs.score,
                max_score=rs.max_score,
                notes=rs.notes,
            )
            for rs in quality.rubric_scores
        ],
        warnings=[
            QualityWarningResponse(
                code=w.code,
                severity=w.severity,
                message=w.message,
                suggestion=w.suggestion,
            )
            for w in quality.warnings
        ],
        card_type=quality.card_type.value if quality.card_type else None,
        regenerate_suggestion=quality.regenerate_suggestion,
        split_candidate=quality.split_candidate,
        merge_candidate=quality.merge_candidate,
    )
