"""Tests for model cache."""
import pytest
from unittest.mock import patch, MagicMock
from audiomancer.analyzers.model_cache import (
    get_effnet_model,
    get_classifier_model,
    get_embedding_model,
    clear_cache,
    get_cache_stats,
)


class TestModelCache:
    """Test model caching functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_cache()

    @patch("audiomancer.analyzers.model_cache.load_model")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredictEffnetDiscogs")
    def test_effnet_model_cached(self, mock_effnet_class, mock_load, tmp_path):
        """Test that effnet model is cached on first load."""
        # Mock model loading
        model_path = tmp_path / "discogs_effnet.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock Essentia model
        mock_model = MagicMock()
        mock_effnet_class.return_value = mock_model

        # First call should create model
        model1 = get_effnet_model()
        assert mock_effnet_class.call_count == 1
        assert model1 is mock_model

        # Second call should return cached model (no new creation)
        model2 = get_effnet_model()
        assert mock_effnet_class.call_count == 1  # Still 1, not 2
        assert model2 is model1  # Same instance

    @patch("audiomancer.analyzers.model_cache.load_model")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredict2D")
    def test_classifier_model_cached(self, mock_classifier_class, mock_load, tmp_path):
        """Test that classifier models are cached."""
        # Mock model loading
        model_path = tmp_path / "mtg_jamendo_instrument.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock Essentia model
        mock_model = MagicMock()
        mock_classifier_class.return_value = mock_model

        # First call should create model
        model1 = get_classifier_model("mtg_jamendo_instrument")
        assert mock_classifier_class.call_count == 1
        assert model1 is mock_model

        # Second call should return cached model
        model2 = get_classifier_model("mtg_jamendo_instrument")
        assert mock_classifier_class.call_count == 1
        assert model2 is model1

    @patch("audiomancer.analyzers.model_cache.load_model")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredict2D")
    def test_different_classifier_models(self, mock_classifier_class, mock_load, tmp_path):
        """Test that different classifier models are cached separately."""
        # Mock model loading for both models
        def load_side_effect(model_name):
            model_path = tmp_path / f"{model_name}.pb"
            model_path.write_bytes(b"model")
            return model_path

        mock_load.side_effect = load_side_effect

        # Mock Essentia models
        mock_model1 = MagicMock()
        mock_model2 = MagicMock()
        mock_classifier_class.side_effect = [mock_model1, mock_model2]

        # Load two different models
        instrument_model = get_classifier_model("mtg_jamendo_instrument")
        mood_model = get_classifier_model("mtg_jamendo_moodtheme")

        assert instrument_model is mock_model1
        assert mood_model is mock_model2
        assert instrument_model is not mood_model

        # Verify both are cached independently
        instrument_model2 = get_classifier_model("mtg_jamendo_instrument")
        mood_model2 = get_classifier_model("mtg_jamendo_moodtheme")

        assert instrument_model2 is mock_model1
        assert mood_model2 is mock_model2
        assert mock_classifier_class.call_count == 2  # Only 2 creations

    @patch("audiomancer.analyzers.model_cache.load_model")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredictMusiCNN")
    def test_embedding_model_cached(self, mock_embedding_class, mock_load, tmp_path):
        """Test that embedding models are cached."""
        # Mock model loading
        model_path = tmp_path / "musicnn.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock Essentia model
        mock_model = MagicMock()
        mock_embedding_class.return_value = mock_model

        # First call should create model
        model1 = get_embedding_model("musicnn")
        assert mock_embedding_class.call_count == 1
        assert model1 is mock_model

        # Second call should return cached model
        model2 = get_embedding_model("musicnn")
        assert mock_embedding_class.call_count == 1
        assert model2 is model1

    @patch("audiomancer.analyzers.model_cache.load_model")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredictVGGish")
    def test_vggish_embedding_model(self, mock_vggish_class, mock_load, tmp_path):
        """Test that VGGish model uses correct Essentia class."""
        # Mock model loading
        model_path = tmp_path / "vggish.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock Essentia model
        mock_model = MagicMock()
        mock_vggish_class.return_value = mock_model

        # Should use TensorflowPredictVGGish for vggish
        model = get_embedding_model("vggish")
        assert mock_vggish_class.call_count == 1
        assert model is mock_model

    def test_clear_cache(self):
        """Test that clear_cache removes all cached models."""
        with patch("audiomancer.analyzers.model_cache.load_model") as mock_load, \
             patch("audiomancer.analyzers.model_cache.es.TensorflowPredictEffnetDiscogs") as mock_effnet:

            mock_load.return_value = "/fake/path.pb"
            mock_effnet.return_value = MagicMock()

            # Load a model
            get_effnet_model()

            # Verify it's cached
            stats = get_cache_stats()
            assert stats["num_models"] == 1

            # Clear cache
            clear_cache()

            # Verify cache is empty
            stats = get_cache_stats()
            assert stats["num_models"] == 0

    def test_get_cache_stats(self):
        """Test cache statistics."""
        with patch("audiomancer.analyzers.model_cache.load_model") as mock_load, \
             patch("audiomancer.analyzers.model_cache.es.TensorflowPredictEffnetDiscogs") as mock_effnet, \
             patch("audiomancer.analyzers.model_cache.es.TensorflowPredict2D") as mock_classifier:

            mock_load.return_value = "/fake/path.pb"
            mock_effnet.return_value = MagicMock()
            mock_classifier.return_value = MagicMock()

            # Initially empty
            stats = get_cache_stats()
            assert stats["num_models"] == 0
            assert stats["model_names"] == []

            # Load models
            get_effnet_model()
            get_classifier_model("mtg_jamendo_instrument")

            # Verify stats
            stats = get_cache_stats()
            assert stats["num_models"] == 2
            assert "discogs_effnet" in stats["model_names"]
            assert "mtg_jamendo_instrument" in stats["model_names"]

    @patch("audiomancer.analyzers.model_cache.load_model")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredictEffnetDiscogs")
    @patch("audiomancer.analyzers.model_cache.es.TensorflowPredict2D")
    def test_cache_survives_multiple_calls(self, mock_classifier, mock_effnet, mock_load):
        """Test that cache persists across multiple function calls."""
        mock_load.return_value = "/fake/path.pb"
        mock_effnet_instance = MagicMock()
        mock_classifier_instance = MagicMock()
        mock_effnet.return_value = mock_effnet_instance
        mock_classifier.return_value = mock_classifier_instance

        # Simulate multiple file processing
        for _ in range(10):
            get_effnet_model()
            get_classifier_model("mtg_jamendo_instrument")
            get_classifier_model("mtg_jamendo_moodtheme")
            get_classifier_model("mtg_jamendo_genre")

        # Models should only be created once each
        assert mock_effnet.call_count == 1
        # 3 different classifiers
        assert mock_classifier.call_count == 3

        # Verify all are still cached
        stats = get_cache_stats()
        assert stats["num_models"] == 4
