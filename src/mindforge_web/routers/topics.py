"""Topics API —— runtime topic 视图。

v0.5: TopicPresenter 驱动的 API。只返回 human_approved 卡片的安全视图。
"""

from fastapi import APIRouter, Depends, HTTPException

from mindforge.cards import iter_cards
from mindforge.topic_presenter import build_topic_view, list_topics
from mindforge_web.deps import get_facade
from mindforge_web.schemas import TopicListResponse, TopicViewResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=TopicListResponse)
def list_all_topics(facade: WebFacade = Depends(get_facade)):
    """列出所有包含 human_approved 卡片的 topic 名称。"""
    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    topics = list_topics(scan.cards)
    return TopicListResponse(topics=topics)


@router.get("/{topic_name}", response_model=TopicViewResponse)
def get_topic(topic_name: str, facade: WebFacade = Depends(get_facade)):
    """获取指定 topic 的运行时视图（仅 human_approved 卡片）。"""
    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    view = build_topic_view(topic_name, scan.cards)

    if view["total_approved_cards"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{topic_name}' not found or has no approved cards",
        )

    return TopicViewResponse(**view)
