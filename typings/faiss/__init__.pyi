"""Type stubs for faiss-cpu (C++ bindings).

FAISS is a library for efficient similarity search and clustering of dense vectors.
These stubs cover the subset of the API actually used by audiomancer.

See: https://github.com/facebookresearch/faiss
"""
import numpy as np
import numpy.typing as npt
from pathlib import Path

class IndexFlatIP:
    """Flat index using inner product (dot product) for similarity.

    For L2-normalized vectors, inner product equals cosine similarity.
    This is the index type used by SimilarityIndex in audiomancer.
    """

    d: int  # Dimension of vectors
    ntotal: int  # Number of vectors in the index

    def __init__(self, d: int) -> None:
        """Initialize index for d-dimensional vectors.

        Args:
            d: Dimension of vectors to be indexed
        """
        ...

    def add(self, x: npt.NDArray[np.float32]) -> None:
        """Add vectors to the index.

        Args:
            x: Array of shape (n, d) containing n vectors of dimension d
        """
        ...

    def search(
        self, x: npt.NDArray[np.float32], k: int
    ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.int64]]:
        """Search for k nearest neighbors.

        Args:
            x: Query vectors of shape (nq, d)
            k: Number of nearest neighbors to return

        Returns:
            Tuple of (distances, indices):
            - distances: Array of shape (nq, k) with similarity scores
            - indices: Array of shape (nq, k) with indices of neighbors
        """
        ...

class IndexFlatL2:
    """Flat index using L2 (Euclidean) distance.

    This index type is available but not currently used by audiomancer.
    Included for completeness.
    """

    d: int  # Dimension of vectors
    ntotal: int  # Number of vectors in the index

    def __init__(self, d: int) -> None:
        """Initialize index for d-dimensional vectors.

        Args:
            d: Dimension of vectors to be indexed
        """
        ...

    def add(self, x: npt.NDArray[np.float32]) -> None:
        """Add vectors to the index.

        Args:
            x: Array of shape (n, d) containing n vectors of dimension d
        """
        ...

    def search(
        self, x: npt.NDArray[np.float32], k: int
    ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.int64]]:
        """Search for k nearest neighbors.

        Args:
            x: Query vectors of shape (nq, d)
            k: Number of nearest neighbors to return

        Returns:
            Tuple of (distances, indices):
            - distances: Array of shape (nq, k) with L2 distances
            - indices: Array of shape (nq, k) with indices of neighbors
        """
        ...

def write_index(index: IndexFlatIP | IndexFlatL2, fname: str) -> None:
    """Write index to disk.

    Args:
        index: Index to save
        fname: File path to write to
    """
    ...

def read_index(fname: str) -> IndexFlatIP | IndexFlatL2:
    """Read index from disk.

    Args:
        fname: File path to read from

    Returns:
        Loaded index (type depends on what was saved)
    """
    ...
