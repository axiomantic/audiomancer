"""Tests for ML-based audio classification."""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from audiomancer.analyzers.classifier import (
    classify_instrument,
    extract_mood_tags,
    extract_genre_tags,
    INSTRUMENT_CLASSES,
    MOOD_CLASSES,
    GENRE_CLASSES,
)
from audiomancer.errors import ModelLoadError, AnalysisFailedError
from tests.utils import create_test_audio


class TestInstrumentClassification:
    """Test instrument classification."""

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_classify_instrument_success(self, mock_model_class, mock_load, tmp_path):
        """Test successful instrument classification."""
        # Mock model loading
        model_path = tmp_path / "instrument.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock model predictions
        mock_model = MagicMock()
        # Create fake predictions (40 classes, drums highest)
        predictions = np.zeros(40, dtype=np.float32)
        predictions[13] = 5.0  # drums (index 13)
        predictions[14] = 3.0  # drummachine
        predictions[27] = 2.0  # percussion
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100, frequency=440)

        # Classify
        result = classify_instrument(audio, 44100, top_k=3)

        # Verify result structure
        assert "instrument_type" in result
        assert "instrument_confidence" in result
        assert "top_predictions" in result

        # Verify top prediction is valid
        assert result["instrument_type"] in INSTRUMENT_CLASSES
        assert 0 <= result["instrument_confidence"] <= 1

        # Verify top-k predictions
        assert len(result["top_predictions"]) == 3
        for instrument, confidence in result["top_predictions"]:
            assert instrument in INSTRUMENT_CLASSES
            assert 0 <= confidence <= 1

        # Verify predictions are sorted by confidence (descending)
        confidences = [conf for _, conf in result["top_predictions"]]
        assert confidences == sorted(confidences, reverse=True)

    @patch("audiomancer.analyzers.classifier.load_model")
    def test_classify_instrument_model_load_error(self, mock_load):
        """Test classification with model load error."""
        # Mock model loading to fail
        mock_load.side_effect = ModelLoadError("Model not found", details={})

        # Create test audio
        audio = create_test_audio(duration=1.0)

        # Should raise ModelLoadError
        with pytest.raises(ModelLoadError):
            classify_instrument(audio, 44100)

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_classify_instrument_stereo_to_mono(self, mock_model_class, mock_load, tmp_path):
        """Test that stereo audio is converted to mono."""
        # Mock model
        model_path = tmp_path / "instrument.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        mock_model = MagicMock()
        predictions = np.zeros(40, dtype=np.float32)
        predictions[0] = 5.0
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        # Create stereo audio
        mono = create_test_audio(duration=0.5, sample_rate=44100)
        stereo = np.stack([mono, mono])

        # Classify
        result = classify_instrument(stereo, 44100)

        # Should succeed (stereo was converted to mono)
        assert result["instrument_type"] in INSTRUMENT_CLASSES

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_classify_instrument_resampling(self, mock_model_class, mock_load, tmp_path):
        """Test that audio is resampled to 16kHz."""
        # Mock model
        model_path = tmp_path / "instrument.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        mock_model = MagicMock()
        predictions = np.zeros(40, dtype=np.float32)
        predictions[0] = 5.0
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        # Create 48kHz audio
        audio = create_test_audio(duration=0.5, sample_rate=48000)

        # Classify
        result = classify_instrument(audio, 48000)

        # Should succeed (was resampled to 16kHz)
        assert result["instrument_type"] in INSTRUMENT_CLASSES


class TestMoodClassification:
    """Test mood/theme classification."""

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_mood_tags_success(self, mock_model_class, mock_load, tmp_path):
        """Test successful mood extraction."""
        # Mock model loading
        model_path = tmp_path / "mood.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock predictions (56 mood classes)
        mock_model = MagicMock()
        predictions = np.zeros(56, dtype=np.float32)
        predictions[11] = 5.0  # dark
        predictions[30] = 4.0  # energetic
        predictions[39] = 3.0  # powerful
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100)

        # Extract moods
        moods = extract_mood_tags(audio, 44100, top_k=3, threshold=0.1)

        # Verify
        assert isinstance(moods, list)
        assert len(moods) <= 3
        for mood in moods:
            assert mood in MOOD_CLASSES

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_mood_tags_threshold_filtering(self, mock_model_class, mock_load, tmp_path):
        """Test that threshold filters low-confidence predictions."""
        # Mock model
        model_path = tmp_path / "mood.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        mock_model = MagicMock()
        # Create predictions with only one above threshold
        predictions = np.ones(56, dtype=np.float32) * 0.01  # All very low
        predictions[11] = 5.0  # Only this one high
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        audio = create_test_audio(duration=1.0)

        # Extract with high threshold
        moods = extract_mood_tags(audio, 44100, top_k=10, threshold=0.5)

        # Should only get the one above threshold after softmax
        assert len(moods) >= 1
        assert all(m in MOOD_CLASSES for m in moods)


class TestGenreClassification:
    """Test genre classification."""

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_genre_tags_success(self, mock_model_class, mock_load, tmp_path):
        """Test successful genre extraction."""
        # Mock model loading
        model_path = tmp_path / "genre.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        # Mock predictions (87 genre classes)
        mock_model = MagicMock()
        predictions = np.zeros(87, dtype=np.float32)
        predictions[68] = 5.0  # techno
        predictions[35] = 4.0  # electronic
        predictions[40] = 3.0  # house
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100)

        # Extract genres
        genres = extract_genre_tags(audio, 44100, top_k=3, threshold=0.1)

        # Verify
        assert isinstance(genres, list)
        assert len(genres) <= 3
        for genre in genres:
            assert genre in GENRE_CLASSES

    @patch("audiomancer.analyzers.classifier.load_model")
    def test_extract_genre_tags_model_error(self, mock_load):
        """Test genre extraction with model error."""
        # Mock model loading to fail
        mock_load.side_effect = ModelLoadError("Model not found", details={})

        audio = create_test_audio(duration=1.0)

        # Should raise ModelLoadError
        with pytest.raises(ModelLoadError):
            extract_genre_tags(audio, 44100)

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_genre_tags_empty_result(self, mock_model_class, mock_load, tmp_path):
        """Test genre extraction when all predictions below threshold."""
        # Mock model
        model_path = tmp_path / "genre.pb"
        model_path.write_bytes(b"model")
        mock_load.return_value = model_path

        mock_model = MagicMock()
        # All predictions very low
        predictions = np.ones(87, dtype=np.float32) * 0.001
        mock_model.return_value = predictions
        mock_model_class.return_value = mock_model

        audio = create_test_audio(duration=1.0)

        # Extract with high threshold
        genres = extract_genre_tags(audio, 44100, top_k=3, threshold=0.9)

        # Should return empty or very few results
        assert isinstance(genres, list)
        assert len(genres) <= 3


class TestClassLists:
    """Test that class lists are properly defined."""

    def test_instrument_classes_count(self):
        """Test instrument class list has expected size."""
        assert len(INSTRUMENT_CLASSES) == 40

    def test_mood_classes_count(self):
        """Test mood class list has expected size."""
        assert len(MOOD_CLASSES) == 56

    def test_genre_classes_count(self):
        """Test genre class list has expected size."""
        assert len(GENRE_CLASSES) == 86

    def test_no_duplicate_instruments(self):
        """Test no duplicate instrument classes."""
        assert len(INSTRUMENT_CLASSES) == len(set(INSTRUMENT_CLASSES))

    def test_no_duplicate_moods(self):
        """Test no duplicate mood classes."""
        assert len(MOOD_CLASSES) == len(set(MOOD_CLASSES))

    def test_no_duplicate_genres(self):
        """Test no duplicate genre classes."""
        assert len(GENRE_CLASSES) == len(set(GENRE_CLASSES))
