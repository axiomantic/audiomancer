"""Tests for audio embedding extraction."""
import pytest
import numpy as np
import math
from unittest.mock import patch, MagicMock
from audiomancer.analyzers.embeddings import (
    extract_audio_embedding,
    cosine_similarity,
    euclidean_distance,
)
from audiomancer.errors import ModelLoadError, AnalysisFailedError
from tests.utils import create_test_audio


class TestEmbeddingExtraction:
    """Test audio embedding extraction."""

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_extract_musicnn_embedding_success(self, mock_extract, mock_load, tmp_path):
        """Test successful MusiCNN embedding extraction."""
        # Mock model loading
        model_path = tmp_path / "musicnn.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock embedding extraction (128-dim)
        mock_embedding = np.random.randn(128).astype(np.float32)
        mock_extract.return_value = mock_embedding

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100)

        # Extract embedding
        embedding = extract_audio_embedding(audio, 44100, model="musicnn")

        # Verify
        assert isinstance(embedding, list)
        assert len(embedding) == 128

        # Verify L2 normalization
        norm = math.sqrt(sum(x**2 for x in embedding))
        assert math.isclose(norm, 1.0, abs_tol=1e-6)

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_vggish_embedding")
    def test_extract_vggish_embedding_success(self, mock_extract, mock_load, tmp_path):
        """Test successful VGGish embedding extraction."""
        # Mock model loading
        model_path = tmp_path / "vggish.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock embedding (128-dim)
        mock_embedding = np.random.randn(128).astype(np.float32)
        mock_extract.return_value = mock_embedding

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100)

        # Extract embedding
        embedding = extract_audio_embedding(audio, 44100, model="vggish")

        # Verify
        assert len(embedding) == 128

        # Verify L2 normalization
        norm = math.sqrt(sum(x**2 for x in embedding))
        assert math.isclose(norm, 1.0, abs_tol=1e-6)

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_openl3_embedding")
    def test_extract_openl3_embedding_success(self, mock_extract, mock_load, tmp_path):
        """Test successful OpenL3 embedding extraction."""
        # Mock model loading
        model_path = tmp_path / "openl3.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock embedding (128-dim)
        mock_embedding = np.random.randn(128).astype(np.float32)
        mock_extract.return_value = mock_embedding

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100)

        # Extract embedding
        embedding = extract_audio_embedding(audio, 44100, model="openl3")

        # Verify
        assert len(embedding) == 128

        # Verify L2 normalization
        norm = math.sqrt(sum(x**2 for x in embedding))
        assert math.isclose(norm, 1.0, abs_tol=1e-6)

    @patch("audiomancer.analyzers.embeddings.load_model")
    def test_extract_embedding_invalid_model(self, mock_load, tmp_path):
        """Test embedding extraction with invalid model type."""
        # Mock model loading
        model_path = tmp_path / "invalid.pb"
        mock_load.return_value = model_path

        audio = create_test_audio(duration=1.0)

        # Should raise ModelLoadError for unknown model
        with pytest.raises(ModelLoadError):
            extract_audio_embedding(audio, 44100, model="invalid_model")

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_extract_embedding_wrong_dimension(self, mock_extract, mock_load, tmp_path):
        """Test that wrong-dimension embeddings raise error."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        # Return wrong dimension
        mock_extract.return_value = np.random.randn(64).astype(np.float32)

        audio = create_test_audio(duration=1.0)

        # Should raise AnalysisFailedError
        with pytest.raises(AnalysisFailedError) as exc_info:
            extract_audio_embedding(audio, 44100, model="musicnn")

        assert "128-dimensional" in str(exc_info.value)

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_extract_embedding_zero_norm(self, mock_extract, mock_load, tmp_path):
        """Test that zero-norm embeddings raise error."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        # Return all zeros
        mock_extract.return_value = np.zeros(128, dtype=np.float32)

        audio = create_test_audio(duration=1.0)

        # Should raise AnalysisFailedError
        with pytest.raises(AnalysisFailedError) as exc_info:
            extract_audio_embedding(audio, 44100, model="musicnn")

        assert "zero-norm" in str(exc_info.value).lower()

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_extract_embedding_stereo_to_mono(self, mock_extract, mock_load, tmp_path):
        """Test that stereo audio is converted to mono."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        mock_extract.return_value = np.random.randn(128).astype(np.float32)

        # Create stereo audio
        mono = create_test_audio(duration=0.5, sample_rate=44100)
        stereo = np.stack([mono, mono])

        # Extract embedding
        embedding = extract_audio_embedding(stereo, 44100, model="musicnn")

        # Should succeed
        assert len(embedding) == 128

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_extract_embedding_resampling(self, mock_extract, mock_load, tmp_path):
        """Test that audio is resampled to 16kHz."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        mock_extract.return_value = np.random.randn(128).astype(np.float32)

        # Create 48kHz audio
        audio = create_test_audio(duration=0.5, sample_rate=48000)

        # Extract embedding
        embedding = extract_audio_embedding(audio, 48000, model="musicnn")

        # Should succeed (was resampled)
        assert len(embedding) == 128


class TestEmbeddingNormalization:
    """Test L2 normalization of embeddings."""

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_embedding_l2_normalized(self, mock_extract, mock_load, tmp_path):
        """Test that embeddings are L2 normalized."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        # Return unnormalized embedding
        unnormalized = np.array([1.0] * 128, dtype=np.float32)  # norm = sqrt(128)
        mock_extract.return_value = unnormalized

        audio = create_test_audio(duration=1.0)

        # Extract embedding
        embedding = extract_audio_embedding(audio, 44100, model="musicnn")

        # Calculate norm
        norm = math.sqrt(sum(x**2 for x in embedding))

        # Should be normalized to 1.0
        assert math.isclose(norm, 1.0, abs_tol=1e-6)

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_multiple_embeddings_consistent_norm(self, mock_extract, mock_load, tmp_path):
        """Test that multiple embeddings all have norm 1.0."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        audio = create_test_audio(duration=1.0)

        # Extract multiple embeddings with different random values
        for i in range(5):
            # Different random embedding each time
            mock_extract.return_value = np.random.randn(128).astype(np.float32)

            embedding = extract_audio_embedding(audio, 44100, model="musicnn")
            norm = math.sqrt(sum(x**2 for x in embedding))

            # All should be normalized
            assert math.isclose(norm, 1.0, abs_tol=1e-6)


class TestSimilarityFunctions:
    """Test embedding similarity functions."""

    def test_cosine_similarity_identical(self):
        """Test cosine similarity of identical embeddings."""
        # Create normalized embedding
        embedding = [1/math.sqrt(128)] * 128  # L2 norm = 1.0

        similarity = cosine_similarity(embedding, embedding)

        # Should be 1.0 (identical)
        assert math.isclose(similarity, 1.0, abs_tol=1e-6)

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal embeddings."""
        # Create two orthogonal normalized embeddings
        embedding1 = [1.0] + [0.0] * 127
        embedding2 = [0.0] + [1.0] + [0.0] * 126

        similarity = cosine_similarity(embedding1, embedding2)

        # Should be 0.0 (orthogonal)
        assert math.isclose(similarity, 0.0, abs_tol=1e-6)

    def test_cosine_similarity_opposite(self):
        """Test cosine similarity of opposite embeddings."""
        # Create two opposite normalized embeddings
        embedding1 = [1/math.sqrt(128)] * 128
        embedding2 = [-1/math.sqrt(128)] * 128

        similarity = cosine_similarity(embedding1, embedding2)

        # Should be -1.0 (opposite)
        assert math.isclose(similarity, -1.0, abs_tol=1e-6)

    def test_euclidean_distance_identical(self):
        """Test Euclidean distance of identical embeddings."""
        embedding = [1/math.sqrt(128)] * 128

        distance = euclidean_distance(embedding, embedding)

        # Should be 0.0 (identical)
        assert math.isclose(distance, 0.0, abs_tol=1e-6)

    def test_euclidean_distance_opposite(self):
        """Test Euclidean distance of opposite normalized embeddings."""
        # For L2-normalized vectors, distance between v and -v is 2*||v|| = 2*1 = 2
        embedding1 = [1/math.sqrt(128)] * 128
        embedding2 = [-1/math.sqrt(128)] * 128

        distance = euclidean_distance(embedding1, embedding2)

        # Should be 2.0 for opposite unit vectors
        expected = 2.0
        assert math.isclose(distance, expected, abs_tol=1e-5)

    def test_euclidean_distance_nonnegative(self):
        """Test that Euclidean distance is always non-negative."""
        # Random embeddings
        embedding1 = list(np.random.randn(128))
        embedding2 = list(np.random.randn(128))

        distance = euclidean_distance(embedding1, embedding2)

        # Should be >= 0
        assert distance >= 0

    def test_similarity_symmetry(self):
        """Test that similarity is symmetric."""
        embedding1 = list(np.random.randn(128))
        embedding2 = list(np.random.randn(128))

        sim1 = cosine_similarity(embedding1, embedding2)
        sim2 = cosine_similarity(embedding2, embedding1)

        # Should be equal
        assert math.isclose(sim1, sim2, abs_tol=1e-6)

    def test_distance_symmetry(self):
        """Test that distance is symmetric."""
        embedding1 = list(np.random.randn(128))
        embedding2 = list(np.random.randn(128))

        dist1 = euclidean_distance(embedding1, embedding2)
        dist2 = euclidean_distance(embedding2, embedding1)

        # Should be equal
        assert math.isclose(dist1, dist2, abs_tol=1e-6)


class TestEmbeddingConsistency:
    """Test that embeddings are consistent and reproducible."""

    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding")
    def test_same_audio_same_embedding(self, mock_extract, mock_load, tmp_path):
        """Test that same audio produces same embedding."""
        # Mock model
        model_path = tmp_path / "musicnn.pb"
        mock_load.return_value = model_path

        # Fixed embedding for consistency
        fixed_embedding = np.random.randn(128).astype(np.float32)
        mock_extract.return_value = fixed_embedding

        audio = create_test_audio(duration=1.0, sample_rate=44100, frequency=440)

        # Extract twice
        embedding1 = extract_audio_embedding(audio, 44100, model="musicnn")

        # Reset mock to return same embedding
        mock_extract.return_value = fixed_embedding
        embedding2 = extract_audio_embedding(audio, 44100, model="musicnn")

        # Should be identical (or very close due to normalization)
        for v1, v2 in zip(embedding1, embedding2):
            assert math.isclose(v1, v2, abs_tol=1e-6)
