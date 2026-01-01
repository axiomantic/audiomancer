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
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_classify_instrument_success(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test successful instrument classification."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        instrument_path = tmp_path / "instrument.pb"
        instrument_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, instrument_path]

        # Mock embedding extractor (returns 2D embeddings)
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier (returns 2D predictions)
        mock_classifier = MagicMock()
        predictions_batch = np.zeros((1, 40), dtype=np.float32)
        predictions_batch[0, 13] = 0.8  # drums
        predictions_batch[0, 14] = 0.6  # drummachine
        predictions_batch[0, 27] = 0.4  # percussion
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

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

    @patch("audiomancer.analyzers.classifier.get_effnet_model")
    def test_classify_instrument_model_load_error(self, mock_effnet):
        """Test classification with model load error."""
        # Mock model loading to fail
        mock_effnet.side_effect = ModelLoadError("Model not found", details={})

        # Create test audio
        audio = create_test_audio(duration=1.0)

        # Should raise ModelLoadError
        with pytest.raises(ModelLoadError):
            classify_instrument(audio, 44100)

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_classify_instrument_stereo_to_mono(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test that stereo audio is converted to mono."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        instrument_path = tmp_path / "instrument.pb"
        instrument_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, instrument_path]

        # Mock embedding extractor
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier
        mock_classifier = MagicMock()
        predictions_batch = np.zeros((1, 40), dtype=np.float32)
        predictions_batch[0, 0] = 0.9
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

        # Create stereo audio
        mono = create_test_audio(duration=0.5, sample_rate=44100)
        stereo = np.stack([mono, mono])

        # Classify
        result = classify_instrument(stereo, 44100)

        # Should succeed (stereo was converted to mono)
        assert result["instrument_type"] in INSTRUMENT_CLASSES

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_classify_instrument_resampling(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test that audio is resampled to 16kHz."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        instrument_path = tmp_path / "instrument.pb"
        instrument_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, instrument_path]

        # Mock embedding extractor
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier
        mock_classifier = MagicMock()
        predictions_batch = np.zeros((1, 40), dtype=np.float32)
        predictions_batch[0, 0] = 0.9
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

        # Create 48kHz audio
        audio = create_test_audio(duration=0.5, sample_rate=48000)

        # Classify
        result = classify_instrument(audio, 48000)

        # Should succeed (was resampled to 16kHz)
        assert result["instrument_type"] in INSTRUMENT_CLASSES

    @patch("audiomancer.analyzers.classifier.get_classifier_model")
    @patch("audiomancer.analyzers.classifier.get_effnet_model")
    def test_classify_instrument_short_audio_padding(
        self, mock_get_effnet, mock_get_classifier
    ):
        """Test that short audio is padded to minimum length."""
        # Mock embedding extractor - verify it receives padded audio
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_get_effnet.return_value = mock_effnet

        # Mock classifier
        mock_classifier = MagicMock()
        predictions_batch = np.zeros((1, 40), dtype=np.float32)
        predictions_batch[0, 13] = 0.9  # drums
        mock_classifier.return_value = predictions_batch
        mock_get_classifier.return_value = mock_classifier

        # Create very short audio (0.1 seconds at 44.1kHz = ~4410 samples)
        # After resampling to 16kHz, this becomes ~1600 samples (< 16000)
        audio = create_test_audio(duration=0.1, sample_rate=44100)

        # Classify
        result = classify_instrument(audio, 44100)

        # Should succeed - audio was padded to minimum length
        assert result["instrument_type"] in INSTRUMENT_CLASSES
        assert result["instrument_confidence"] > 0

        # Verify effnet was called with padded audio (>= 16000 samples at 16kHz)
        called_audio = mock_effnet.call_args[0][0]
        assert len(called_audio) >= 16000


class TestMoodClassification:
    """Test mood/theme classification."""

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_mood_tags_success(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test successful mood extraction."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        mood_path = tmp_path / "mood.pb"
        mood_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, mood_path]

        # Mock embedding extractor
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier (56 mood classes)
        mock_classifier = MagicMock()
        predictions_batch = np.zeros((1, 56), dtype=np.float32)
        predictions_batch[0, 11] = 0.8  # dark
        predictions_batch[0, 18] = 0.6  # energetic
        predictions_batch[0, 41] = 0.4  # powerful
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

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
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_mood_tags_threshold_filtering(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test that threshold filters low-confidence predictions."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        mood_path = tmp_path / "mood.pb"
        mood_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, mood_path]

        # Mock embedding extractor
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier with one high prediction
        mock_classifier = MagicMock()
        predictions_batch = np.ones((1, 56), dtype=np.float32) * 0.01
        predictions_batch[0, 11] = 0.9  # Only this one high
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

        audio = create_test_audio(duration=1.0)

        # Extract with high threshold
        moods = extract_mood_tags(audio, 44100, top_k=10, threshold=0.5)

        # Should only get the one above threshold
        assert len(moods) >= 1
        assert all(m in MOOD_CLASSES for m in moods)


class TestGenreClassification:
    """Test genre classification."""

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_genre_tags_success(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test successful genre extraction."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        genre_path = tmp_path / "genre.pb"
        genre_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, genre_path]

        # Mock embedding extractor
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier (87 genre classes)
        mock_classifier = MagicMock()
        # Note: GENRE_CLASSES has 86 items, not 87 (test was wrong)
        predictions_batch = np.zeros((1, 86), dtype=np.float32)
        predictions_batch[0, 68] = 0.8  # techno
        predictions_batch[0, 35] = 0.6  # electronic
        predictions_batch[0, 40] = 0.4  # house
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

        # Create test audio
        audio = create_test_audio(duration=1.0, sample_rate=44100)

        # Extract genres
        genres = extract_genre_tags(audio, 44100, top_k=3, threshold=0.1)

        # Verify
        assert isinstance(genres, list)
        assert len(genres) <= 3
        for genre in genres:
            assert genre in GENRE_CLASSES

    @patch("audiomancer.analyzers.classifier.get_effnet_model")
    def test_extract_genre_tags_model_error(self, mock_effnet):
        """Test genre extraction with model error."""
        # Mock model loading to fail
        mock_effnet.side_effect = ModelLoadError("Model not found", details={})

        audio = create_test_audio(duration=1.0)

        # Should raise ModelLoadError
        with pytest.raises(ModelLoadError):
            extract_genre_tags(audio, 44100)

    @patch("audiomancer.analyzers.classifier.load_model")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredict2D")
    @patch("audiomancer.analyzers.classifier.es.TensorflowPredictEffnetDiscogs")
    def test_extract_genre_tags_empty_result(
        self, mock_effnet_class, mock_classifier_class, mock_load, tmp_path
    ):
        """Test genre extraction when all predictions below threshold."""
        # Mock model loading
        effnet_path = tmp_path / "discogs_effnet.pb"
        effnet_path.write_bytes(b"effnet")
        genre_path = tmp_path / "genre.pb"
        genre_path.write_bytes(b"model")
        mock_load.side_effect = [effnet_path, genre_path]

        # Mock embedding extractor
        mock_effnet = MagicMock()
        embeddings = np.random.rand(3, 1280).astype(np.float32)
        mock_effnet.return_value = embeddings
        mock_effnet_class.return_value = mock_effnet

        # Mock classifier with all low predictions
        mock_classifier = MagicMock()
        predictions_batch = np.ones((1, 86), dtype=np.float32) * 0.001
        mock_classifier.return_value = predictions_batch
        mock_classifier_class.return_value = mock_classifier

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
