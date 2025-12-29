"""Unit tests for SynthStore."""

import pytest
from datetime import datetime

from audiomancer.storage.synth_store import SynthStore
from audiomancer.errors import StorageError


@pytest.fixture
def store():
    """Create in-memory SynthStore for testing."""
    return SynthStore(":memory:")


@pytest.fixture
def sample_synth():
    """Create sample synth metadata for testing."""
    return {
        "id": "synth_abc12345",
        "name": "test_synth",
        "file_path": "/path/to/test.scd",
        "file_hash": "abc123def456",
        "source_code": "SynthDef(\\test, { Out.ar(0, SinOsc.ar(440)) })",
        "controls": [
            {"name": "freq", "default": 440.0},
            {"name": "amp", "default": 0.5},
        ],
        "characteristics": {
            "num_channels": 2,
            "has_gate": True,
            "has_envelope": True,
        },
        "categorization": {
            "category": "lead",
            "tags": ["simple", "test"],
        },
    }


class TestSynthStoreAdd:
    """Tests for SynthStore.add()."""

    def test_add_synth(self, store, sample_synth):
        """Test adding a synth."""
        synth_id = store.add(sample_synth)

        assert synth_id == "synth_abc12345"

        # Verify synth was stored
        retrieved = store.get(synth_id)
        assert retrieved is not None
        assert retrieved["name"] == "test_synth"
        assert retrieved["file_hash"] == "abc123def456"

    def test_add_synth_with_timestamps(self, store, sample_synth):
        """Test that timestamps are added automatically."""
        synth_id = store.add(sample_synth)
        retrieved = store.get(synth_id)

        assert isinstance(retrieved["created_at"], datetime)
        assert isinstance(retrieved["updated_at"], datetime)

    def test_add_duplicate_name(self, store, sample_synth):
        """Test adding synth with duplicate name raises error."""
        store.add(sample_synth)

        # Try to add another synth with same name
        duplicate = sample_synth.copy()
        duplicate["id"] = "synth_different"
        duplicate["file_hash"] = "different_hash"

        with pytest.raises(StorageError) as exc_info:
            store.add(duplicate)

        assert "already exists" in str(exc_info.value)
        assert exc_info.value.details["name"] == "test_synth"

    def test_add_duplicate_hash(self, store, sample_synth):
        """Test adding synth with duplicate hash raises error."""
        store.add(sample_synth)

        # Try to add another synth with same hash
        duplicate = sample_synth.copy()
        duplicate["id"] = "synth_different"
        duplicate["name"] = "different_name"

        with pytest.raises(StorageError) as exc_info:
            store.add(duplicate)

        assert "same content" in str(exc_info.value)
        assert exc_info.value.details["file_hash"] == "abc123def456"

    def test_add_json_serialization(self, store, sample_synth):
        """Test that JSON fields are properly serialized."""
        synth_id = store.add(sample_synth)
        retrieved = store.get(synth_id)

        # Check controls
        assert isinstance(retrieved["controls"], list)
        assert len(retrieved["controls"]) == 2
        assert retrieved["controls"][0]["name"] == "freq"
        assert retrieved["controls"][0]["default"] == 440.0

        # Check characteristics
        assert isinstance(retrieved["characteristics"], dict)
        assert retrieved["characteristics"]["num_channels"] == 2
        assert retrieved["characteristics"]["has_gate"] is True

        # Check categorization
        assert isinstance(retrieved["categorization"], dict)
        assert retrieved["categorization"]["category"] == "lead"
        assert "simple" in retrieved["categorization"]["tags"]


class TestSynthStoreGet:
    """Tests for SynthStore.get() methods."""

    def test_get_by_id(self, store, sample_synth):
        """Test retrieving synth by ID."""
        synth_id = store.add(sample_synth)
        retrieved = store.get(synth_id)

        assert retrieved is not None
        assert retrieved["id"] == synth_id
        assert retrieved["name"] == "test_synth"

    def test_get_nonexistent(self, store):
        """Test retrieving nonexistent synth returns None."""
        result = store.get("synth_nonexistent")
        assert result is None

    def test_get_by_name(self, store, sample_synth):
        """Test retrieving synth by name."""
        store.add(sample_synth)
        retrieved = store.get_by_name("test_synth")

        assert retrieved is not None
        assert retrieved["name"] == "test_synth"
        assert retrieved["id"] == "synth_abc12345"

    def test_get_by_name_nonexistent(self, store):
        """Test retrieving nonexistent synth by name returns None."""
        result = store.get_by_name("nonexistent")
        assert result is None

    def test_get_by_path(self, store, sample_synth):
        """Test retrieving synth by file path."""
        store.add(sample_synth)
        retrieved = store.get_by_path("/path/to/test.scd")

        assert retrieved is not None
        assert retrieved["file_path"] == "/path/to/test.scd"
        assert retrieved["name"] == "test_synth"

    def test_get_by_hash(self, store, sample_synth):
        """Test retrieving synth by file hash."""
        store.add(sample_synth)
        retrieved = store.get_by_hash("abc123def456")

        assert retrieved is not None
        assert retrieved["file_hash"] == "abc123def456"
        assert retrieved["name"] == "test_synth"


class TestSynthStoreUpdate:
    """Tests for SynthStore.update()."""

    def test_update_characteristics(self, store, sample_synth):
        """Test updating synth characteristics."""
        synth_id = store.add(sample_synth)

        success = store.update(
            synth_id,
            {"characteristics": {"num_channels": 4, "has_gate": False}}
        )

        assert success is True

        retrieved = store.get(synth_id)
        assert retrieved["characteristics"]["num_channels"] == 4
        assert retrieved["characteristics"]["has_gate"] is False

    def test_update_categorization(self, store, sample_synth):
        """Test updating synth categorization."""
        synth_id = store.add(sample_synth)

        success = store.update(
            synth_id,
            {"categorization": {"category": "bass", "tags": ["acid", "303"]}}
        )

        assert success is True

        retrieved = store.get(synth_id)
        assert retrieved["categorization"]["category"] == "bass"
        assert "acid" in retrieved["categorization"]["tags"]

    def test_update_timestamp(self, store, sample_synth):
        """Test that update modifies updated_at timestamp."""
        synth_id = store.add(sample_synth)
        original = store.get(synth_id)

        # Small delay to ensure timestamp differs
        import time
        time.sleep(0.01)

        store.update(synth_id, {"characteristics": {"num_channels": 4}})
        updated = store.get(synth_id)

        assert updated["updated_at"] > original["updated_at"]

    def test_update_nonexistent(self, store):
        """Test updating nonexistent synth returns False."""
        success = store.update("synth_nonexistent", {"name": "new_name"})
        assert success is False


class TestSynthStoreDelete:
    """Tests for SynthStore.delete()."""

    def test_delete_synth(self, store, sample_synth):
        """Test deleting a synth."""
        synth_id = store.add(sample_synth)

        success = store.delete(synth_id)
        assert success is True

        # Verify synth is gone
        retrieved = store.get(synth_id)
        assert retrieved is None

    def test_delete_nonexistent(self, store):
        """Test deleting nonexistent synth returns False."""
        success = store.delete("synth_nonexistent")
        assert success is False


class TestSynthStoreSearch:
    """Tests for SynthStore.search()."""

    @pytest.fixture
    def multiple_synths(self, store):
        """Add multiple synths for search testing."""
        synths = [
            {
                "id": "synth_bass1",
                "name": "tb303",
                "file_path": "/synths/tb303.scd",
                "file_hash": "hash1",
                "source_code": "SynthDef(...)",
                "controls": [],
                "characteristics": {"num_channels": 2, "has_gate": True},
                "categorization": {"category": "bass"},
            },
            {
                "id": "synth_lead1",
                "name": "simple_lead",
                "file_path": "/synths/lead.scd",
                "file_hash": "hash2",
                "source_code": "SynthDef(...)",
                "controls": [],
                "characteristics": {"num_channels": 2, "has_gate": True},
                "categorization": {"category": "lead"},
            },
            {
                "id": "synth_pad1",
                "name": "ambient_pad",
                "file_path": "/synths/pad.scd",
                "file_hash": "hash3",
                "source_code": "SynthDef(...)",
                "controls": [],
                "characteristics": {"num_channels": 2, "has_gate": True},
                "categorization": {"category": "pad"},
            },
            {
                "id": "synth_drum1",
                "name": "kick",
                "file_path": "/synths/kick.scd",
                "file_hash": "hash4",
                "source_code": "SynthDef(...)",
                "controls": [],
                "characteristics": {"num_channels": 2, "has_gate": False},
                "categorization": {"category": "drum"},
            },
        ]

        for synth in synths:
            store.add(synth)

        return store

    def test_search_all(self, multiple_synths):
        """Test searching without filters returns all synths."""
        results = multiple_synths.search()
        assert len(results) == 4

    def test_search_by_category(self, multiple_synths):
        """Test searching by category."""
        results = multiple_synths.search(category="bass")
        assert len(results) == 1
        assert results[0]["name"] == "tb303"

    def test_search_by_query(self, multiple_synths):
        """Test text search in name and path."""
        results = multiple_synths.search(query="lead")
        assert len(results) == 1
        assert results[0]["name"] == "simple_lead"

    def test_search_by_has_gate(self, multiple_synths):
        """Test searching by gate parameter presence."""
        results = multiple_synths.search(has_gate=False)
        assert len(results) == 1
        assert results[0]["name"] == "kick"

        results_with_gate = multiple_synths.search(has_gate=True)
        assert len(results_with_gate) == 3

    def test_search_pagination(self, multiple_synths):
        """Test search pagination."""
        page1 = multiple_synths.search(limit=2, offset=0)
        page2 = multiple_synths.search(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        # Ensure no overlap
        page1_ids = {s["id"] for s in page1}
        page2_ids = {s["id"] for s in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_count(self, multiple_synths):
        """Test counting synths."""
        total = multiple_synths.count()
        assert total == 4

        bass_count = multiple_synths.count(category="bass")
        assert bass_count == 1

        with_gate = multiple_synths.count(has_gate=True)
        assert with_gate == 3


class TestSynthLineage:
    """Tests for synth lineage tracking."""

    def test_add_lineage(self, store, sample_synth):
        """Test adding synth lineage."""
        # Add parent synth
        parent_id = store.add(sample_synth)

        # Add child synth
        child = sample_synth.copy()
        child["id"] = "synth_child"
        child["name"] = "child_synth"
        child["file_path"] = "/path/to/child.scd"
        child["file_hash"] = "child_hash"
        child_id = store.add(child)

        # Record lineage
        store.add_lineage(child_id, parent_id, 0.8)

        # Verify lineage
        lineages = store.get_lineage(child_id)
        assert len(lineages) == 1
        assert lineages[0]["parent_synth_id"] == parent_id
        assert lineages[0]["contribution_weight"] == 0.8

    def test_add_lineage_nonexistent_synth(self, store):
        """Test adding lineage for nonexistent synth raises error."""
        with pytest.raises(StorageError) as exc_info:
            store.add_lineage("synth_nonexistent", "synth_parent", 0.5)

        assert "not found" in str(exc_info.value)

    def test_add_lineage_nonexistent_parent(self, store, sample_synth):
        """Test adding lineage with nonexistent parent raises error."""
        synth_id = store.add(sample_synth)

        with pytest.raises(StorageError) as exc_info:
            store.add_lineage(synth_id, "synth_nonexistent_parent", 0.5)

        assert "Parent synth not found" in str(exc_info.value)

    def test_get_lineage_empty(self, store, sample_synth):
        """Test getting lineage for synth with no parents."""
        synth_id = store.add(sample_synth)
        lineages = store.get_lineage(synth_id)

        assert lineages == []

    def test_multiple_parents(self, store, sample_synth):
        """Test synth with multiple parents."""
        # Add parent synths
        parent1_id = store.add(sample_synth)

        parent2 = sample_synth.copy()
        parent2["id"] = "synth_parent2"
        parent2["name"] = "parent2"
        parent2["file_path"] = "/path/to/parent2.scd"
        parent2["file_hash"] = "hash2"
        parent2_id = store.add(parent2)

        # Add child
        child = sample_synth.copy()
        child["id"] = "synth_child"
        child["name"] = "child"
        child["file_path"] = "/path/to/child.scd"
        child["file_hash"] = "hash_child"
        child_id = store.add(child)

        # Record lineage from both parents
        store.add_lineage(child_id, parent1_id, 0.6)
        store.add_lineage(child_id, parent2_id, 0.4)

        # Verify both lineages
        lineages = store.get_lineage(child_id)
        assert len(lineages) == 2

        parent_ids = {l["parent_synth_id"] for l in lineages}
        assert parent1_id in parent_ids
        assert parent2_id in parent_ids
