"""CollectionStore CRUD tests — Collections JSON sidecar persistence."""

from __future__ import annotations

from pathlib import Path

from mindforge.services.collection_store import Collection, CollectionStore


def _make_collection(**overrides) -> Collection:
    kwargs = {
        "id": "my-collection",
        "name": "My Collection",
        "description": "",
        "card_refs": (),
        "rule_tags": (),
        "created_at": "",
    }
    kwargs.update(overrides)
    return Collection(**kwargs)


class TestCollectionStore:
    def test_list_collections_empty(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        assert store.list_collections() == []

    def test_create_and_list_collections(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="col-a", name="Collection A"))
        store.create_collection(_make_collection(id="col-b", name="Collection B",
                                                   description="Second collection"))
        cols = store.list_collections()
        assert len(cols) == 2
        assert {c.id for c in cols} == {"col-a", "col-b"}

    def test_create_collection_sets_created_at(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        col = store.create_collection(_make_collection(id="c1", name="C1"))
        assert col.created_at != ""

    def test_get_collection(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="c1", name="Found"))
        found = store.get_collection("c1")
        assert found is not None
        assert found.name == "Found"

    def test_get_nonexistent_collection(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        assert store.get_collection("nonexistent") is None

    def test_add_cards(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="c1", name="C1"))
        col = store.add_cards("c1", ["card-1", "card-2"])
        assert col is not None
        assert set(col.card_refs) == {"card-1", "card-2"}

    def test_add_cards_deduplicates(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="c1", name="C1",
                                                   card_refs=("card-1",)))
        col = store.add_cards("c1", ["card-1", "card-2"])
        assert col is not None
        assert set(col.card_refs) == {"card-1", "card-2"}

    def test_add_cards_nonexistent_collection(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        assert store.add_cards("nonexistent", ["card-1"]) is None

    def test_remove_cards(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="c1", name="C1",
                                                   card_refs=("card-1", "card-2", "card-3")))
        col = store.remove_cards("c1", ["card-2"])
        assert col is not None
        assert set(col.card_refs) == {"card-1", "card-3"}

    def test_remove_cards_nonexistent_collection(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        assert store.remove_cards("nonexistent", ["card-1"]) is None

    def test_delete_collection(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="c1", name="C1"))
        store.create_collection(_make_collection(id="c2", name="C2"))
        assert store.delete_collection("c1") is True
        cols = store.list_collections()
        assert len(cols) == 1
        assert cols[0].id == "c2"

    def test_delete_nonexistent_collection(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        assert store.delete_collection("nonexistent") is False

    def test_collection_to_dict_roundtrip(self) -> None:
        original = _make_collection(
            id="test-1", name="Test", description="A test collection",
            card_refs=("card-1", "card-2"), rule_tags=("tag-a", "tag-b"),
        )
        restored = Collection.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.card_refs == original.card_refs
        assert restored.rule_tags == original.rule_tags

    def test_collections_json_path(self, tmp_path: Path) -> None:
        store = CollectionStore(tmp_path)
        store.create_collection(_make_collection(id="c1"))
        assert (tmp_path / ".mindforge" / "collections.json").exists()
