"""Tests for rhythm analysis module."""

import pytest
import numpy as np

from audiomancer.analyzers.rhythm import extract_rhythm_features
from audiomancer.errors import AnalysisFailedError


class TestRhythmAnalyzer:
    """Test cases for rhythm feature extraction."""

    def test_extract_rhythm_from_silence(self, sample_audio_data):
        """Test that silence returns None for BPM."""
        silence = sample_audio_data["silence"]
        sr = sample_audio_data["sample_rate"]

        features = extract_rhythm_features(silence, sr)

        assert features['bpm'] is None
        assert features['bpm_confidence'] == 0.0
        assert features['beat_positions'] == []
        assert features['is_loop'] is False

    def test_extract_rhythm_from_sine_wave(self, sample_audio_data):
        """Test that pure tone (non-rhythmic) returns None for BPM."""
        sine = sample_audio_data["sine_440"]
        sr = sample_audio_data["sample_rate"]

        features = extract_rhythm_features(sine, sr)

        # Pure sine wave has no rhythm
        assert features['bpm'] is None
        assert features['bpm_confidence'] < 0.5  # Low confidence
        assert features['is_loop'] is False

    def test_extract_rhythm_from_impulse(self, sample_audio_data):
        """Test that impulse (single transient) has low confidence."""
        impulse = sample_audio_data["impulse"]
        sr = sample_audio_data["sample_rate"]

        features = extract_rhythm_features(impulse, sr)

        # Single impulse is not enough to determine tempo
        assert features['bpm'] is None or features['bpm_confidence'] < 0.3

    def test_extract_rhythm_from_4_4_loop(self):
        """Test loop detection for 4/4 time signature."""
        # Generate 4-bar loop at 120 BPM (8 seconds)
        sr = 44100
        bpm = 120
        bars = 4
        duration = (60.0 / bpm) * 4 * bars  # 8 seconds

        # Create kick pattern: kick on every beat (4 kicks per bar)
        samples = int(sr * duration)
        audio = np.zeros(samples, dtype=np.float32)

        beat_duration = 60.0 / bpm
        for bar in range(bars):
            for beat in range(4):
                # Place impulse at each beat
                sample_pos = int(sr * (bar * 4 + beat) * beat_duration)
                if sample_pos < len(audio):
                    # Create short kick-like envelope
                    kick_len = int(sr * 0.1)  # 100ms
                    kick = np.exp(-np.linspace(0, 10, kick_len))
                    audio[sample_pos:sample_pos+kick_len] = kick[:min(kick_len, len(audio)-sample_pos)]

        features = extract_rhythm_features(audio, sr)

        # Should detect as a loop
        assert features['is_loop'] is True

        # BPM might not be exactly 120 but should be detected
        if features['bpm'] is not None:
            assert 100 <= features['bpm'] <= 140  # Within reasonable range

    def test_rhythm_features_shape(self, sample_audio_data):
        """Test that all returned features have expected types."""
        sine = sample_audio_data["sine_440"]
        sr = sample_audio_data["sample_rate"]

        features = extract_rhythm_features(sine, sr)

        # Check return value structure
        assert 'bpm' in features
        assert 'bpm_confidence' in features
        assert 'beat_positions' in features
        assert 'is_loop' in features

        # Check types
        assert features['bpm'] is None or isinstance(features['bpm'], float)
        assert isinstance(features['bpm_confidence'], float)
        assert isinstance(features['beat_positions'], list)
        assert isinstance(features['is_loop'], bool)

        # Check confidence is in valid range
        assert 0.0 <= features['bpm_confidence'] <= 1.0

    def test_stereo_to_mono_conversion(self):
        """Test that stereo audio is converted to mono."""
        sr = 44100
        duration = 1.0
        samples = int(sr * duration)

        # Create stereo audio (2 channels)
        left = np.random.randn(samples).astype(np.float32) * 0.1
        right = np.random.randn(samples).astype(np.float32) * 0.1
        stereo = np.stack([left, right], axis=0)

        # Should not raise an error
        features = extract_rhythm_features(stereo, sr)

        assert isinstance(features, dict)
        assert 'bpm' in features

    def test_empty_audio_raises_error(self):
        """Test that empty audio raises AnalysisFailedError."""
        empty_audio = np.array([], dtype=np.float32)
        sr = 44100

        with pytest.raises(AnalysisFailedError) as exc_info:
            extract_rhythm_features(empty_audio, sr)

        assert "empty" in str(exc_info.value).lower()

    def test_nan_audio_returns_none(self):
        """Test that NaN audio returns None for BPM."""
        nan_audio = np.full(44100, np.nan, dtype=np.float32)
        sr = 44100

        features = extract_rhythm_features(nan_audio, sr)

        assert features['bpm'] is None
        assert features['bpm_confidence'] == 0.0

    def test_long_audio_not_marked_as_loop(self):
        """Test that long audio (>30s) is not marked as loop."""
        sr = 44100
        duration = 35.0  # Longer than 30s
        samples = int(sr * duration)

        # Create rhythmic pattern
        audio = np.random.randn(samples).astype(np.float32) * 0.1

        features = extract_rhythm_features(audio, sr)

        # Should not be marked as loop due to duration
        assert features['is_loop'] is False

    def test_beat_positions_are_sorted(self):
        """Test that beat positions are in ascending order."""
        # Generate simple rhythmic audio
        sr = 44100
        duration = 2.0
        samples = int(sr * duration)
        audio = np.zeros(samples, dtype=np.float32)

        # Add beats every 0.5 seconds
        for i in range(4):
            pos = int(sr * i * 0.5)
            if pos < len(audio):
                audio[pos] = 1.0

        features = extract_rhythm_features(audio, sr)

        # Check beat positions are sorted
        beat_positions = features['beat_positions']
        if len(beat_positions) > 1:
            assert all(beat_positions[i] <= beat_positions[i+1]
                      for i in range(len(beat_positions)-1))

    def test_no_nan_or_inf_in_output(self, sample_audio_data):
        """Test that output never contains NaN or inf values."""
        for audio_type in ["silence", "sine_440", "impulse"]:
            audio = sample_audio_data[audio_type]
            sr = sample_audio_data["sample_rate"]

            features = extract_rhythm_features(audio, sr)

            # Check BPM
            if features['bpm'] is not None:
                assert not np.isnan(features['bpm'])
                assert not np.isinf(features['bpm'])

            # Check confidence
            assert not np.isnan(features['bpm_confidence'])
            assert not np.isinf(features['bpm_confidence'])

            # Check beat positions
            for pos in features['beat_positions']:
                assert not np.isnan(pos)
                assert not np.isinf(pos)
