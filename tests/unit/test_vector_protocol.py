"""Type checking test to verify LanceDBVectorStore conforms to VectorStore Protocol."""

from pathlib import Path
import tempfile
import shutil

from audiomancer.storage.interfaces import VectorStore
from audiomancer.storage.vectors import LanceDBVectorStore


def test_lancedb_implements_protocol():
    """LanceDBVectorStore should satisfy VectorStore Protocol."""
    # Create temporary database
    temp_dir = Path(tempfile.mkdtemp())
    try:
        store = LanceDBVectorStore(temp_dir)

        # Type checker should accept this assignment
        vector_store: VectorStore = store

        # Verify all protocol methods exist and are callable
        assert callable(vector_store.add_embedding)
        assert callable(vector_store.add_embeddings_batch)
        assert callable(vector_store.get_embedding)
        assert callable(vector_store.search_similar)
        assert callable(vector_store.delete_embedding)

    finally:
        shutil.rmtree(temp_dir)
