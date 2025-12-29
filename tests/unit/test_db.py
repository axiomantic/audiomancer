"""Unit tests for SQLite storage layer (db.py).

Tests all CRUD operations, duplicate handling, batch operations, and pagination.
Uses in-memory SQLite for speed without filesystem dependencies.
"""

import pytest
from datetime import datetime
from typing import cast

from audiomancer.storage.db import SampleStore
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.errors import DuplicateSampleError, StorageError


@pytest.fixture
def store() -> SampleStore:
    """Create in-memory SampleStore for each test.

    Returns fresh database with no data for isolation.
    """
    return SampleStore(":memory:")


@pytest.fixture
def sample_kick() -> SampleMetadata:
    """Sample metadata for a kick drum.

    Returns:
        Complete SampleMetadata with all required fields
    """
    return cast(
        SampleMetadata,
        {
            "id": "smpl_abc12345",
            "file_path": "/samples/kick.wav",
            "file_hash": "abc123def456",
            "duration_ms": 250.5,
            "sample_rate": 44100,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 44100,
            "spectral_centroid": 1500.0,
            "spectral_bandwidth": 800.0,
            "spectral_rolloff": 5000.0,
            "zero_crossing_rate": 0.15,
            "rms_energy": 0.7,
            "dynamic_range": 40.0,
            "bpm": 125.0,
            "bpm_confidence": 0.95,
            "is_loop": True,
            "key": "C",
            "key_confidence": 0.88,
            "tuning_frequency": 440.0,
            "pitch_salience": 0.8,
            "instrument_type": "kick",
            "instrument_confidence": 0.92,
            "mood": ["energetic", "dark"],
            "genre_tags": ["techno", "industrial"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )


@pytest.fixture
def sample_snare() -> SampleMetadata:
    """Sample metadata for a snare drum.

    Returns:
        Complete SampleMetadata with different values than sample_kick
    """
    return cast(
        SampleMetadata,
        {
            "id": "smpl_def67890",
            "file_path": "/samples/snare.wav",
            "file_hash": "def789ghi012",
            "duration_ms": 180.3,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 24,
            "file_size_bytes": 88200,
            "spectral_centroid": 2500.0,
            "bpm": 130.0,
            "bpm_confidence": 0.88,
            "is_loop": False,
            "instrument_type": "snare",
            "instrument_confidence": 0.95,
            "mood": ["aggressive"],
            "genre_tags": ["drum_and_bass"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )


@pytest.fixture
def sample_hihat() -> SampleMetadata:
    """Sample metadata for a hi-hat.

    Returns:
        Minimal SampleMetadata with only required fields
    """
    return cast(
        SampleMetadata,
        {
            "id": "smpl_ghi34567",
            "file_path": "/samples/hihat.wav",
            "file_hash": "ghi345jkl678",
            "duration_ms": 50.0,
            "sample_rate": 48000,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 9600,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )


class TestSampleStoreAdd:
    """Test SampleStore.add() method."""

    def test_add_sample_success(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test adding a sample returns correct ID."""
        sample_id = store.add(sample_kick)
        assert sample_id == "smpl_abc12345"

    def test_add_sample_can_retrieve(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test added sample can be retrieved."""
        sample_id = store.add(sample_kick)
        retrieved = store.get(sample_id)

        assert retrieved is not None
        assert retrieved["id"] == sample_id
        assert retrieved["file_path"] == "/samples/kick.wav"
        assert retrieved["file_hash"] == "abc123def456"
        assert retrieved["duration_ms"] == 250.5
        assert retrieved["sample_rate"] == 44100
        assert retrieved["channels"] == 1

    def test_add_sample_preserves_optional_fields(
        self, store: SampleStore, sample_kick: SampleMetadata
    ):
        """Test optional fields are preserved correctly."""
        store.add(sample_kick)
        retrieved = store.get(sample_kick["id"])

        assert retrieved is not None
        assert retrieved["spectral_centroid"] == 1500.0
        assert retrieved["bpm"] == 125.0
        assert retrieved["is_loop"] is True
        assert retrieved["key"] == "C"
        assert retrieved["instrument_type"] == "kick"
        assert retrieved["mood"] == ["energetic", "dark"]
        assert retrieved["genre_tags"] == ["techno", "industrial"]

    def test_add_sample_minimal_fields(self, store: SampleStore, sample_hihat: SampleMetadata):
        """Test adding sample with only required fields."""
        sample_id = store.add(sample_hihat)
        retrieved = store.get(sample_id)

        assert retrieved is not None
        assert retrieved["id"] == sample_id
        assert "spectral_centroid" not in retrieved
        assert "bpm" not in retrieved
        assert "mood" not in retrieved

    def test_add_duplicate_hash_raises_error(
        self, store: SampleStore, sample_kick: SampleMetadata
    ):
        """Test adding duplicate file_hash raises DuplicateSampleError."""
        store.add(sample_kick)

        # Try to add same hash with different path
        duplicate = sample_kick.copy()
        duplicate["file_path"] = "/different/path.wav"
        duplicate["id"] = "smpl_different"

        with pytest.raises(DuplicateSampleError) as exc_info:
            store.add(duplicate)

        assert exc_info.value.existing_id == "smpl_abc12345"
        assert "already exists" in str(exc_info.value)

    def test_add_duplicate_path_raises_error(
        self, store: SampleStore, sample_kick: SampleMetadata
    ):
        """Test adding duplicate file_path raises StorageError."""
        store.add(sample_kick)

        # Try to add same path with different hash
        duplicate = sample_kick.copy()
        duplicate["file_hash"] = "different_hash"
        duplicate["id"] = "smpl_different"

        # Should fail on path uniqueness constraint
        with pytest.raises(StorageError) as exc_info:
            store.add(duplicate)

        assert "constraint violation" in str(exc_info.value)


class TestSampleStoreAddBatch:
    """Test SampleStore.add_batch() method."""

    def test_add_batch_success(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test batch insert returns all IDs in correct order."""
        samples = [sample_kick, sample_snare, sample_hihat]
        ids = store.add_batch(samples)

        assert len(ids) == 3
        assert ids[0] == "smpl_abc12345"
        assert ids[1] == "smpl_def67890"
        assert ids[2] == "smpl_ghi34567"

    def test_add_batch_all_retrievable(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test all batch-inserted samples can be retrieved."""
        samples = [sample_kick, sample_snare, sample_hihat]
        ids = store.add_batch(samples)

        for sample_id, original in zip(ids, samples):
            retrieved = store.get(sample_id)
            assert retrieved is not None
            assert retrieved["file_path"] == original["file_path"]

    def test_add_batch_duplicate_rolls_back(
        self, store: SampleStore, sample_kick: SampleMetadata, sample_snare: SampleMetadata
    ):
        """Test batch insert with duplicate rolls back entire transaction."""
        # Add first sample
        store.add(sample_kick)

        # Try to batch insert kick (duplicate) + snare (new)
        with pytest.raises(DuplicateSampleError):
            store.add_batch([sample_kick, sample_snare])

        # Verify snare was NOT added (atomic rollback)
        snare_check = store.get(sample_snare["id"])
        assert snare_check is None

        # Verify only kick exists
        assert store.count() == 1

    def test_add_batch_atomic_on_error(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test batch is atomic - no partial commits on failure."""
        # Pre-populate database with kick
        store.add(sample_kick)
        initial_count = store.count()

        # Try to batch insert: snare (new), hihat (new), kick (duplicate)
        with pytest.raises(DuplicateSampleError):
            store.add_batch([sample_snare, sample_hihat, sample_kick])

        # Verify nothing was added (count unchanged)
        assert store.count() == initial_count

        # Verify snare and hihat were NOT added
        assert store.get(sample_snare["id"]) is None
        assert store.get(sample_hihat["id"]) is None


class TestSampleStoreGet:
    """Test SampleStore.get() method."""

    def test_get_existing_sample(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test retrieving existing sample by ID."""
        store.add(sample_kick)
        retrieved = store.get("smpl_abc12345")

        assert retrieved is not None
        assert retrieved["id"] == "smpl_abc12345"

    def test_get_nonexistent_returns_none(self, store: SampleStore):
        """Test retrieving nonexistent sample returns None."""
        result = store.get("smpl_nonexistent")
        assert result is None


class TestSampleStoreGetByPath:
    """Test SampleStore.get_by_path() method."""

    def test_get_by_path_existing(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test retrieving sample by file path."""
        store.add(sample_kick)
        retrieved = store.get_by_path("/samples/kick.wav")

        assert retrieved is not None
        assert retrieved["id"] == "smpl_abc12345"
        assert retrieved["file_path"] == "/samples/kick.wav"

    def test_get_by_path_nonexistent_returns_none(self, store: SampleStore):
        """Test retrieving nonexistent path returns None."""
        result = store.get_by_path("/nonexistent/path.wav")
        assert result is None


class TestSampleStoreGetByHash:
    """Test SampleStore.get_by_hash() method."""

    def test_get_by_hash_existing(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test retrieving sample by file hash."""
        store.add(sample_kick)
        retrieved = store.get_by_hash("abc123def456")

        assert retrieved is not None
        assert retrieved["id"] == "smpl_abc12345"
        assert retrieved["file_hash"] == "abc123def456"

    def test_get_by_hash_nonexistent_returns_none(self, store: SampleStore):
        """Test retrieving nonexistent hash returns None."""
        result = store.get_by_hash("nonexistent_hash")
        assert result is None

    def test_get_by_hash_deduplication_check(
        self, store: SampleStore, sample_kick: SampleMetadata
    ):
        """Test using get_by_hash for deduplication before import."""
        # Simulate import workflow: check before adding
        existing = store.get_by_hash("abc123def456")
        assert existing is None  # Not in database

        # Add sample
        store.add(sample_kick)

        # Check again - now exists
        existing = store.get_by_hash("abc123def456")
        assert existing is not None
        assert existing["id"] == "smpl_abc12345"


class TestSampleStoreUpdate:
    """Test SampleStore.update() method."""

    def test_update_single_field(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test updating a single field."""
        store.add(sample_kick)
        success = store.update("smpl_abc12345", {"bpm": 128.0})

        assert success is True

        retrieved = store.get("smpl_abc12345")
        assert retrieved is not None
        assert retrieved["bpm"] == 128.0

    def test_update_multiple_fields(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test updating multiple fields at once."""
        store.add(sample_kick)
        success = store.update(
            "smpl_abc12345", {"bpm": 130.0, "key": "C#", "instrument_confidence": 0.99}
        )

        assert success is True

        retrieved = store.get("smpl_abc12345")
        assert retrieved is not None
        assert retrieved["bpm"] == 130.0
        assert retrieved["key"] == "C#"
        assert retrieved["instrument_confidence"] == 0.99

    def test_update_preserves_other_fields(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test update only changes specified fields."""
        store.add(sample_kick)
        original_path = sample_kick["file_path"]
        original_hash = sample_kick["file_hash"]

        store.update("smpl_abc12345", {"bpm": 140.0})

        retrieved = store.get("smpl_abc12345")
        assert retrieved is not None
        assert retrieved["file_path"] == original_path
        assert retrieved["file_hash"] == original_hash

    def test_update_nonexistent_returns_false(self, store: SampleStore):
        """Test updating nonexistent sample returns False."""
        success = store.update("smpl_nonexistent", {"bpm": 120.0})
        assert success is False

    def test_update_json_fields(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test updating JSON array fields (mood, genre_tags)."""
        store.add(sample_kick)
        store.update(
            "smpl_abc12345",
            {"mood": ["chill", "ambient"], "genre_tags": ["downtempo", "lofi"]},
        )

        retrieved = store.get("smpl_abc12345")
        assert retrieved is not None
        assert retrieved["mood"] == ["chill", "ambient"]
        assert retrieved["genre_tags"] == ["downtempo", "lofi"]

    def test_update_boolean_field(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test updating boolean is_loop field."""
        store.add(sample_kick)
        store.update("smpl_abc12345", {"is_loop": False})

        retrieved = store.get("smpl_abc12345")
        assert retrieved is not None
        assert retrieved["is_loop"] is False


class TestSampleStoreDelete:
    """Test SampleStore.delete() method."""

    def test_delete_existing_sample(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test deleting an existing sample."""
        store.add(sample_kick)
        success = store.delete("smpl_abc12345")

        assert success is True

        # Verify deletion
        retrieved = store.get("smpl_abc12345")
        assert retrieved is None

    def test_delete_nonexistent_returns_false(self, store: SampleStore):
        """Test deleting nonexistent sample returns False."""
        success = store.delete("smpl_nonexistent")
        assert success is False


class TestSampleStoreSearch:
    """Test SampleStore.search() method."""

    def test_search_no_filters_returns_all(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test search with no filters returns all samples."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])
        results = store.search()

        assert len(results) == 3

    def test_search_by_instrument_type(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test filtering by instrument_type."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])
        results = store.search(instrument_type="kick")

        assert len(results) == 1
        assert results[0]["instrument_type"] == "kick"

    def test_search_by_bpm_range(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
    ):
        """Test filtering by BPM range."""
        store.add_batch([sample_kick, sample_snare])

        # kick=125, snare=130
        results = store.search(bpm_min=120.0, bpm_max=127.0)

        assert len(results) == 1
        assert results[0]["bpm"] == 125.0

    def test_search_by_key(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test filtering by musical key."""
        store.add(sample_kick)
        results = store.search(key="C")

        assert len(results) == 1
        assert results[0]["key"] == "C"

    def test_search_by_path_query(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
    ):
        """Test text search in file path."""
        store.add_batch([sample_kick, sample_snare])

        # Search for "kick" in path
        results = store.search(query="kick")

        assert len(results) == 1
        assert "kick" in results[0]["file_path"]

    def test_search_by_mood(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
    ):
        """Test filtering by mood tags."""
        store.add_batch([sample_kick, sample_snare])

        # kick has ["energetic", "dark"], snare has ["aggressive"]
        results = store.search(mood=["dark"])

        assert len(results) == 1
        assert "dark" in results[0]["mood"]

    def test_search_combined_filters(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
    ):
        """Test combining multiple filters (AND logic)."""
        store.add_batch([sample_kick, sample_snare])

        results = store.search(
            instrument_type="kick", bpm_min=120.0, bpm_max=130.0, key="C"
        )

        assert len(results) == 1
        assert results[0]["instrument_type"] == "kick"
        assert results[0]["key"] == "C"

    def test_search_pagination_limit(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test limit parameter."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])

        results = store.search(limit=2)
        assert len(results) == 2

    def test_search_pagination_offset(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test offset parameter for pagination."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])

        # Get first page
        page1 = store.search(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = store.search(limit=2, offset=2)
        assert len(page2) == 1

        # Ensure no overlap
        page1_ids = {s["id"] for s in page1}
        page2_ids = {s["id"] for s in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_search_no_results(self, store: SampleStore):
        """Test search with no matching results returns empty list."""
        results = store.search(instrument_type="nonexistent")
        assert results == []


class TestSampleStoreCount:
    """Test SampleStore.count() method."""

    def test_count_no_filters(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test count with no filters returns total."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])
        total = store.count()

        assert total == 3

    def test_count_with_filters(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test count respects filters."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])

        # Only kick and snare have instrument_type set
        count = store.count(bpm_min=120.0)
        assert count == 2

    def test_count_for_pagination(
        self,
        store: SampleStore,
        sample_kick: SampleMetadata,
        sample_snare: SampleMetadata,
        sample_hihat: SampleMetadata,
    ):
        """Test using count() to calculate pagination."""
        store.add_batch([sample_kick, sample_snare, sample_hihat])

        total = store.count()
        page_size = 10
        num_pages = (total + page_size - 1) // page_size  # Ceiling division

        assert num_pages == 1  # 3 items, 10 per page = 1 page

    def test_count_empty_database(self, store: SampleStore):
        """Test count on empty database returns 0."""
        total = store.count()
        assert total == 0


class TestSampleStoreEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_database_operations(self, store: SampleStore):
        """Test operations on empty database don't crash."""
        assert store.get("smpl_any") is None
        assert store.get_by_path("/any/path.wav") is None
        assert store.get_by_hash("anyhash") is None
        assert store.delete("smpl_any") is False
        assert store.update("smpl_any", {"bpm": 120}) is False
        assert store.search() == []
        assert store.count() == 0

    def test_add_batch_empty_list(self, store: SampleStore):
        """Test batch insert with empty list."""
        ids = store.add_batch([])
        assert ids == []

    def test_unicode_in_paths(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test handling unicode characters in file paths."""
        sample_kick["file_path"] = "/samples/кик.wav"  # Cyrillic
        sample_kick["file_hash"] = "unicode_hash"
        sample_kick["id"] = "smpl_unicode"

        sample_id = store.add(sample_kick)
        retrieved = store.get(sample_id)

        assert retrieved is not None
        assert retrieved["file_path"] == "/samples/кик.wav"

    def test_large_batch_insert(self, store: SampleStore, sample_kick: SampleMetadata):
        """Test inserting large batch of samples."""
        samples = []
        for i in range(100):
            sample = sample_kick.copy()
            sample["id"] = f"smpl_batch_{i:03d}"
            sample["file_path"] = f"/samples/batch_{i:03d}.wav"
            sample["file_hash"] = f"hash_{i:03d}"
            samples.append(sample)

        ids = store.add_batch(samples)
        assert len(ids) == 100

        # Verify all were added
        assert store.count() == 100

    def test_search_with_none_values(self, store: SampleStore, sample_hihat: SampleMetadata):
        """Test search works when samples have None/NULL fields."""
        # hihat has minimal fields (many are None)
        store.add(sample_hihat)

        # These should not crash even though hihat has no bpm/key/mood
        results = store.search(bpm_min=120.0)
        assert len(results) == 0  # hihat has no BPM

        results = store.search(key="C")
        assert len(results) == 0  # hihat has no key

        results = store.search(mood=["chill"])
        assert len(results) == 0  # hihat has no mood
