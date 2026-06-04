from fastapi import APIRouter, Depends
from mindforge_web.deps import get_facade
from mindforge_web.services.web_facade import WebFacade
from mindforge.cards import iter_cards
from mindforge.topic_presenter import build_topic_view

router = APIRouter(prefix="/api/topics", tags=["topics"])

@router.get("/{topic_name}")
def get_topic(topic_name: str, facade: WebFacade = Depends(get_facade)):
    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    view = build_topic_view(topic_name, scan.cards)
    return view
