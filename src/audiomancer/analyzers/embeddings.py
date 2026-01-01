"""Audio embedding extraction for audiomancer.

This module provides functions for extracting fixed-dimension audio embeddings
for similarity search and clustering using pre-trained Essentia models.

All embeddings are L2-normalized 128-dimensional vectors.

Includes SimilarityIndex for fast nearest-neighbor search using FAISS.
"""

import numpy as np
import essentia.standard as es
from pathlib import Path
from typing import Literal, Optional

from ..errors import ModelLoadError, AnalysisFailedError
from .models import load_model

# FAISS is optional - only needed for SimilarityIndex
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


ModelType = Literal["musicnn", "vggish", "openl3"]


def extract_audio_embedding(
    audio: np.ndarray,
    sr: int,
    model: ModelType = "musicnn",
) -> list[float]:
    """Extract 128-dimensional audio embedding for similarity search.

    Embeddings are L2-normalized fixed-size vectors that encode audio content.
    Similar-sounding audio will have similar embeddings (high cosine similarity).

    Args:
        audio: Audio samples as numpy array (mono or stereo)
        sr: Sample rate in Hz
        model: Embedding model to use:
            - "musicnn": MusiCNN embeddings (recommended for music)
            - "vggish": VGGish embeddings (general audio)
            - "openl3": OpenL3 embeddings (environmental sounds)

    Returns:
        List of 128 floats (L2-normalized embedding vector)

    Raises:
        ModelLoadError: If model file not found
        AnalysisFailedError: If embedding extraction fails

    Example:
        >>> embedding = extract_audio_embedding(audio, 44100)
        >>> len(embedding)
        128
        >>> # Verify L2 normalization
        >>> import math
        >>> math.isclose(sum(x**2 for x in embedding), 1.0, abs_tol=1e-6)
        True
    """
    try:
        # Load model
        model_path_obj = load_model(model)
        model_path = str(model_path_obj)

        # Ensure mono audio
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)

        # Resample to model's expected sample rate
        # Most Essentia models expect 16kHz
        target_sr = 16000
        if sr != target_sr:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)

        # Extract embedding based on model type
        if model == "musicnn":
            embedding = _extract_musicnn_embedding(audio, model_path)
        elif model == "vggish":
            embedding = _extract_vggish_embedding(audio, model_path)
        elif model == "openl3":
            embedding = _extract_openl3_embedding(audio, model_path)
        else:
            raise ModelLoadError(
                f"Unknown embedding model: {model}",
                details={"model": model}
            )

        # Ensure embedding is 128-dimensional
        if len(embedding) != 128:
            raise AnalysisFailedError(
                f"Expected 128-dimensional embedding, got {len(embedding)}",
                details={
                    "model": model,
                    "embedding_dim": len(embedding),
                }
            )

        # L2 normalize
        embedding_array = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(embedding_array)

        if norm == 0:
            raise AnalysisFailedError(
                "Zero-norm embedding (silent audio?)",
                details={"model": model}
            )

        normalized_embedding = embedding_array / norm

        # Verify normalization
        verification_norm = np.linalg.norm(normalized_embedding)
        if not np.isclose(verification_norm, 1.0, atol=1e-6):
            raise AnalysisFailedError(
                f"L2 normalization failed: norm={verification_norm}",
                details={"model": model, "norm": float(verification_norm)}
            )

        return normalized_embedding.tolist()

    except ModelLoadError:
        raise
    except AnalysisFailedError:
        raise
    except Exception as e:
        raise AnalysisFailedError(
            "Embedding extraction failed",
            details={
                "error": str(e),
                "stage": "embedding extraction",
                "model": model,
            }
        )


def _extract_musicnn_embedding(audio: np.ndarray, model_path: str) -> np.ndarray:
    """Extract MusiCNN embedding.

    Args:
        audio: Audio samples (mono, 16kHz)
        model_path: Path to MusiCNN model file

    Returns:
        128-dimensional embedding vector
    """
    # Use TensorflowPredictMusiCNN for MusiCNN embeddings
    model = es.TensorflowPredictMusiCNN(
        graphFilename=model_path,
        output="model/dense/BiasAdd",
    )

    # Extract embedding
    embedding = model(audio)

    # MusiCNN outputs 200-dim, we take first 128
    # or average pool to 128 if needed
    if len(embedding) > 128:
        # Average pool to 128 dimensions
        pooled = np.zeros(128, dtype=np.float32)
        pool_size = len(embedding) // 128
        for i in range(128):
            start = i * pool_size
            end = start + pool_size
            pooled[i] = np.mean(embedding[start:end])
        return pooled
    elif len(embedding) < 128:
        # Zero-pad to 128
        padded = np.zeros(128, dtype=np.float32)
        padded[:len(embedding)] = embedding
        return padded
    else:
        return embedding


def _extract_vggish_embedding(audio: np.ndarray, model_path: str) -> np.ndarray:
    """Extract VGGish embedding.

    Args:
        audio: Audio samples (mono, 16kHz)
        model_path: Path to VGGish model file

    Returns:
        128-dimensional embedding vector
    """
    # Use TensorflowPredictVGGish for VGGish embeddings
    model = es.TensorflowPredictVGGish(
        graphFilename=model_path,
        output="model/vggish/fc2/BiasAdd",
    )

    # VGGish processes audio in 0.96s windows
    # We'll extract embeddings for all windows and average
    embeddings = model(audio)

    # embeddings is a 2D array (n_windows, 128)
    if embeddings.ndim == 2:
        # Average across windows
        embedding = np.mean(embeddings, axis=0)
    else:
        embedding = embeddings

    # Ensure 128 dimensions
    if len(embedding) > 128:
        embedding = embedding[:128]
    elif len(embedding) < 128:
        padded = np.zeros(128, dtype=np.float32)
        padded[:len(embedding)] = embedding
        return padded

    return embedding


def _extract_openl3_embedding(audio: np.ndarray, model_path: str) -> np.ndarray:
    """Extract OpenL3 embedding.

    Args:
        audio: Audio samples (mono, 16kHz)
        model_path: Path to OpenL3 model file

    Returns:
        128-dimensional embedding vector
    """
    # OpenL3 uses similar approach to VGGish
    # Use generic TensorflowPredict with appropriate layer
    model = es.TensorflowPredict(
        graphFilename=model_path,
        output="model/openl3/embedding",
    )

    # Extract embedding
    embeddings = model(audio)

    # Average across time if multiple frames
    if embeddings.ndim == 2:
        embedding = np.mean(embeddings, axis=0)
    else:
        embedding = embeddings

    # Ensure 128 dimensions
    if len(embedding) > 128:
        # Average pool to 128
        pooled = np.zeros(128, dtype=np.float32)
        pool_size = len(embedding) // 128
        for i in range(128):
            start = i * pool_size
            end = start + pool_size
            pooled[i] = np.mean(embedding[start:end])
        return pooled
    elif len(embedding) < 128:
        padded = np.zeros(128, dtype=np.float32)
        padded[:len(embedding)] = embedding
        return padded

    return embedding


def cosine_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    """Compute cosine similarity between two embeddings.

    Since embeddings are L2-normalized, cosine similarity is just the dot product.

    Args:
        embedding1: First embedding (128-dim)
        embedding2: Second embedding (128-dim)

    Returns:
        Cosine similarity in range [-1, 1]
        (1 = identical, 0 = orthogonal, -1 = opposite)

    Example:
        >>> emb1 = extract_audio_embedding(audio1, 44100)
        >>> emb2 = extract_audio_embedding(audio2, 44100)
        >>> similarity = cosine_similarity(emb1, emb2)
        >>> 0 <= similarity <= 1  # For typical audio
        True
    """
    arr1 = np.array(embedding1, dtype=np.float32)
    arr2 = np.array(embedding2, dtype=np.float32)

    # Dot product (since both are L2-normalized)
    return float(np.dot(arr1, arr2))


def euclidean_distance(embedding1: list[float], embedding2: list[float]) -> float:
    """Compute Euclidean distance between two embeddings.

    Args:
        embedding1: First embedding (128-dim)
        embedding2: Second embedding (128-dim)

    Returns:
        Euclidean distance (lower = more similar)

    Example:
        >>> emb1 = extract_audio_embedding(audio1, 44100)
        >>> emb2 = extract_audio_embedding(audio2, 44100)
        >>> distance = euclidean_distance(emb1, emb2)
        >>> distance >= 0
        True
    """
    arr1 = np.array(embedding1, dtype=np.float32)
    arr2 = np.array(embedding2, dtype=np.float32)

    return float(np.linalg.norm(arr1 - arr2))


class SimilarityIndex:
    """Fast similarity search index using FAISS.

    Enables efficient nearest-neighbor search across thousands of audio embeddings.
    Uses IndexFlatIP (inner product) which equals cosine similarity for L2-normalized vectors.

    Example:
        >>> # Build index from embeddings
        >>> embeddings = [extract_audio_embedding(audio, sr) for audio in samples]
        >>> index = SimilarityIndex()
        >>> index.add(embeddings)
        >>>
        >>> # Search for similar samples
        >>> query = extract_audio_embedding(query_audio, sr)
        >>> similarities, indices = index.search(query, k=5)
        >>>
        >>> # Save/load for persistence
        >>> index.save("samples.index")
        >>> loaded = SimilarityIndex.load("samples.index")
    """

    def __init__(self, dimension: int = 128):
        """Create a new similarity index.

        Args:
            dimension: Embedding dimension (default 128 for audiomancer)

        Raises:
            ImportError: If faiss-cpu is not installed
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss-cpu is required for SimilarityIndex. "
                "Install with: pip install faiss-cpu"
            )

        self._dimension = dimension
        # IndexFlatIP uses inner product (dot product)
        # For L2-normalized vectors, this equals cosine similarity
        self._index = faiss.IndexFlatIP(dimension)

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension

    @property
    def ntotal(self) -> int:
        """Get the number of embeddings in the index."""
        return self._index.ntotal

    def add(self, embeddings: list[list[float]]) -> None:
        """Add embeddings to the index.

        Args:
            embeddings: List of embedding vectors (each 128-dim, L2-normalized)

        Raises:
            ValueError: If embeddings have wrong dimension
        """
        if not embeddings:
            return

        # Convert to numpy array with correct dtype
        arr = np.array(embeddings, dtype=np.float32)

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if arr.shape[1] != self._dimension:
            raise ValueError(
                f"Expected {self._dimension}-dimensional embeddings, "
                f"got {arr.shape[1]}"
            )

        self._index.add(arr)

    def search(
        self,
        query: list[float],
        k: int = 5,
    ) -> tuple[list[float], list[int]]:
        """Search for k most similar embeddings.

        Args:
            query: Query embedding (128-dim, L2-normalized)
            k: Number of nearest neighbors to return

        Returns:
            Tuple of (similarities, indices):
            - similarities: Cosine similarity scores (1.0 = identical)
            - indices: Indices of matching embeddings in add() order

        Raises:
            ValueError: If query has wrong dimension or index is empty
        """
        if self._index.ntotal == 0:
            raise ValueError("Index is empty. Add embeddings first.")

        # Convert to numpy array
        query_arr = np.array([query], dtype=np.float32)

        if query_arr.shape[1] != self._dimension:
            raise ValueError(
                f"Expected {self._dimension}-dimensional query, "
                f"got {query_arr.shape[1]}"
            )

        # Limit k to number of indexed vectors
        k = min(k, self._index.ntotal)

        # Search returns (distances, indices)
        # For IndexFlatIP, "distances" are actually similarity scores
        similarities, indices = self._index.search(query_arr, k)

        return similarities[0].tolist(), indices[0].tolist()

    def save(self, path: str | Path) -> None:
        """Save the index to disk.

        Args:
            path: Path to save the index file
        """
        faiss.write_index(self._index, str(path))

    @classmethod
    def load(cls, path: str | Path) -> "SimilarityIndex":
        """Load an index from disk.

        Args:
            path: Path to the index file

        Returns:
            Loaded SimilarityIndex

        Raises:
            ImportError: If faiss-cpu is not installed
            FileNotFoundError: If index file doesn't exist
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss-cpu is required for SimilarityIndex. "
                "Install with: pip install faiss-cpu"
            )

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")

        index = faiss.read_index(str(path))

        # Create instance and set the loaded index
        instance = cls.__new__(cls)
        instance._dimension = index.d
        instance._index = index

        return instance
