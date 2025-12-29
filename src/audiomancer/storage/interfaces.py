"""Storage layer interfaces for audiomancer.

This module defines Protocol interfaces for sample and vector storage operations.
All implementations must conform to these interfaces for dependency injection.
"""

from datetime import datetime
from typing import Literal, Optional, Protocol
from typing_extensions import TypedDict


class SampleMetadata(TypedDict, total=False):
    """Metadata for an audio sample.

    This TypedDict describes all fields stored for each sample. Fields marked
    as required (not NotRequired) must be present when creating a sample.

    Example:
        >>> sample = SampleMetadata(
        ...     id="smpl_abc12345",
        ...     file_path="/path/to/kick.wav",
        ...     file_hash="abc123def456",
        ...     duration_ms=250.5,
        ...     sample_rate=44100,
        ...     channels=1,
        ...     bit_depth=16,
        ...     file_size_bytes=44100,
        ...     spectral_centroid=1500.0,
        ...     spectral_bandwidth=800.0,
        ...     spectral_rolloff=5000.0,
        ...     zero_crossing_rate=0.15,
        ...     rms_energy=0.7,
        ...     dynamic_range=40.0,
        ...     bpm=125.0,
        ...     bpm_confidence=0.95,
        ...     is_loop=True,
        ...     key="C",
        ...     key_confidence=0.88,
        ...     tuning_frequency=440.0,
        ...     pitch_salience=0.8,
        ...     instrument_type="kick",
        ...     instrument_confidence=0.92,
        ...     mood=["energetic", "dark"],
        ...     genre_tags=["techno", "industrial"],
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now(),
        ... )
    """
    # Identity (required)
    id: str  # Format: "smpl_{hash[:8]}"
    file_path: str  # Absolute path to audio file
    file_hash: str  # SHA256 hash for deduplication

    # Basic metadata (required)
    duration_ms: float  # Duration in milliseconds
    sample_rate: int  # Sample rate in Hz (e.g., 44100, 48000)
    channels: int  # Number of audio channels (1=mono, 2=stereo)
    bit_depth: int  # Bit depth (16, 24, 32)
    file_size_bytes: int  # File size in bytes

    # Spectral features (optional, from Essentia analysis)
    spectral_centroid: float  # Brightness indicator in Hz
    spectral_bandwidth: float  # Frequency spread in Hz
    spectral_rolloff: float  # High frequency energy in Hz
    zero_crossing_rate: float  # Roughness/noisiness indicator (0-1)
    rms_energy: float  # Overall loudness (0-1)
    dynamic_range: float  # Difference between peaks and valleys in dB

    # Rhythm analysis (optional)
    bpm: float  # Tempo in beats per minute
    bpm_confidence: float  # Confidence score (0-1)
    is_loop: bool  # Whether sample is rhythmic loop

    # Tonal analysis (optional)
    key: str  # Musical key (e.g., "C", "Cm", "F#")
    key_confidence: float  # Confidence score (0-1)
    tuning_frequency: float  # Reference tuning (default 440 Hz)
    pitch_salience: float  # Tonal vs percussive (0-1, higher = more tonal)

    # ML-derived categories (optional)
    instrument_type: str  # Category: kick, snare, hi-hat, bass, pad, etc.
    instrument_confidence: float  # Classification confidence (0-1)
    mood: list[str]  # Mood tags (e.g., ["dark", "energetic"])
    genre_tags: list[str]  # Genre tags (e.g., ["techno", "house"])

    # Timestamps
    created_at: datetime  # When sample was indexed
    updated_at: datetime  # Last metadata update


class SampleStore(Protocol):
    """Interface for sample storage operations.

    This Protocol defines the contract for storing and retrieving sample metadata.
    Implementations must provide CRUD operations, search, and batch operations.
    """

    def add(self, sample: SampleMetadata) -> str:
        """Add sample to database.

        Args:
            sample: Complete sample metadata to store

        Returns:
            Sample ID (format: "smpl_{hash[:8]}")

        Raises:
            DuplicateSampleError: If sample with same file_hash already exists

        Example:
            >>> sample = SampleMetadata(
            ...     file_path="/samples/kick.wav",
            ...     file_hash="abc123",
            ...     duration_ms=250.5,
            ...     sample_rate=44100,
            ...     channels=1,
            ...     bit_depth=16,
            ...     file_size_bytes=44100,
            ... )
            >>> sample_id = store.add(sample)
            >>> sample_id
            "smpl_abc123"
        """
        ...

    def add_batch(self, samples: list[SampleMetadata]) -> list[str]:
        """Add multiple samples atomically in a single transaction.

        All samples are added or none are (atomic operation). On duplicate,
        rolls back entire batch without partial commits.

        Args:
            samples: List of sample metadata to store

        Returns:
            List of sample IDs in same order as input

        Raises:
            DuplicateSampleError: On first duplicate (no partial commits)

        Example:
            >>> samples = [sample1, sample2, sample3]
            >>> ids = store.add_batch(samples)
            >>> len(ids)
            3
            >>> ids[0]
            "smpl_abc123"
        """
        ...

    def get(self, sample_id: str) -> Optional[SampleMetadata]:
        """Retrieve sample by ID.

        Args:
            sample_id: Sample ID (format: "smpl_{hash[:8]}")

        Returns:
            Sample metadata if found, None otherwise

        Example:
            >>> sample = store.get("smpl_abc123")
            >>> sample['file_path']
            "/samples/kick.wav"
            >>> store.get("smpl_nonexistent")
            None
        """
        ...

    def get_by_path(self, file_path: str) -> Optional[SampleMetadata]:
        """Retrieve sample by file path.

        Args:
            file_path: Absolute path to audio file

        Returns:
            Sample metadata if found, None otherwise

        Example:
            >>> sample = store.get_by_path("/samples/kick.wav")
            >>> sample['id']
            "smpl_abc123"
        """
        ...

    def get_by_hash(self, file_hash: str) -> Optional[SampleMetadata]:
        """Retrieve sample by file hash.

        Used for deduplication - check if sample already exists before adding.

        Args:
            file_hash: SHA256 hash of audio file

        Returns:
            Sample metadata if found, None otherwise

        Example:
            >>> sample = store.get_by_hash("abc123")
            >>> sample is not None
            True
        """
        ...

    def update(self, sample_id: str, updates: dict) -> bool:
        """Update sample fields.

        Only updates specified fields, leaving others unchanged.

        Args:
            sample_id: Sample ID to update
            updates: Dictionary of field names and new values

        Returns:
            True if sample was updated, False if not found

        Example:
            >>> success = store.update(
            ...     "smpl_abc123",
            ...     {"bpm": 128.0, "key": "C#"}
            ... )
            >>> success
            True
            >>> store.update("smpl_nonexistent", {"bpm": 120})
            False
        """
        ...

    def delete(self, sample_id: str) -> bool:
        """Delete sample from database.

        Args:
            sample_id: Sample ID to delete

        Returns:
            True if sample was deleted, False if not found

        Example:
            >>> success = store.delete("smpl_abc123")
            >>> success
            True
            >>> store.delete("smpl_nonexistent")
            False
        """
        ...

    def search(
        self,
        query: Optional[str] = None,
        instrument_type: Optional[str] = None,
        bpm_min: Optional[float] = None,
        bpm_max: Optional[float] = None,
        key: Optional[str] = None,
        mood: Optional[list[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SampleMetadata]:
        """Search samples with filters and pagination.

        All filters are combined with AND logic. Text query searches file_path.

        Args:
            query: Text search in file path
            instrument_type: Filter by instrument category
            bpm_min: Minimum BPM (inclusive)
            bpm_max: Maximum BPM (inclusive)
            key: Musical key filter
            mood: Mood tags (matches if ANY tag present)
            limit: Maximum results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of matching samples (up to limit)

        Example:
            >>> # Search for kicks between 120-130 BPM
            >>> results = store.search(
            ...     instrument_type="kick",
            ...     bpm_min=120.0,
            ...     bpm_max=130.0,
            ...     limit=10,
            ...     offset=0,
            ... )
            >>> len(results) <= 10
            True

            >>> # Pagination - get second page
            >>> page2 = store.search(
            ...     instrument_type="kick",
            ...     limit=10,
            ...     offset=10,
            ... )
        """
        ...

    def count(
        self,
        query: Optional[str] = None,
        instrument_type: Optional[str] = None,
        bpm_min: Optional[float] = None,
        bpm_max: Optional[float] = None,
        key: Optional[str] = None,
        mood: Optional[list[str]] = None,
    ) -> int:
        """Count samples matching filters.

        Same filter logic as search(), but returns count instead of results.
        Useful for calculating pagination.

        Args:
            query: Text search in file path
            instrument_type: Filter by instrument category
            bpm_min: Minimum BPM (inclusive)
            bpm_max: Maximum BPM (inclusive)
            key: Musical key filter
            mood: Mood tags (matches if ANY tag present)

        Returns:
            Number of matching samples

        Example:
            >>> total = store.count(instrument_type="kick")
            >>> total
            234
            >>> pages = (total + 9) // 10  # Calculate pages (10 per page)
            >>> pages
            24
        """
        ...


class VectorStore(Protocol):
    """Interface for embedding vector operations.

    Stores and searches sample embeddings for semantic similarity search.
    Uses cosine distance metric (0 = identical, 2 = opposite).
    """

    def add_embedding(self, sample_id: str, embedding: list[float]) -> None:
        """Store embedding vector for a sample.

        Args:
            sample_id: Sample ID (must exist in SampleStore)
            embedding: Vector embedding (dimension=128)

        Raises:
            ValueError: If embedding dimension != 128

        Example:
            >>> embedding = [0.1, 0.2, ..., 0.5]  # 128 dimensions
            >>> store.add_embedding("smpl_abc123", embedding)
        """
        ...

    def add_embeddings_batch(
        self,
        items: list[tuple[str, list[float]]]
    ) -> None:
        """Add multiple embeddings efficiently in batch.

        Optimized for bulk insertion (10-100x faster than individual adds).

        Args:
            items: List of (sample_id, embedding) tuples

        Raises:
            ValueError: If any embedding dimension != 128

        Example:
            >>> items = [
            ...     ("smpl_abc123", [0.1, 0.2, ..., 0.5]),
            ...     ("smpl_def456", [0.3, 0.4, ..., 0.6]),
            ...     ("smpl_ghi789", [0.2, 0.3, ..., 0.4]),
            ... ]
            >>> store.add_embeddings_batch(items)
        """
        ...

    def get_embedding(self, sample_id: str) -> Optional[list[float]]:
        """Retrieve embedding vector for a sample.

        Args:
            sample_id: Sample ID

        Returns:
            Embedding vector if found, None otherwise

        Example:
            >>> embedding = store.get_embedding("smpl_abc123")
            >>> len(embedding)
            128
            >>> store.get_embedding("smpl_nonexistent")
            None
        """
        ...

    def search_similar(
        self,
        embedding: list[float],
        limit: int = 10,
        offset: int = 0,
        exclude_ids: Optional[list[str]] = None,
        distance_metric: Literal["cosine", "l2"] = "cosine",
    ) -> list[tuple[str, float]]:
        """Find similar samples by embedding distance.

        Returns samples sorted by distance (ascending = most similar first).

        Distance metrics:
        - cosine: Cosine distance (0 = identical, 2 = opposite)
        - l2: Euclidean distance (lower = more similar)

        Args:
            embedding: Query vector (dimension=128)
            limit: Maximum results to return
            offset: Number of results to skip (for pagination)
            exclude_ids: Sample IDs to exclude from results
            distance_metric: Distance calculation method

        Returns:
            List of (sample_id, distance) sorted by distance ascending

        Raises:
            ValueError: If embedding dimension != 128

        Example:
            >>> query_emb = [0.3, 0.4, ..., 0.5]  # 128 dimensions
            >>> results = store.search_similar(
            ...     query_emb,
            ...     limit=5,
            ...     offset=0,
            ...     distance_metric="cosine",
            ... )
            >>> results
            [
                ("smpl_abc123", 0.05),
                ("smpl_def456", 0.12),
                ("smpl_ghi789", 0.18),
                ("smpl_jkl012", 0.23),
                ("smpl_mno345", 0.29),
            ]

            >>> # Pagination - get next page
            >>> page2 = store.search_similar(query_emb, limit=5, offset=5)

            >>> # Exclude already-used samples
            >>> more = store.search_similar(
            ...     query_emb,
            ...     limit=5,
            ...     exclude_ids=["smpl_abc123", "smpl_def456"],
            ... )
        """
        ...

    def delete_embedding(self, sample_id: str) -> bool:
        """Delete embedding vector for a sample.

        Args:
            sample_id: Sample ID

        Returns:
            True if embedding was deleted, False if not found

        Example:
            >>> success = store.delete_embedding("smpl_abc123")
            >>> success
            True
            >>> store.delete_embedding("smpl_nonexistent")
            False
        """
        ...
