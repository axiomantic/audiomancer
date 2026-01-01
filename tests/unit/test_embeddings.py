"""Tests for audio embedding extraction."""
import pytest
import numpy as np
import math
from unittest.mock import patch, MagicMock
from audiomancer.analyzers.embeddings import (
    extract_audio_embedding,
    cosine_similarity,
    euclidean_distance,
    SimilarityIndex,
    FAISS_AVAILABLE,
)
from audiomancer.errors import ModelLoadError, AnalysisFailedError
from tests.utils import create_test_audio


class TestEmbeddingExtraction:
    """Test audio embedding extraction."""

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
    def test_extract_musicnn_embedding_cached_success(self, mock_extract, mock_load, mock_get_embedding, tmp_path):
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_vggish_embedding_cached")
    def test_extract_vggish_embedding_cached_success(self, mock_extract, mock_load, mock_get_embedding, tmp_path):
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_openl3_embedding_cached")
    def test_extract_openl3_embedding_cached_success(self, mock_extract, mock_load, mock_get_embedding, tmp_path):
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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

    @patch("audiomancer.analyzers.embeddings.get_embedding_model")
    @patch("audiomancer.analyzers.embeddings.load_model")
    @patch("audiomancer.analyzers.embeddings._extract_musicnn_embedding_cached")
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


@pytest.mark.skipif(not FAISS_AVAILABLE, reason="faiss-cpu not installed")
class TestSimilarityIndex:
    """Test SimilarityIndex for fast nearest-neighbor search."""

    def test_init_default_dimension(self):
        """Test initialization with default dimension."""
        index = SimilarityIndex()

        assert index.dimension == 128
        assert index.ntotal == 0

    def test_init_custom_dimension(self):
        """Test initialization with custom dimension."""
        index = SimilarityIndex(dimension=256)

        assert index.dimension == 256
        assert index.ntotal == 0

    @patch("audiomancer.analyzers.embeddings.FAISS_AVAILABLE", False)
    def test_init_faiss_unavailable(self):
        """Test that ImportError is raised when FAISS is unavailable."""
        with pytest.raises(ImportError) as exc_info:
            SimilarityIndex()

        assert "faiss-cpu is required" in str(exc_info.value)
        assert "pip install faiss-cpu" in str(exc_info.value)

    def test_dimension_property(self):
        """Test dimension property returns correct value."""
        index = SimilarityIndex(dimension=64)

        assert index.dimension == 64

    def test_ntotal_property_empty(self):
        """Test ntotal property returns 0 for empty index."""
        index = SimilarityIndex()

        assert index.ntotal == 0

    def test_ntotal_property_after_add(self):
        """Test ntotal property reflects number of added embeddings."""
        index = SimilarityIndex()

        # Add 3 embeddings
        embeddings = [
            [1/math.sqrt(128)] * 128,
            [1/math.sqrt(128)] * 128,
            [1/math.sqrt(128)] * 128,
        ]
        index.add(embeddings)

        assert index.ntotal == 3

    def test_add_single_embedding(self):
        """Test adding a single embedding."""
        index = SimilarityIndex()

        # Create L2-normalized embedding
        embedding = [1/math.sqrt(128)] * 128
        index.add([embedding])

        assert index.ntotal == 1

    def test_add_multiple_embeddings(self):
        """Test adding multiple embeddings at once."""
        index = SimilarityIndex()

        # Create 5 L2-normalized embeddings
        embeddings = []
        for i in range(5):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)  # L2 normalize
            embeddings.append(emb.tolist())

        index.add(embeddings)

        assert index.ntotal == 5

    def test_add_empty_list(self):
        """Test that adding empty list is a no-op."""
        index = SimilarityIndex()

        index.add([])

        assert index.ntotal == 0

    def test_add_wrong_dimension(self):
        """Test that adding wrong-dimension embeddings raises ValueError."""
        index = SimilarityIndex(dimension=128)

        # Try to add 64-dim embeddings
        wrong_embeddings = [[0.1] * 64]

        with pytest.raises(ValueError) as exc_info:
            index.add(wrong_embeddings)

        assert "128-dimensional" in str(exc_info.value)
        assert "64" in str(exc_info.value)

    def test_search_exact_match(self):
        """Test search finds exact match with similarity ~1.0."""
        index = SimilarityIndex()

        # Create 3 different L2-normalized embeddings
        emb1 = np.array([1.0] + [0.0] * 127, dtype=np.float32)
        emb2 = np.array([0.0] + [1.0] + [0.0] * 126, dtype=np.float32)
        emb3 = np.array([0.0, 0.0] + [1.0] + [0.0] * 125, dtype=np.float32)

        index.add([emb1.tolist(), emb2.tolist(), emb3.tolist()])

        # Search for exact match to emb2
        similarities, indices = index.search(emb2.tolist(), k=1)

        assert len(similarities) == 1
        assert len(indices) == 1
        assert indices[0] == 1  # emb2 was added second (index 1)
        assert math.isclose(similarities[0], 1.0, abs_tol=1e-6)

    def test_search_k_neighbors(self):
        """Test search returns k nearest neighbors."""
        index = SimilarityIndex()

        # Add 5 embeddings
        embeddings = []
        for i in range(5):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        index.add(embeddings)

        # Search for 3 nearest neighbors
        query = embeddings[0]  # Use first embedding as query
        similarities, indices = index.search(query, k=3)

        assert len(similarities) == 3
        assert len(indices) == 3
        # First result should be exact match with index 0
        assert indices[0] == 0
        assert math.isclose(similarities[0], 1.0, abs_tol=1e-6)

    def test_search_empty_index(self):
        """Test that searching empty index raises ValueError."""
        index = SimilarityIndex()

        query = [1/math.sqrt(128)] * 128

        with pytest.raises(ValueError) as exc_info:
            index.search(query, k=5)

        assert "empty" in str(exc_info.value).lower()

    def test_search_wrong_query_dimension(self):
        """Test that wrong-dimension query raises ValueError."""
        index = SimilarityIndex(dimension=128)

        # Add one embedding
        embedding = [1/math.sqrt(128)] * 128
        index.add([embedding])

        # Try to search with wrong dimension
        wrong_query = [0.1] * 64

        with pytest.raises(ValueError) as exc_info:
            index.search(wrong_query, k=1)

        assert "128-dimensional" in str(exc_info.value)
        assert "64" in str(exc_info.value)

    def test_search_k_larger_than_ntotal(self):
        """Test that k larger than ntotal returns all embeddings."""
        index = SimilarityIndex()

        # Add 3 embeddings
        embeddings = []
        for i in range(3):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        index.add(embeddings)

        # Search with k=10 (larger than ntotal=3)
        query = embeddings[0]
        similarities, indices = index.search(query, k=10)

        # Should return all 3 embeddings
        assert len(similarities) == 3
        assert len(indices) == 3

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test save and load preserves index state."""
        # Create index and add embeddings
        index = SimilarityIndex(dimension=128)

        embeddings = []
        for i in range(5):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        index.add(embeddings)

        # Save to file
        index_path = tmp_path / "test.index"
        index.save(index_path)

        # Load from file
        loaded_index = SimilarityIndex.load(index_path)

        # Verify loaded index has same properties
        assert loaded_index.dimension == 128
        assert loaded_index.ntotal == 5

        # Verify search results are identical
        query = embeddings[0]

        original_similarities, original_indices = index.search(query, k=3)
        loaded_similarities, loaded_indices = loaded_index.search(query, k=3)

        assert original_indices == loaded_indices
        for orig_sim, loaded_sim in zip(original_similarities, loaded_similarities):
            assert math.isclose(orig_sim, loaded_sim, abs_tol=1e-6)

    def test_load_preserves_dimension_and_ntotal(self, tmp_path):
        """Test that load preserves dimension and ntotal metadata."""
        # Create index with custom dimension
        index = SimilarityIndex(dimension=256)

        # Add some embeddings
        embeddings = []
        for i in range(10):
            emb = np.random.randn(256).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        index.add(embeddings)

        # Save
        index_path = tmp_path / "custom.index"
        index.save(index_path)

        # Load
        loaded = SimilarityIndex.load(index_path)

        # Verify metadata
        assert loaded.dimension == 256
        assert loaded.ntotal == 10

    def test_load_nonexistent_file(self, tmp_path):
        """Test that loading non-existent file raises FileNotFoundError."""
        nonexistent_path = tmp_path / "does_not_exist.index"

        with pytest.raises(FileNotFoundError) as exc_info:
            SimilarityIndex.load(nonexistent_path)

        assert "not found" in str(exc_info.value).lower()

    @patch("audiomancer.analyzers.embeddings.FAISS_AVAILABLE", False)
    def test_load_faiss_unavailable(self, tmp_path):
        """Test that load raises ImportError when FAISS unavailable."""
        # Note: We can't actually create a real index file without FAISS,
        # but we can test that the check happens before trying to load
        fake_path = tmp_path / "fake.index"
        fake_path.write_bytes(b"fake index data")

        with pytest.raises(ImportError) as exc_info:
            SimilarityIndex.load(fake_path)

        assert "faiss-cpu is required" in str(exc_info.value)

    def test_integration_build_and_search_ordering(self):
        """Test building index and verifying cosine similarity ordering."""
        index = SimilarityIndex()

        # Create 5 embeddings with known relationships
        # emb0 and emb1 will be very similar (differ by small noise)
        # emb2, emb3, emb4 will be progressively different

        base_emb = np.random.randn(128).astype(np.float32)
        base_emb = base_emb / np.linalg.norm(base_emb)

        emb0 = base_emb

        # emb1: add small noise to base (high similarity)
        emb1 = base_emb + np.random.randn(128).astype(np.float32) * 0.01
        emb1 = emb1 / np.linalg.norm(emb1)

        # emb2: add medium noise (medium similarity)
        emb2 = base_emb + np.random.randn(128).astype(np.float32) * 0.5
        emb2 = emb2 / np.linalg.norm(emb2)

        # emb3: add large noise (low similarity)
        emb3 = base_emb + np.random.randn(128).astype(np.float32) * 2.0
        emb3 = emb3 / np.linalg.norm(emb3)

        # emb4: completely random (very low similarity)
        emb4 = np.random.randn(128).astype(np.float32)
        emb4 = emb4 / np.linalg.norm(emb4)

        embeddings = [emb0.tolist(), emb1.tolist(), emb2.tolist(),
                      emb3.tolist(), emb4.tolist()]

        index.add(embeddings)

        # Search with emb0 as query
        similarities, indices = index.search(emb0.tolist(), k=5)

        # Verify all similarities in [-1, 1] range (cosine similarity)
        # Allow small tolerance for floating-point precision
        for sim in similarities:
            assert -1.0 - 1e-6 <= sim <= 1.0 + 1e-6

        # Verify similarity scores are in descending order
        for i in range(len(similarities) - 1):
            assert similarities[i] >= similarities[i + 1]

        # First result should be exact match (emb0 at index 0)
        assert indices[0] == 0
        assert math.isclose(similarities[0], 1.0, abs_tol=1e-6)

        # Second result should be emb1 (index 1, high similarity)
        assert indices[1] == 1
        assert similarities[1] > 0.9  # Should be very similar

    def test_l2_normalized_vectors_cosine_similarity(self):
        """Test that L2-normalized identical vectors give cosine similarity ~1.0."""
        index = SimilarityIndex()

        # Create an L2-normalized embedding
        embedding = np.random.randn(128).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        # Verify it's normalized
        norm = np.linalg.norm(embedding)
        assert math.isclose(norm, 1.0, abs_tol=1e-6)

        # Add to index
        index.add([embedding.tolist()])

        # Search with identical embedding
        similarities, indices = index.search(embedding.tolist(), k=1)

        # Cosine similarity should be 1.0 for identical L2-normalized vectors
        assert len(similarities) == 1
        assert len(indices) == 1
        assert indices[0] == 0
        assert math.isclose(similarities[0], 1.0, abs_tol=1e-6)

    def test_ntotal_updates_correctly(self):
        """Test that ntotal property updates correctly after multiple add() calls."""
        index = SimilarityIndex()

        # Initially empty
        assert index.ntotal == 0

        # Add 3 embeddings
        embeddings_batch1 = []
        for i in range(3):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings_batch1.append(emb.tolist())

        index.add(embeddings_batch1)
        assert index.ntotal == 3

        # Add 2 more embeddings
        embeddings_batch2 = []
        for i in range(2):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings_batch2.append(emb.tolist())

        index.add(embeddings_batch2)
        assert index.ntotal == 5

        # Add 4 more embeddings
        embeddings_batch3 = []
        for i in range(4):
            emb = np.random.randn(128).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings_batch3.append(emb.tolist())

        index.add(embeddings_batch3)
        assert index.ntotal == 9

        # Verify we can search and get all 9 results
        query = embeddings_batch1[0]
        similarities, indices = index.search(query, k=10)

        # Should return all 9 embeddings
        assert len(similarities) == 9
        assert len(indices) == 9
