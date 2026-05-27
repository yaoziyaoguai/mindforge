"""ViewStore CRUD tests — Saved Views JSON sidecar persistence."""

from __future__ import annotations

from pathlib import Path

from mindforge.services.view_store import SavedView, ViewStore


def _make_view(**overrides) -> SavedView:
    kwargs = {
        "id": "my-view",
        "name": "My View",
        "status_filter": "all",
        "track_filter": "all",
        "source_type_filter": "all",
        "quality_filter": "all",
        "sort_by": "newest",
    }
    kwargs.update(overrides)
    return SavedView(**kwargs)


class TestViewStore:
    def test_list_views_empty(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        assert store.list_views() == []

    def test_save_and_list_views(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        store.save_view(_make_view(id="high-quality", name="High Quality",
                                    quality_filter="high", sort_by="quality"))
        store.save_view(_make_view(id="recent", name="Recent Drafts",
                                    status_filter="ai_draft", sort_by="newest"))
        views = store.list_views()
        assert len(views) == 2
        assert {v.id for v in views} == {"high-quality", "recent"}

    def test_save_view_idempotent_update(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        store.save_view(_make_view(id="v1", name="Original"))
        store.save_view(_make_view(id="v1", name="Updated", sort_by="oldest"))
        views = store.list_views()
        assert len(views) == 1
        assert views[0].name == "Updated"
        assert views[0].sort_by == "oldest"

    def test_delete_view(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        store.save_view(_make_view(id="v1", name="One"))
        store.save_view(_make_view(id="v2", name="Two"))
        assert store.delete_view("v1") is True
        views = store.list_views()
        assert len(views) == 1
        assert views[0].id == "v2"

    def test_delete_nonexistent_view(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        assert store.delete_view("nonexistent") is False

    def test_saved_view_to_dict_roundtrip(self) -> None:
        original = _make_view(id="test-1", name="Test", status_filter="human_approved",
                               track_filter="tech", source_type_filter="markdown",
                               quality_filter="high", sort_by="quality")
        restored = SavedView.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.status_filter == original.status_filter
        assert restored.track_filter == original.track_filter
        assert restored.quality_filter == original.quality_filter
        assert restored.sort_by == original.sort_by

    def test_created_at_preserved_on_update(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        first = store.save_view(_make_view(id="v1", name="First"))
        second = store.save_view(_make_view(id="v1", name="Second"))
        assert first.created_at == second.created_at

    def test_views_json_path(self, tmp_path: Path) -> None:
        store = ViewStore(tmp_path)
        store.save_view(_make_view(id="v1"))
        assert (tmp_path / ".mindforge" / "views.json").exists()
