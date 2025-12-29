"""Audio embedding extraction for audiomancer.

This module provides functions for extracting fixed-dimension audio embeddings
for similarity search and clustering using pre-trained Essentia models.

All embeddings are L2-normalized 128-dimensional vectors.
"""

import numpy as np
import essentia.standard as es
from typing import Literal

from ..errors import ModelLoadError, AnalysisFailedError
from .models import load_model


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
