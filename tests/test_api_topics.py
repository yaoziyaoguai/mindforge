from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from pathlib import Path

from mindforge_web.app import create_app
from mindforge_web.deps import get_facade

@pytest.fixture
def mock_facade():
    facade = MagicMock()
    # Ensure it has basic cfg
    facade.cfg.vault.root = Path("/fake/root")
    facade.cfg.vault.cards_dir = "cards"
    return facade

@pytest.fixture
def client(mock_facade):
    app = create_app()
    app.dependency_overrides[get_facade] = lambda: mock_facade
    return TestClient(app)

def test_get_topic_view(client, mock_facade, monkeypatch):
    # Setup mock iter_cards and build_topic_view since topics router uses them
    mock_scan = MagicMock()
    mock_scan.cards = []
    
    def mock_iter_cards(root, cards_dir):
        return mock_scan
        
    def mock_build_topic_view(topic, cards):
        return {
            "topic": topic,
            "total_approved_cards": 0,
            "type_counts": {},
            "cards": []
        }
        
    monkeypatch.setattr("mindforge_web.routers.topics.iter_cards", mock_iter_cards)
    monkeypatch.setattr("mindforge_web.routers.topics.build_topic_view", mock_build_topic_view)
    
    response = client.get("/api/topics/TestTopic")
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert data["topic"] == "TestTopic"
    assert "cards" in data
