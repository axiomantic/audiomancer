"""Integration tests for unified storage layer.

Tests atomic operations across SQLite and LanceDB to ensure data consistency
and proper rollback on errors.
"""

from datetime import datetime
from pathlib import Path
import tempfile
import pytest

from audiomancer.errors import DuplicateSampleError, SampleNotFoundError, StorageError
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.storage.unified import UnifiedSampleStorage


@pytest.fixture
def temp_storage():
    """Create temporary unified storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        db_path = tmppath / "test_samples.db"
        embeddings_path = tmppath / "embeddings"

        storage = UnifiedSampleStorage(
            db_path=db_path,
            embeddings_path=embeddings_path
        )
        yield storage


def make_sample(sample_id: str, file_hash: str, file_path: str = "/test/sample.wav") -> SampleMetadata:
    """Create test sample metadata."""
    return SampleMetadata(
        id=sample_id,
        file_path=file_path,
        file_hash=file_hash,
        duration_ms=250.5,
        sample_rate=44100,
        channels=1,
        bit_depth=16,
        file_size_bytes=44100,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_embedding(base: float = 0.1) -> list[float]:
    """Create 128-dim test embedding."""
    return [base] * 128


class TestAtomicAdd:
    """Test atomic add operations."""

    def test_add_sample_with_embedding_success(self, temp_storage):
        """Both sample and embedding are added together with correct values."""
        sample = make_sample("smpl_abc123", "hash123")
        embedding = make_embedding(0.1)

        sample_id = temp_storage.add_sample_with_embedding(sample, embedding)

        # Verify sample ID
        assert sample_id == "smpl_abc123"

        # Verify sample data, not just existence
        retrieved_sample = temp_storage.sample_store.get(sample_id)
        assert retrieved_sample is not None
        assert retrieved_sample["file_hash"] == "hash123"
        assert retrieved_sample["duration_ms"] == 250.5

        # Verify embedding values, not just existence
        retrieved_emb = temp_storage.vector_store.get_embedding(sample_id)
        assert retrieved_emb is not None
        assert len(retrieved_emb) == 128
        assert retrieved_emb[0] == pytest.approx(0.1, abs=0.01)

    def test_add_rollback_on_invalid_embedding(self, temp_storage):
        """Sample is rolled back if embedding validation fails."""
        sample = make_sample("smpl_abc123", "hash123")
        invalid_embedding = [0.1] * 127  # Wrong dimension

        # Should raise ValueError for invalid embedding
        with pytest.raises(StorageError) as exc_info:
            temp_storage.add_sample_with_embedding(sample, invalid_embedding)

        assert "Invalid embedding" in str(exc_info.value)

        # Verify sample was rolled back (not in database)
        assert temp_storage.sample_store.get("smpl_abc123") is None
        assert temp_storage.vector_store.get_embedding("smpl_abc123") is None

    def test_add_rollback_on_duplicate_sample(self, temp_storage):
        """Duplicate sample error propagates without adding embedding."""
        sample1 = make_sample("smpl_abc123", "hash123")
        embedding1 = make_embedding(0.1)

        # Add first sample
        temp_storage.add_sample_with_embedding(sample1, embedding1)

        # Try to add duplicate with different ID but same hash
        sample2 = make_sample("smpl_def456", "hash123")  # Same hash!
        embedding2 = make_embedding(0.2)

        # Should raise DuplicateSampleError
        with pytest.raises(DuplicateSampleError):
            temp_storage.add_sample_with_embedding(sample2, embedding2)

        # Verify only first sample exists
        assert temp_storage.sample_store.get("smpl_abc123") is not None
        assert temp_storage.sample_store.get("smpl_def456") is None

        # Verify only first embedding exists
        assert temp_storage.vector_store.get_embedding("smpl_abc123") is not None
        assert temp_storage.vector_store.get_embedding("smpl_def456") is None


class TestAtomicBatch:
    """Test atomic batch operations."""

    def test_batch_add_success(self, temp_storage):
        """All samples and embeddings added atomically with correct values."""
        items = [
            (make_sample("smpl_abc123", "hash1", "/test/kick1.wav"), make_embedding(0.1)),
            (make_sample("smpl_def456", "hash2", "/test/kick2.wav"), make_embedding(0.2)),
            (make_sample("smpl_ghi789", "hash3", "/test/kick3.wav"), make_embedding(0.3)),
        ]

        sample_ids = temp_storage.add_samples_with_embeddings_batch(items)

        # Verify all added
        assert len(sample_ids) == 3
        assert sample_ids == ["smpl_abc123", "smpl_def456", "smpl_ghi789"]

        # Verify samples with correct values (spot check first item)
        retrieved_sample = temp_storage.sample_store.get("smpl_abc123")
        assert retrieved_sample is not None
        assert retrieved_sample["file_hash"] == "hash1"
        assert retrieved_sample["file_path"] == "/test/kick1.wav"

        # Verify embeddings with correct values
        for (sample, expected_emb), sample_id in zip(items, sample_ids):
            retrieved_emb = temp_storage.vector_store.get_embedding(sample_id)
            assert retrieved_emb is not None
            assert len(retrieved_emb) == 128
            assert retrieved_emb[0] == pytest.approx(expected_emb[0], abs=0.01)

    def test_batch_rollback_on_invalid_embedding(self, temp_storage):
        """Entire batch rolled back if any embedding invalid."""
        items = [
            (make_sample("smpl_abc123", "hash1"), make_embedding(0.1)),
            (make_sample("smpl_def456", "hash2"), [0.2] * 127),  # Invalid!
            (make_sample("smpl_ghi789", "hash3"), make_embedding(0.3)),
        ]

        # Should raise StorageError
        with pytest.raises(StorageError) as exc_info:
            temp_storage.add_samples_with_embeddings_batch(items)

        assert "Invalid embedding in batch" in str(exc_info.value)

        # Verify NO samples were added (atomic rollback)
        assert temp_storage.sample_store.get("smpl_abc123") is None
        assert temp_storage.sample_store.get("smpl_def456") is None
        assert temp_storage.sample_store.get("smpl_ghi789") is None

        # Verify NO embeddings were added
        assert temp_storage.vector_store.get_embedding("smpl_abc123") is None
        assert temp_storage.vector_store.get_embedding("smpl_def456") is None
        assert temp_storage.vector_store.get_embedding("smpl_ghi789") is None

    def test_batch_rollback_on_duplicate(self, temp_storage):
        """Entire batch rolled back on duplicate sample."""
        # Add first sample
        sample1 = make_sample("smpl_abc123", "hash1")
        embedding1 = make_embedding(0.1)
        temp_storage.add_sample_with_embedding(sample1, embedding1)

        # Try batch with duplicate hash
        items = [
            (make_sample("smpl_def456", "hash2"), make_embedding(0.2)),
            (make_sample("smpl_ghi789", "hash1"), make_embedding(0.3)),  # Duplicate hash!
        ]

        # Should raise DuplicateSampleError
        with pytest.raises(DuplicateSampleError):
            temp_storage.add_samples_with_embeddings_batch(items)

        # Verify original sample still exists
        assert temp_storage.sample_store.get("smpl_abc123") is not None

        # Verify new samples were NOT added
        assert temp_storage.sample_store.get("smpl_def456") is None
        assert temp_storage.sample_store.get("smpl_ghi789") is None

        # Verify no orphaned embeddings
        assert temp_storage.vector_store.get_embedding("smpl_def456") is None
        assert temp_storage.vector_store.get_embedding("smpl_ghi789") is None


class TestDelete:
    """Test delete operations."""

    def test_delete_removes_from_both_stores(self, temp_storage):
        """Delete removes sample and embedding."""
        sample = make_sample("smpl_abc123", "hash123")
        embedding = make_embedding(0.1)
        temp_storage.add_sample_with_embedding(sample, embedding)

        # Delete
        result = temp_storage.delete_sample("smpl_abc123")

        # Verify deleted from both stores
        assert result is True
        assert temp_storage.sample_store.get("smpl_abc123") is None
        assert temp_storage.vector_store.get_embedding("smpl_abc123") is None

    def test_delete_nonexistent_returns_false(self, temp_storage):
        """Delete of nonexistent sample returns False."""
        result = temp_storage.delete_sample("smpl_nonexistent")
        assert result is False

    def test_delete_orphaned_embedding_cleanup(self, temp_storage):
        """Delete cleans up orphaned embeddings."""
        # Manually create orphaned embedding (bypass unified storage)
        temp_storage.vector_store.add_embedding("smpl_orphan", make_embedding(0.1))

        # Delete should clean up embedding even though sample doesn't exist
        result = temp_storage.delete_sample("smpl_orphan")

        # Returns False because sample wasn't in metadata store
        assert result is False

        # But embedding should be cleaned up
        assert temp_storage.vector_store.get_embedding("smpl_orphan") is None


class TestFindSimilar:
    """Test similarity search."""

    def test_find_similar_returns_correct_samples(self, temp_storage):
        """Find similar returns samples sorted by distance."""
        # Add samples with different embeddings
        items = [
            (make_sample("smpl_query", "hash0", "/test/query.wav"), [0.5] * 128),
            (make_sample("smpl_similar1", "hash1", "/test/sim1.wav"), [0.51] * 128),
            (make_sample("smpl_similar2", "hash2", "/test/sim2.wav"), [0.52] * 128),
            (make_sample("smpl_different", "hash3", "/test/diff.wav"), [0.9] * 128),
        ]
        temp_storage.add_samples_with_embeddings_batch(items)

        # Find similar to query
        results = temp_storage.find_similar("smpl_query", limit=3, exclude_self=True)

        # Should return 3 results (excluding query itself)
        assert len(results) == 3

        # Results should be (sample, distance) tuples
        for sample, distance in results:
            assert isinstance(sample, dict)
            assert isinstance(distance, float)

        # Distances should be ascending (most similar first)
        distances = [distance for _, distance in results]
        assert distances == sorted(distances)

        # Most similar should be smpl_similar1 or smpl_similar2
        most_similar_id = results[0][0]["id"]
        assert most_similar_id in ["smpl_similar1", "smpl_similar2"]

    def test_find_similar_excludes_self(self, temp_storage):
        """Find similar excludes query sample when exclude_self=True."""
        sample = make_sample("smpl_query", "hash0")
        embedding = make_embedding(0.5)
        temp_storage.add_sample_with_embedding(sample, embedding)

        # Find similar (with exclude_self=True)
        results = temp_storage.find_similar("smpl_query", limit=10, exclude_self=True)

        # Query sample should not be in results
        result_ids = [s["id"] for s, _ in results]
        assert "smpl_query" not in result_ids

    def test_find_similar_includes_self_when_disabled(self, temp_storage):
        """Find similar includes query sample when exclude_self=False."""
        sample = make_sample("smpl_query", "hash0")
        embedding = make_embedding(0.5)
        temp_storage.add_sample_with_embedding(sample, embedding)

        # Find similar (with exclude_self=False)
        results = temp_storage.find_similar("smpl_query", limit=10, exclude_self=False)

        # Query sample should be in results (distance = 0)
        assert len(results) >= 1
        assert results[0][0]["id"] == "smpl_query"
        assert results[0][1] == 0.0  # Exact match

    def test_find_similar_raises_on_missing_embedding(self, temp_storage):
        """Find similar raises SampleNotFoundError if no embedding."""
        # Add sample without embedding (bypass unified storage)
        sample = make_sample("smpl_no_embedding", "hash123")
        temp_storage.sample_store.add(sample)

        # Should raise SampleNotFoundError
        with pytest.raises(SampleNotFoundError) as exc_info:
            temp_storage.find_similar("smpl_no_embedding", limit=10)

        assert "No embedding found" in str(exc_info.value)


class TestCombinedSearch:
    """Test combined text and similarity search."""

    def test_similarity_search_only(self, temp_storage):
        """Search with only embedding returns similar samples."""
        items = [
            (make_sample("smpl_abc123", "hash1", "/test/kick1.wav"), [0.5] * 128),
            (make_sample("smpl_def456", "hash2", "/test/kick2.wav"), [0.51] * 128),
            (make_sample("smpl_ghi789", "hash3", "/test/snare.wav"), [0.9] * 128),
        ]
        temp_storage.add_samples_with_embeddings_batch(items)

        # Search by similarity only
        query_emb = [0.5] * 128
        results = temp_storage.search_by_text_and_similarity(
            query_embedding=query_emb,
            limit=2
        )

        assert len(results) == 2
        # Most similar should be returned
        assert results[0]["id"] in ["smpl_abc123", "smpl_def456"]

    def test_text_search_only(self, temp_storage):
        """Search with only text returns filtered samples."""
        items = [
            (make_sample("smpl_kick1", "hash1", "/test/kick1.wav"), make_embedding(0.1)),
            (make_sample("smpl_kick2", "hash2", "/test/kick2.wav"), make_embedding(0.2)),
            (make_sample("smpl_snare", "hash3", "/test/snare.wav"), make_embedding(0.3)),
        ]
        temp_storage.add_samples_with_embeddings_batch(items)

        # Search by text only
        results = temp_storage.search_by_text_and_similarity(
            text_query="kick",
            limit=10
        )

        assert len(results) == 2
        result_ids = {s["id"] for s in results}
        assert result_ids == {"smpl_kick1", "smpl_kick2"}

    def test_combined_search_intersects_results(self, temp_storage):
        """Combined search returns samples matching both criteria."""
        items = [
            (make_sample("smpl_kick1", "hash1", "/test/kick1.wav"), [0.5] * 128),
            (make_sample("smpl_kick2", "hash2", "/test/kick2.wav"), [0.51] * 128),
            (make_sample("smpl_snare", "hash3", "/test/snare.wav"), [0.52] * 128),  # Similar but not kick
        ]
        temp_storage.add_samples_with_embeddings_batch(items)

        # Search by both similarity AND text
        query_emb = [0.5] * 128
        results = temp_storage.search_by_text_and_similarity(
            query_embedding=query_emb,
            text_query="kick",
            limit=10
        )

        # Should only return kicks (text filter) that are similar (embedding)
        assert len(results) == 2
        result_ids = {s["id"] for s in results}
        assert result_ids == {"smpl_kick1", "smpl_kick2"}

    def test_search_raises_on_no_query(self, temp_storage):
        """Search raises ValueError if no query provided."""
        with pytest.raises(ValueError) as exc_info:
            temp_storage.search_by_text_and_similarity(limit=10)

        assert "Must provide query_embedding or text_query" in str(exc_info.value)


class TestConvenienceMethods:
    """Test convenience wrapper methods."""

    def test_get_sample(self, temp_storage):
        """get_sample returns sample metadata."""
        sample = make_sample("smpl_abc123", "hash123")
        embedding = make_embedding(0.1)
        temp_storage.add_sample_with_embedding(sample, embedding)

        retrieved = temp_storage.get_sample("smpl_abc123")
        assert retrieved is not None
        assert retrieved["id"] == "smpl_abc123"

    def test_get_embedding(self, temp_storage):
        """get_embedding returns embedding vector."""
        sample = make_sample("smpl_abc123", "hash123")
        embedding = make_embedding(0.1)
        temp_storage.add_sample_with_embedding(sample, embedding)

        retrieved = temp_storage.get_embedding("smpl_abc123")
        assert retrieved is not None
        assert len(retrieved) == 128

    def test_update_sample(self, temp_storage):
        """update_sample updates metadata only."""
        sample = make_sample("smpl_abc123", "hash123")
        embedding = make_embedding(0.1)
        temp_storage.add_sample_with_embedding(sample, embedding)

        # Update metadata
        success = temp_storage.update_sample("smpl_abc123", {"bpm": 128.0})
        assert success is True

        # Verify update
        updated = temp_storage.get_sample("smpl_abc123")
        assert updated["bpm"] == 128.0

        # Embedding should be unchanged (within float32 precision)
        emb = temp_storage.get_embedding("smpl_abc123")
        assert len(emb) == 128
        # Check approximate equality (float32 precision)
        for i, (a, b) in enumerate(zip(emb, embedding)):
            assert abs(a - b) < 1e-6, f"Embedding mismatch at index {i}: {a} != {b}"
