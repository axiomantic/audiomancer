"""Unified storage layer integrating SQLite and LanceDB.

This module provides atomic operations across both metadata (SQLite) and
embedding (LanceDB) stores, ensuring data consistency. All operations
follow fail-fast semantics with automatic rollback on partial failures.

Example:
    >>> from pathlib import Path
    >>> storage = UnifiedSampleStorage(
    ...     db_path=Path("~/.audiomancer/samples.db"),
    ...     embeddings_path=Path("~/.audiomancer/embeddings")
    ... )
    >>> sample_id = storage.add_sample_with_embedding(sample, embedding)
    >>> similar = storage.find_similar(sample_id, limit=10)
"""

from pathlib import Path
from typing import Literal, Optional

from audiomancer.errors import DuplicateSampleError, SampleNotFoundError, StorageError
from audiomancer.storage.db import SampleStore
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.storage.vectors import LanceDBVectorStore


class UnifiedSampleStorage:
    """Unified interface for sample storage with metadata and embeddings.

    Coordinates atomic operations across SQLite (metadata) and LanceDB (embeddings)
    to maintain data consistency. If either store fails, changes are rolled back.

    Attributes:
        sample_store: SQLite metadata store
        vector_store: LanceDB embedding store

    Example:
        >>> storage = UnifiedSampleStorage(
        ...     db_path=Path("~/.audiomancer/samples.db"),
        ...     embeddings_path=Path("~/.audiomancer/embeddings")
        ... )
        >>> sample = SampleMetadata(
        ...     id="smpl_abc123",
        ...     file_path="/samples/kick.wav",
        ...     file_hash="abc123",
        ...     duration_ms=250.5,
        ...     sample_rate=44100,
        ...     channels=1,
        ...     bit_depth=16,
        ...     file_size_bytes=44100,
        ... )
        >>> embedding = [0.1] * 128
        >>> sample_id = storage.add_sample_with_embedding(sample, embedding)
    """

    def __init__(self, db_path: Path, embeddings_path: Path):
        """Initialize unified storage with both stores.

        Creates database and embedding directories if they don't exist.

        Args:
            db_path: Path to SQLite database file
            embeddings_path: Path to LanceDB embeddings directory

        Example:
            >>> storage = UnifiedSampleStorage(
            ...     db_path=Path("~/.audiomancer/samples.db"),
            ...     embeddings_path=Path("~/.audiomancer/embeddings")
            ... )
        """
        # Expand user paths
        db_path = db_path.expanduser().absolute()
        embeddings_path = embeddings_path.expanduser().absolute()

        # Create parent directories
        db_path.parent.mkdir(parents=True, exist_ok=True)
        embeddings_path.mkdir(parents=True, exist_ok=True)

        self.sample_store = SampleStore(str(db_path))
        self.vector_store = LanceDBVectorStore(embeddings_path)

    def add_sample_with_embedding(
        self,
        sample: SampleMetadata,
        embedding: list[float]
    ) -> str:
        """Add sample and embedding atomically.

        Both metadata and embedding are added together. If either operation fails,
        neither is persisted (atomic rollback).

        Args:
            sample: Complete sample metadata
            embedding: 128-dimensional embedding vector

        Returns:
            Sample ID (format: "smpl_{hash[:8]}")

        Raises:
            DuplicateSampleError: If sample hash already exists in database
            ValueError: If embedding dimension != 128
            StorageError: On unexpected storage errors

        Example:
            >>> sample = SampleMetadata(
            ...     id="smpl_abc123",
            ...     file_path="/samples/kick.wav",
            ...     file_hash="abc123",
            ...     duration_ms=250.5,
            ...     sample_rate=44100,
            ...     channels=1,
            ...     bit_depth=16,
            ...     file_size_bytes=44100,
            ... )
            >>> embedding = [0.1] * 128
            >>> sample_id = storage.add_sample_with_embedding(sample, embedding)
            >>> storage.sample_store.get(sample_id) is not None
            True
            >>> storage.vector_store.get_embedding(sample_id) is not None
            True
        """
        sample_id: Optional[str] = None

        try:
            # Add sample metadata first
            sample_id = self.sample_store.add(sample)

            # Add embedding (if this fails, rollback sample)
            self.vector_store.add_embedding(sample_id, embedding)

            return sample_id

        except DuplicateSampleError:
            # Sample already exists, propagate error
            raise
        except ValueError as e:
            # Embedding validation failed, rollback sample if added
            if sample_id:
                try:
                    self.sample_store.delete(sample_id)
                except Exception:
                    # Ignore rollback errors, original error is more important
                    pass
            raise StorageError(
                f"Invalid embedding: {str(e)}",
                details={"sample_id": sample.get("id"), "error": str(e)}
            )
        except Exception as e:
            # Unexpected error, rollback sample if added
            if sample_id:
                try:
                    self.sample_store.delete(sample_id)
                except Exception:
                    # Ignore rollback errors
                    pass
            raise StorageError(
                f"Failed to add sample with embedding: {str(e)}",
                details={"sample_id": sample.get("id"), "error": str(e)}
            )

    def add_samples_with_embeddings_batch(
        self,
        items: list[tuple[SampleMetadata, list[float]]]
    ) -> list[str]:
        """Add multiple samples and embeddings atomically.

        All samples and embeddings are added together or none are added
        (atomic batch operation). On any failure, rolls back all changes.

        Args:
            items: List of (sample, embedding) tuples

        Returns:
            List of sample IDs in same order as input

        Raises:
            DuplicateSampleError: If any sample hash already exists
            ValueError: If any embedding dimension != 128
            StorageError: On unexpected storage errors

        Example:
            >>> items = [
            ...     (sample1, [0.1] * 128),
            ...     (sample2, [0.2] * 128),
            ...     (sample3, [0.3] * 128),
            ... ]
            >>> sample_ids = storage.add_samples_with_embeddings_batch(items)
            >>> len(sample_ids)
            3
        """
        if not items:
            return []

        sample_ids: list[str] = []

        try:
            # Validate all embeddings first (fail fast)
            for sample, embedding in items:
                if len(embedding) != LanceDBVectorStore.EMBEDDING_DIM:
                    raise ValueError(
                        f"Embedding dimension must be {LanceDBVectorStore.EMBEDDING_DIM}, "
                        f"got {len(embedding)} for sample {sample.get('id')}"
                    )

            # Add all samples first
            samples = [sample for sample, _ in items]
            sample_ids = self.sample_store.add_batch(samples)

            # Add all embeddings
            embedding_items = [
                (sample_id, embedding)
                for sample_id, (_, embedding) in zip(sample_ids, items)
            ]
            self.vector_store.add_embeddings_batch(embedding_items)

            return sample_ids

        except DuplicateSampleError:
            # Sample already exists, propagate error
            raise
        except ValueError as e:
            # Embedding validation failed, rollback samples if added
            if sample_ids:
                for sample_id in sample_ids:
                    try:
                        self.sample_store.delete(sample_id)
                    except Exception:
                        # Ignore rollback errors
                        pass
            raise StorageError(
                f"Invalid embedding in batch: {str(e)}",
                details={"batch_size": len(items), "error": str(e)}
            )
        except Exception as e:
            # Unexpected error, rollback samples if added
            if sample_ids:
                for sample_id in sample_ids:
                    try:
                        self.sample_store.delete(sample_id)
                    except Exception:
                        # Ignore rollback errors
                        pass
            raise StorageError(
                f"Failed to add batch with embeddings: {str(e)}",
                details={"batch_size": len(items), "error": str(e)}
            )

    def delete_sample(self, sample_id: str) -> bool:
        """Delete sample and its embedding.

        Removes from both metadata and embedding stores. If either delete fails,
        the operation continues (best effort cleanup).

        Args:
            sample_id: Sample ID to delete

        Returns:
            True if sample was deleted from metadata store, False if not found

        Example:
            >>> success = storage.delete_sample("smpl_abc123")
            >>> success
            True
            >>> storage.sample_store.get("smpl_abc123")
            None
            >>> storage.vector_store.get_embedding("smpl_abc123")
            None
        """
        # Delete from both stores (best effort)
        sample_deleted = self.sample_store.delete(sample_id)

        # Always try to delete embedding even if sample wasn't found
        # (orphaned embeddings should be cleaned up)
        try:
            self.vector_store.delete_embedding(sample_id)
        except Exception:
            # Ignore embedding deletion errors
            pass

        return sample_deleted

    def find_similar(
        self,
        sample_id: str,
        limit: int = 10,
        exclude_self: bool = True,
        distance_metric: Literal["cosine", "l2"] = "cosine",
    ) -> list[tuple[SampleMetadata, float]]:
        """Find samples similar to the given sample.

        Uses the sample's embedding to find nearest neighbors in vector space,
        then retrieves full metadata for each result.

        Args:
            sample_id: Sample ID to find similar samples for
            limit: Maximum number of results to return
            exclude_self: Whether to exclude the query sample from results
            distance_metric: Distance calculation method ("cosine" or "l2")

        Returns:
            List of (sample, distance) tuples sorted by distance ascending

        Raises:
            SampleNotFoundError: If sample_id not found in vector store
            StorageError: On unexpected storage errors

        Example:
            >>> similar = storage.find_similar("smpl_abc123", limit=5)
            >>> len(similar) <= 5
            True
            >>> # First result is most similar
            >>> similar[0][1] < similar[1][1]
            True
        """
        # Get embedding for query sample
        embedding = self.vector_store.get_embedding(sample_id)
        if embedding is None:
            raise SampleNotFoundError(
                f"No embedding found for sample {sample_id}",
                details={"sample_id": sample_id, "reason": "No embedding found for sample"}
            )

        # Find similar embeddings
        exclude_ids = [sample_id] if exclude_self else None

        # Request extra results to account for potentially missing metadata
        search_limit = limit * 2 if exclude_self else limit + 1

        similar_ids = self.vector_store.search_similar(
            embedding,
            limit=search_limit,
            exclude_ids=exclude_ids,
            distance_metric=distance_metric
        )

        # Retrieve metadata for each result
        results = []
        for sid, distance in similar_ids:
            metadata = self.sample_store.get(sid)
            if metadata:
                results.append((metadata, distance))
                if len(results) >= limit:
                    break

        return results

    def search_by_text_and_similarity(
        self,
        query_embedding: Optional[list[float]] = None,
        text_query: Optional[str] = None,
        filters: Optional[dict] = None,
        limit: int = 20,
        distance_metric: Literal["cosine", "l2"] = "cosine",
    ) -> list[SampleMetadata]:
        """Combined text search and similarity search.

        Can use vector similarity, text search, or both. When both are provided,
        results are intersected (samples must match both criteria).

        Args:
            query_embedding: Optional embedding vector for similarity search
            text_query: Optional text query for metadata search
            filters: Optional filters (instrument_type, bpm_min, bpm_max, key, mood)
            limit: Maximum number of results
            distance_metric: Distance metric for similarity search

        Returns:
            List of matching samples sorted by relevance

        Raises:
            ValueError: If neither query_embedding nor text_query provided
            StorageError: On unexpected storage errors

        Example:
            >>> # Similarity search only
            >>> results = storage.search_by_text_and_similarity(
            ...     query_embedding=[0.1] * 128,
            ...     limit=10
            ... )

            >>> # Text search only
            >>> results = storage.search_by_text_and_similarity(
            ...     text_query="kick",
            ...     filters={"bpm_min": 120.0, "bpm_max": 130.0},
            ...     limit=10
            ... )

            >>> # Combined search
            >>> results = storage.search_by_text_and_similarity(
            ...     query_embedding=[0.1] * 128,
            ...     text_query="kick",
            ...     filters={"key": "C"},
            ...     limit=10
            ... )
        """
        if query_embedding is None and text_query is None:
            raise ValueError("Must provide query_embedding or text_query or both")

        filters = filters or {}

        # Case 1: Only text search
        if query_embedding is None:
            return self.sample_store.search(
                query=text_query,
                instrument_type=filters.get("instrument_type"),
                bpm_min=filters.get("bpm_min"),
                bpm_max=filters.get("bpm_max"),
                key=filters.get("key"),
                mood=filters.get("mood"),
                limit=limit
            )

        # Case 2: Only similarity search
        if text_query is None and not filters:
            similar_ids = self.vector_store.search_similar(
                query_embedding,
                limit=limit,
                distance_metric=distance_metric
            )

            results = []
            for sample_id, _ in similar_ids:
                metadata = self.sample_store.get(sample_id)
                if metadata:
                    results.append(metadata)

            return results

        # Case 3: Combined search - get candidates from similarity, filter by text
        # Request more candidates to account for filtering
        search_limit = limit * 5

        similar_ids = self.vector_store.search_similar(
            query_embedding,
            limit=search_limit,
            distance_metric=distance_metric
        )

        # Get sample IDs from similarity search
        candidate_ids = {sample_id for sample_id, _ in similar_ids}

        # Get samples matching text filters
        text_results = self.sample_store.search(
            query=text_query,
            instrument_type=filters.get("instrument_type"),
            bpm_min=filters.get("bpm_min"),
            bpm_max=filters.get("bpm_max"),
            key=filters.get("key"),
            mood=filters.get("mood"),
            limit=search_limit
        )

        # Intersect: only samples that match both criteria
        results = []
        for sample in text_results:
            if sample["id"] in candidate_ids:
                results.append(sample)
                if len(results) >= limit:
                    break

        return results

    def get_sample(self, sample_id: str) -> Optional[SampleMetadata]:
        """Retrieve sample metadata by ID.

        Convenience wrapper around sample_store.get().

        Args:
            sample_id: Sample ID

        Returns:
            Sample metadata if found, None otherwise

        Example:
            >>> sample = storage.get_sample("smpl_abc123")
            >>> sample['file_path']
            "/samples/kick.wav"
        """
        return self.sample_store.get(sample_id)

    def get_embedding(self, sample_id: str) -> Optional[list[float]]:
        """Retrieve embedding by sample ID.

        Convenience wrapper around vector_store.get_embedding().

        Args:
            sample_id: Sample ID

        Returns:
            Embedding vector if found, None otherwise

        Example:
            >>> embedding = storage.get_embedding("smpl_abc123")
            >>> len(embedding)
            128
        """
        return self.vector_store.get_embedding(sample_id)

    def update_sample(self, sample_id: str, updates: dict) -> bool:
        """Update sample metadata fields.

        Only updates specified fields in metadata store. Does not affect embedding.
        To update embedding, use add_sample_with_embedding() with new embedding.

        Args:
            sample_id: Sample ID to update
            updates: Dictionary of field names and new values

        Returns:
            True if sample was updated, False if not found

        Example:
            >>> success = storage.update_sample(
            ...     "smpl_abc123",
            ...     {"bpm": 128.0, "key": "C#"}
            ... )
            >>> success
            True
        """
        return self.sample_store.update(sample_id, updates)
