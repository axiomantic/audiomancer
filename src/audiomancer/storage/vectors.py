"""LanceDB-backed vector storage for audio embeddings.

This module implements the VectorStore protocol using LanceDB for efficient
vector similarity search. Embeddings are 128-dimensional vectors representing
audio features, stored with metadata for fast nearest-neighbor queries.

Example:
    >>> from pathlib import Path
    >>> store = LanceDBVectorStore(Path("./embeddings"))
    >>> embedding = [0.1] * 128  # 128-dim vector
    >>> store.add_embedding("smpl_abc123", embedding)
    >>> results = store.search_similar(embedding, limit=5)
    >>> results[0]
    ("smpl_abc123", 0.0)  # Distance 0.0 = exact match
"""

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import lancedb
import numpy as np
import pyarrow as pa


class LanceDBVectorStore:
    """LanceDB-backed vector storage for audio embeddings.

    Provides efficient storage and similarity search for 128-dimensional
    audio embeddings using LanceDB's vector index capabilities.

    The embeddings table has schema:
    - id: string (sample ID)
    - embedding: fixed_size_list[float32, 128] (audio embedding)
    - created_at: timestamp (insertion time)

    Attributes:
        db_path: Path to LanceDB database directory
        table_name: Name of embeddings table (default: "embeddings")
        embedding_dim: Required embedding dimension (always 128)
    """

    EMBEDDING_DIM = 128
    TABLE_NAME = "embeddings"

    def __init__(self, db_path: Path) -> None:
        """Initialize LanceDB at given path.

        Creates database directory if it doesn't exist. Table is created
        lazily on first add operation.

        Args:
            db_path: Path to LanceDB database directory

        Example:
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> store.db_path
            PosixPath('./embeddings')
        """
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._table: Optional[lancedb.table.Table] = None

    @property
    def _schema(self) -> pa.Schema:
        """PyArrow schema for embeddings table.

        Returns:
            Schema with id, embedding, and created_at columns
        """
        return pa.schema([
            pa.field("id", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), self.EMBEDDING_DIM)),
            pa.field("created_at", pa.timestamp('ms')),
        ])

    def _validate_embedding(self, embedding: list[float]) -> None:
        """Validate embedding dimension.

        Args:
            embedding: Vector to validate

        Raises:
            ValueError: If embedding dimension != 128

        Example:
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> store._validate_embedding([0.1] * 128)  # OK
            >>> store._validate_embedding([0.1] * 127)  # Raises ValueError
        """
        if len(embedding) != self.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension must be {self.EMBEDDING_DIM}, "
                f"got {len(embedding)}"
            )

    def _ensure_table(self) -> lancedb.table.Table:
        """Ensure embeddings table exists.

        Creates table if it doesn't exist, reuses existing table otherwise.

        Returns:
            LanceDB table instance
        """
        if self._table is None:
            table_names = self._db.table_names()
            if self.TABLE_NAME in table_names:
                self._table = self._db.open_table(self.TABLE_NAME)
            else:
                # Create empty table with schema
                empty_data = pa.Table.from_pydict(
                    {
                        "id": pa.array([], type=pa.string()),
                        "embedding": pa.array(
                            [],
                            type=pa.list_(pa.float32(), self.EMBEDDING_DIM)
                        ),
                        "created_at": pa.array([], type=pa.timestamp('ms')),
                    },
                    schema=self._schema
                )
                self._table = self._db.create_table(
                    self.TABLE_NAME,
                    data=empty_data,
                    mode="create"
                )
        return self._table

    def add_embedding(self, sample_id: str, embedding: list[float]) -> None:
        """Store 128-dim embedding for sample.

        If sample_id already exists, replaces the existing embedding.

        Args:
            sample_id: Sample ID (format: "smpl_{hash[:8]}")
            embedding: Vector embedding (dimension=128)

        Raises:
            ValueError: If embedding dimension != 128

        Example:
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> embedding = [0.1, 0.2] + [0.0] * 126  # 128 dims
            >>> store.add_embedding("smpl_abc123", embedding)
            >>> retrieved = store.get_embedding("smpl_abc123")
            >>> len(retrieved)
            128
        """
        self._validate_embedding(embedding)

        table = self._ensure_table()

        # Delete existing embedding if present
        self.delete_embedding(sample_id)

        # Add new embedding
        data = pa.Table.from_pydict(
            {
                "id": [sample_id],
                "embedding": [embedding],
                "created_at": [datetime.now()],
            },
            schema=self._schema
        )
        table.add(data)

    def add_embeddings_batch(
        self,
        items: list[tuple[str, list[float]]]
    ) -> None:
        """Add multiple embeddings efficiently.

        Validates all dimensions first, then batch inserts. If any embedding
        has wrong dimension, entire batch fails atomically.

        Args:
            items: List of (sample_id, embedding) tuples

        Raises:
            ValueError: If any embedding dimension != 128

        Example:
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> items = [
            ...     ("smpl_abc123", [0.1] * 128),
            ...     ("smpl_def456", [0.2] * 128),
            ...     ("smpl_ghi789", [0.3] * 128),
            ... ]
            >>> store.add_embeddings_batch(items)
            >>> len(store.search_similar([0.1] * 128, limit=10))
            3
        """
        # Validate all embeddings first (fail fast)
        for sample_id, embedding in items:
            self._validate_embedding(embedding)

        if not items:
            return

        table = self._ensure_table()

        # Delete existing embeddings
        sample_ids = [sample_id for sample_id, _ in items]
        for sample_id in sample_ids:
            self.delete_embedding(sample_id)

        # Prepare batch data
        now = datetime.now()
        data = pa.Table.from_pydict(
            {
                "id": sample_ids,
                "embedding": [embedding for _, embedding in items],
                "created_at": [now] * len(items),
            },
            schema=self._schema
        )

        table.add(data)

    def get_embedding(self, sample_id: str) -> Optional[list[float]]:
        """Retrieve embedding by sample ID.

        Args:
            sample_id: Sample ID

        Returns:
            Embedding vector if found, None otherwise

        Example:
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> store.add_embedding("smpl_abc123", [0.1] * 128)
            >>> embedding = store.get_embedding("smpl_abc123")
            >>> len(embedding)
            128
            >>> store.get_embedding("smpl_nonexistent")
            None
        """
        table = self._ensure_table()

        # Query for exact ID match
        results = table.search().where(f"id = '{sample_id}'").limit(1).to_list()

        if not results:
            return None

        return results[0]["embedding"]

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
        Uses ANN (Approximate Nearest Neighbors) for efficient search.

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
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> store.add_embedding("smpl_abc123", [0.1] * 128)
            >>> store.add_embedding("smpl_def456", [0.2] * 128)
            >>> results = store.search_similar([0.1] * 128, limit=2)
            >>> results[0][0]  # Most similar ID
            'smpl_abc123'
            >>> results[0][1] < results[1][1]  # Distance ascending
            True
        """
        self._validate_embedding(embedding)

        table = self._ensure_table()

        # LanceDB needs total limit including offset
        total_limit = limit + offset

        # Build query
        query = table.search(embedding, vector_column_name="embedding")

        # Set distance metric
        if distance_metric == "cosine":
            query = query.metric("cosine")
        elif distance_metric == "l2":
            query = query.metric("l2")

        # Execute search with total limit
        results = query.limit(total_limit).to_list()

        # Apply offset and exclude_ids manually
        filtered_results = []
        for row in results:
            sample_id = row["id"]

            # Skip excluded IDs
            if exclude_ids and sample_id in exclude_ids:
                continue

            distance = float(row["_distance"])
            filtered_results.append((sample_id, distance))

        # Apply offset and limit
        paginated_results = filtered_results[offset:offset + limit]

        return paginated_results

    def delete_embedding(self, sample_id: str) -> bool:
        """Delete embedding. Returns True if deleted, False if not found.

        Args:
            sample_id: Sample ID to delete

        Returns:
            True if embedding was deleted, False if not found

        Example:
            >>> store = LanceDBVectorStore(Path("./embeddings"))
            >>> store.add_embedding("smpl_abc123", [0.1] * 128)
            >>> store.delete_embedding("smpl_abc123")
            True
            >>> store.delete_embedding("smpl_abc123")  # Already deleted
            False
        """
        table = self._ensure_table()

        # Check if exists
        exists = table.search().where(f"id = '{sample_id}'").limit(1).to_list()
        if not exists:
            return False

        # Delete by predicate
        table.delete(f"id = '{sample_id}'")
        return True
