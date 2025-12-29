"""Unit tests for LanceDB vector storage.

Tests the VectorStore implementation to ensure:
- Dimension validation (must be exactly 128)
- Search returns results sorted by distance
- Exclusion filters work correctly
- Pagination (offset + limit) functions properly
- Batch operations are efficient and atomic
- Distance metrics (cosine, L2) work as expected
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from audiomancer.storage.vectors import LanceDBVectorStore


@pytest.fixture
def temp_db_path():
    """Create temporary directory for LanceDB."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def vector_store(temp_db_path):
    """Create fresh LanceDB vector store for each test."""
    return LanceDBVectorStore(temp_db_path)


class TestDimensionValidation:
    """Test that embedding dimensions are strictly validated."""

    def test_add_embedding_wrong_dimension_127(self, vector_store):
        """Embedding with 127 dimensions raises ValueError."""
        embedding_127 = [0.1] * 127

        with pytest.raises(ValueError) as exc_info:
            vector_store.add_embedding("smpl_abc123", embedding_127)

        assert "must be 128" in str(exc_info.value)
        assert "got 127" in str(exc_info.value)

    def test_add_embedding_wrong_dimension_129(self, vector_store):
        """Embedding with 129 dimensions raises ValueError."""
        embedding_129 = [0.1] * 129

        with pytest.raises(ValueError) as exc_info:
            vector_store.add_embedding("smpl_abc123", embedding_129)

        assert "must be 128" in str(exc_info.value)
        assert "got 129" in str(exc_info.value)

    def test_add_embedding_correct_dimension(self, vector_store):
        """Embedding with exactly 128 dimensions succeeds."""
        embedding_128 = [0.1] * 128

        # Should not raise
        vector_store.add_embedding("smpl_abc123", embedding_128)

        retrieved = vector_store.get_embedding("smpl_abc123")
        assert len(retrieved) == 128

    def test_batch_add_wrong_dimension(self, vector_store):
        """Batch with any wrong dimension raises ValueError."""
        items = [
            ("smpl_abc123", [0.1] * 128),  # Correct
            ("smpl_def456", [0.2] * 127),  # Wrong - 127 dims
            ("smpl_ghi789", [0.3] * 128),  # Correct
        ]

        with pytest.raises(ValueError) as exc_info:
            vector_store.add_embeddings_batch(items)

        assert "must be 128" in str(exc_info.value)

        # No partial commits - first item should not exist
        assert vector_store.get_embedding("smpl_abc123") is None

    def test_search_wrong_dimension(self, vector_store):
        """Search with wrong query dimension raises ValueError."""
        # Add valid embedding first
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)

        # Search with wrong dimension
        query_127 = [0.5] * 127

        with pytest.raises(ValueError) as exc_info:
            vector_store.search_similar(query_127)

        assert "must be 128" in str(exc_info.value)


class TestSearchOrdering:
    """Test that search results are sorted by distance (ascending)."""

    def test_search_returns_ascending_distance(self, vector_store):
        """Search results sorted by distance (most similar first)."""
        # Add embeddings with different similarities to query
        vector_store.add_embedding("smpl_exact", [1.0] * 128)  # Exact match
        vector_store.add_embedding("smpl_close", [0.9] + [1.0] * 127)  # Very close
        vector_store.add_embedding("smpl_far", [0.0] * 128)  # Opposite

        query = [1.0] * 128
        results = vector_store.search_similar(query, limit=3)

        # Verify we got all three
        assert len(results) == 3

        # Verify distances are ascending (most similar first)
        distances = [dist for _, dist in results]
        assert distances == sorted(distances), "Results not sorted by distance"

        # Exact match should be first (distance ~0)
        assert results[0][0] == "smpl_exact"
        assert results[0][1] < 0.01, f"Expected distance ~0, got {results[0][1]}"

    def test_search_cosine_distance_range(self, vector_store):
        """Cosine distance is in range [0, 2]."""
        vector_store.add_embedding("smpl_same", [1.0] + [0.0] * 127)
        vector_store.add_embedding("smpl_opposite", [-1.0] + [0.0] * 127)

        query = [1.0] + [0.0] * 127
        results = vector_store.search_similar(query, limit=2, distance_metric="cosine")

        # All distances should be in [0, 2]
        for _, distance in results:
            assert 0 <= distance <= 2, f"Cosine distance {distance} out of range"

    def test_search_l2_distance(self, vector_store):
        """L2 distance metric works and returns sorted results."""
        vector_store.add_embedding("smpl_close", [1.0, 1.0] + [0.0] * 126)
        vector_store.add_embedding("smpl_far", [5.0, 5.0] + [0.0] * 126)

        query = [1.0, 1.0] + [0.0] * 126
        results = vector_store.search_similar(query, limit=2, distance_metric="l2")

        # Verify ascending distance
        assert results[0][1] < results[1][1]

        # Close should be first
        assert results[0][0] == "smpl_close"


class TestExcludeIds:
    """Test that exclude_ids filter works correctly."""

    def test_exclude_single_id(self, vector_store):
        """Excluded ID is not in results."""
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)
        vector_store.add_embedding("smpl_def456", [0.2] * 128)
        vector_store.add_embedding("smpl_ghi789", [0.3] * 128)

        query = [0.1] * 128
        results = vector_store.search_similar(
            query,
            limit=3,
            exclude_ids=["smpl_abc123"]
        )

        # Should get 2 results (excluded smpl_abc123)
        assert len(results) == 2

        # Excluded ID should not appear
        result_ids = [sample_id for sample_id, _ in results]
        assert "smpl_abc123" not in result_ids

    def test_exclude_multiple_ids(self, vector_store):
        """Multiple excluded IDs are all filtered out."""
        for i in range(5):
            vector_store.add_embedding(f"smpl_{i}", [0.1 * i] * 128)

        query = [0.1] * 128
        results = vector_store.search_similar(
            query,
            limit=5,
            exclude_ids=["smpl_0", "smpl_1", "smpl_2"]
        )

        # Should get 2 results (excluded 3)
        assert len(results) == 2

        # None of excluded IDs should appear
        result_ids = [sample_id for sample_id, _ in results]
        assert "smpl_0" not in result_ids
        assert "smpl_1" not in result_ids
        assert "smpl_2" not in result_ids

    def test_exclude_all_results(self, vector_store):
        """Excluding all matches returns empty list."""
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)
        vector_store.add_embedding("smpl_def456", [0.2] * 128)

        query = [0.1] * 128
        results = vector_store.search_similar(
            query,
            limit=5,
            exclude_ids=["smpl_abc123", "smpl_def456"]
        )

        assert results == []


class TestPagination:
    """Test offset and limit for pagination."""

    def test_pagination_offset_limit(self, vector_store):
        """Offset skips results, limit caps results."""
        # Add 10 embeddings
        for i in range(10):
            vector_store.add_embedding(f"smpl_{i:02d}", [0.1 * i] * 128)

        query = [0.5] * 128

        # Get first page (limit=3)
        page1 = vector_store.search_similar(query, limit=3, offset=0)
        assert len(page1) == 3

        # Get second page (offset=3, limit=3)
        page2 = vector_store.search_similar(query, limit=3, offset=3)
        assert len(page2) == 3

        # Pages should have different IDs (no overlap)
        page1_ids = [sample_id for sample_id, _ in page1]
        page2_ids = [sample_id for sample_id, _ in page2]
        assert set(page1_ids).isdisjoint(set(page2_ids))

    def test_offset_beyond_results(self, vector_store):
        """Offset beyond total results returns empty list."""
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)
        vector_store.add_embedding("smpl_def456", [0.2] * 128)

        query = [0.1] * 128
        results = vector_store.search_similar(query, limit=5, offset=10)

        assert results == []

    def test_limit_larger_than_results(self, vector_store):
        """Limit larger than total returns all results."""
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)
        vector_store.add_embedding("smpl_def456", [0.2] * 128)

        query = [0.1] * 128
        results = vector_store.search_similar(query, limit=100)

        # Should get only 2 results (all that exist)
        assert len(results) == 2


class TestBatchOperations:
    """Test batch operations are efficient and atomic."""

    def test_batch_add_multiple(self, vector_store):
        """Batch add inserts all items with correct values."""
        items = [
            ("smpl_abc123", [0.1] * 128),
            ("smpl_def456", [0.2] * 128),
            ("smpl_ghi789", [0.3] * 128),
        ]

        vector_store.add_embeddings_batch(items)

        # Verify all inserted WITH CORRECT VALUES
        for sample_id, expected in items:
            retrieved = vector_store.get_embedding(sample_id)
            assert retrieved is not None
            assert len(retrieved) == 128
            assert retrieved[0] == pytest.approx(expected[0], abs=0.01)

    def test_batch_add_empty_list(self, vector_store):
        """Batch add with empty list is no-op."""
        vector_store.add_embeddings_batch([])

        # Should not crash, table should be empty
        query = [0.1] * 128
        results = vector_store.search_similar(query, limit=10)
        assert results == []

    def test_batch_replaces_existing(self, vector_store):
        """Batch add replaces existing embeddings."""
        # Add initial embedding
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)

        # Batch add with same ID but different embedding
        vector_store.add_embeddings_batch([
            ("smpl_abc123", [0.9] * 128),
        ])

        # Should get updated embedding
        updated = vector_store.get_embedding("smpl_abc123")
        assert updated[0] == pytest.approx(0.9, abs=0.01)


class TestCRUDOperations:
    """Test basic CRUD operations."""

    def test_add_and_get(self, vector_store):
        """Add embedding and retrieve it."""
        embedding = [0.1 * i for i in range(128)]
        vector_store.add_embedding("smpl_abc123", embedding)

        retrieved = vector_store.get_embedding("smpl_abc123")

        assert retrieved is not None
        assert len(retrieved) == 128
        # Check first few values (approximate due to float32 precision)
        for i in range(10):
            assert retrieved[i] == pytest.approx(embedding[i], abs=0.001)

    def test_get_nonexistent(self, vector_store):
        """Get nonexistent embedding returns None."""
        result = vector_store.get_embedding("smpl_nonexistent")
        assert result is None

    def test_delete_existing(self, vector_store):
        """Delete existing embedding returns True."""
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)

        deleted = vector_store.delete_embedding("smpl_abc123")
        assert deleted is True

        # Verify deleted
        assert vector_store.get_embedding("smpl_abc123") is None

    def test_delete_nonexistent(self, vector_store):
        """Delete nonexistent embedding returns False."""
        deleted = vector_store.delete_embedding("smpl_nonexistent")
        assert deleted is False

    def test_replace_embedding(self, vector_store):
        """Adding same ID replaces embedding."""
        vector_store.add_embedding("smpl_abc123", [0.1] * 128)
        vector_store.add_embedding("smpl_abc123", [0.9] * 128)

        retrieved = vector_store.get_embedding("smpl_abc123")
        assert retrieved[0] == pytest.approx(0.9, abs=0.01)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_vector(self, vector_store):
        """Zero vector is valid embedding."""
        zero_embedding = [0.0] * 128
        vector_store.add_embedding("smpl_zero", zero_embedding)

        retrieved = vector_store.get_embedding("smpl_zero")
        assert retrieved is not None
        assert all(v == 0.0 for v in retrieved)

    def test_large_values(self, vector_store):
        """Large embedding values are handled correctly."""
        large_embedding = [1000.0] * 128
        vector_store.add_embedding("smpl_large", large_embedding)

        retrieved = vector_store.get_embedding("smpl_large")
        assert retrieved[0] == pytest.approx(1000.0, abs=0.01)

    def test_negative_values(self, vector_store):
        """Negative embedding values are valid."""
        negative_embedding = [-0.5] * 128
        vector_store.add_embedding("smpl_negative", negative_embedding)

        retrieved = vector_store.get_embedding("smpl_negative")
        assert retrieved[0] == pytest.approx(-0.5, abs=0.01)

    def test_search_no_results(self, vector_store):
        """Search on empty database returns empty list."""
        query = [0.1] * 128
        results = vector_store.search_similar(query, limit=10)

        assert results == []

    def test_multiple_databases(self, temp_db_path):
        """Multiple stores can coexist in different directories."""
        db1 = LanceDBVectorStore(temp_db_path / "db1")
        db2 = LanceDBVectorStore(temp_db_path / "db2")

        db1.add_embedding("smpl_abc123", [0.1] * 128)
        db2.add_embedding("smpl_def456", [0.2] * 128)

        # Each database has only its own data
        assert db1.get_embedding("smpl_abc123") is not None
        assert db1.get_embedding("smpl_def456") is None

        assert db2.get_embedding("smpl_def456") is not None
        assert db2.get_embedding("smpl_abc123") is None
