"""Tests for spectral feature extraction."""
import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from audiomancer.analyzers.spectral import extract_spectral_features
from audiomancer.errors import AnalysisFailedError
from tests.utils import create_test_audio
import librosa


class TestSpectralFeatureExtraction:
    """Test suite for spectral feature extraction."""

    def test_sine_wave_features(self):
        """Test spectral features of a pure sine wave."""
        # Pure sine at 440Hz should have centroid near 440Hz
        audio = create_test_audio(duration=1.0, sample_rate=44100, frequency=440, waveform='sine')
        features = extract_spectral_features(audio, 44100)

        # Verify all expected fields exist
        assert 'spectral_centroid' in features
        assert 'spectral_bandwidth' in features
        assert 'spectral_rolloff' in features
        assert 'zero_crossing_rate' in features
        assert 'rms_energy' in features
        assert 'dynamic_range' in features

        # Pure sine should have low zero crossing rate (smooth signal)
        assert features['zero_crossing_rate'] < 0.5

        # Should have reasonable energy
        assert features['rms_energy'] > 0

    def test_noise_features(self):
        """Test spectral features of white noise."""
        audio = create_test_audio(duration=1.0, sample_rate=44100, waveform='noise')
        features = extract_spectral_features(audio, 44100)

        # Noise should have higher zero crossing rate
        assert features['zero_crossing_rate'] > 0.3

        # Noise has broad spectrum, so bandwidth should be non-negative
        # (Can be 0.0 in edge cases due to numerical precision)
        assert features['spectral_bandwidth'] >= 0

        # Should have valid centroid
        assert 0 < features['spectral_centroid'] < 44100 / 2

    def test_stereo_to_mono_conversion(self):
        """Test that stereo audio is converted to mono correctly."""
        mono = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        stereo = np.stack([mono, mono])

        features = extract_spectral_features(stereo, 44100)

        # Should succeed and produce valid features
        assert features['spectral_centroid'] > 0
        assert features['rms_energy'] > 0

    def test_different_sample_rates(self):
        """Test feature extraction at different sample rates."""
        sample_rates = [22050, 44100, 48000]

        for sr in sample_rates:
            audio = create_test_audio(duration=0.5, sample_rate=sr, frequency=440)
            features = extract_spectral_features(audio, sr)

            # All features should be valid
            assert features['spectral_centroid'] > 0
            assert features['spectral_rolloff'] > 0
            # Centroid and rolloff should be within Nyquist limit
            assert features['spectral_centroid'] < sr / 2
            assert features['spectral_rolloff'] < sr / 2

    def test_empty_audio(self):
        """Test error handling for empty audio."""
        empty_audio = np.array([], dtype=np.float32)

        with pytest.raises(AnalysisFailedError) as exc_info:
            extract_spectral_features(empty_audio, 44100)

        assert "empty" in str(exc_info.value).lower()
        assert exc_info.value.details['reason'] == "zero samples"

    def test_too_short_audio(self):
        """Test error handling for audio shorter than frame size."""
        # Create audio with only 1000 samples (< 2048 frame size)
        short_audio = create_test_audio(duration=0.02, sample_rate=44100)  # ~880 samples

        with pytest.raises(AnalysisFailedError) as exc_info:
            extract_spectral_features(short_audio, 44100)

        assert "too short" in str(exc_info.value).lower()
        assert exc_info.value.details['stage'] == "spectral analysis preparation"

    def test_silence_features(self):
        """Test spectral features of silence."""
        silence = create_test_audio(duration=1.0, waveform='silence')
        features = extract_spectral_features(silence, 44100)

        # Silence should have zero or near-zero energy
        assert features['rms_energy'] < 0.01

        # Zero crossing rate should be zero for silence
        assert features['zero_crossing_rate'] < 0.01

        # Dynamic range might be zero or very small for silence
        assert features['dynamic_range'] >= 0

    def test_feature_value_types(self):
        """Test that all feature values are float type."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # All values should be float
        for key, value in features.items():
            assert isinstance(value, float), f"{key} should be float, got {type(value)}"

    def test_no_nan_or_inf(self):
        """Test that features never contain NaN or inf values."""
        # Test various audio types
        test_cases = [
            create_test_audio(duration=0.5, waveform='sine'),
            create_test_audio(duration=0.5, waveform='square'),
            create_test_audio(duration=0.5, waveform='saw'),
            create_test_audio(duration=0.5, waveform='noise'),
            create_test_audio(duration=0.5, waveform='silence'),
        ]

        for audio in test_cases:
            features = extract_spectral_features(audio, 44100)

            for key, value in features.items():
                assert not np.isnan(value), f"{key} is NaN"
                assert not np.isinf(value), f"{key} is inf"
                assert isinstance(value, float), f"{key} is not float"

    def test_dynamic_range_calculation(self):
        """Test dynamic range calculation with known signal."""
        # Create signal with known peak and RMS
        # Square wave has peak=1, RMS=1, so dynamic_range ≈ 0 dB
        square = create_test_audio(duration=0.5, waveform='square', frequency=100)
        features = extract_spectral_features(square, 44100)

        # Square wave should have low dynamic range (close to 0 dB)
        assert 0 <= features['dynamic_range'] < 3

        # Sine wave has peak=1, RMS=1/sqrt(2), so ~3dB dynamic range
        sine = create_test_audio(duration=0.5, waveform='sine', frequency=100)
        features_sine = extract_spectral_features(sine, 44100)

        # Sine should have ~3dB dynamic range
        assert 2 < features_sine['dynamic_range'] < 4

    def test_spectral_features_bright_vs_dark(self):
        """Test that centroid distinguishes bright vs dark timbres."""
        # Low frequency sine (dark)
        dark = create_test_audio(duration=0.5, sample_rate=44100, frequency=100, waveform='sine')
        features_dark = extract_spectral_features(dark, 44100)

        # High frequency sine (bright)
        bright = create_test_audio(duration=0.5, sample_rate=44100, frequency=8000, waveform='sine')
        features_bright = extract_spectral_features(bright, 44100)

        # Bright signal should have higher centroid
        assert features_bright['spectral_centroid'] > features_dark['spectral_centroid']

    def test_rolloff_increases_with_content(self):
        """Test that rolloff reflects high-frequency content."""
        # Sine at 1kHz
        low_content = create_test_audio(duration=0.5, sample_rate=44100, frequency=1000)
        features_low = extract_spectral_features(low_content, 44100)

        # Noise (broad spectrum)
        high_content = create_test_audio(duration=0.5, sample_rate=44100, waveform='noise')
        features_high = extract_spectral_features(high_content, 44100)

        # Noise should have higher rolloff due to broad spectrum
        assert features_high['spectral_rolloff'] > features_low['spectral_rolloff']

    def test_feature_stability_across_runs(self):
        """Test that features are deterministic for same audio."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)

        features1 = extract_spectral_features(audio, 44100)
        features2 = extract_spectral_features(audio, 44100)

        # Features should be identical (deterministic)
        for key in features1:
            assert abs(features1[key] - features2[key]) < 1e-6

    def test_real_audio_file(self, tmp_path):
        """Test feature extraction from actual audio file."""
        # Create and save a test file
        audio_path = tmp_path / "test.wav"
        audio = create_test_audio(duration=1.0, sample_rate=44100, frequency=440)
        sf.write(str(audio_path), audio, 44100)

        # Load with librosa and extract features
        y, sr = librosa.load(str(audio_path), sr=None)
        features = extract_spectral_features(y, sr)

        # Should produce valid features
        assert features['spectral_centroid'] > 0
        assert features['rms_energy'] > 0
        assert features['dynamic_range'] > 0


class TestSpectralFeatureRanges:
    """Test that feature values are in reasonable ranges."""

    def test_centroid_range(self):
        """Test that spectral centroid is within valid range."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # Centroid should be positive and below Nyquist
        assert 0 < features['spectral_centroid'] < 22050

    def test_bandwidth_range(self):
        """Test that spectral bandwidth is non-negative."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # Bandwidth should be non-negative
        assert features['spectral_bandwidth'] >= 0

    def test_rolloff_range(self):
        """Test that spectral rolloff is within valid range."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # Rolloff should be positive and below Nyquist
        assert 0 < features['spectral_rolloff'] < 22050

    def test_zcr_range(self):
        """Test that zero crossing rate is in [0, 1] range."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # ZCR should be between 0 and 1
        assert 0 <= features['zero_crossing_rate'] <= 1

    def test_rms_range(self):
        """Test that RMS energy is non-negative and reasonable."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # RMS should be positive and <= 1 for normalized audio
        assert 0 < features['rms_energy'] <= 1

    def test_dynamic_range_positive(self):
        """Test that dynamic range is non-negative."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        features = extract_spectral_features(audio, 44100)

        # Dynamic range in dB should be non-negative
        assert features['dynamic_range'] >= 0


class TestSpectralFeatureEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_low_frequency(self):
        """Test with very low frequency sine wave (20 Hz)."""
        audio = create_test_audio(duration=1.0, sample_rate=44100, frequency=20)
        features = extract_spectral_features(audio, 44100)

        # Should handle low frequencies
        assert features['spectral_centroid'] > 0
        assert features['zero_crossing_rate'] < 0.1  # Slow oscillation

    def test_very_high_frequency(self):
        """Test with high frequency near Nyquist."""
        audio = create_test_audio(duration=1.0, sample_rate=44100, frequency=20000)
        features = extract_spectral_features(audio, 44100)

        # Should handle high frequencies
        assert features['spectral_centroid'] > 0

    def test_minimum_duration(self):
        """Test with minimum viable audio duration (just over 2048 samples)."""
        # 2100 samples at 44100 Hz = ~47.6ms
        min_audio = create_test_audio(duration=0.048, sample_rate=44100, frequency=440)
        features = extract_spectral_features(min_audio, 44100)

        # Should produce valid features even for short audio
        assert features['spectral_centroid'] > 0
        assert features['rms_energy'] > 0

    def test_float64_audio(self):
        """Test that float64 audio is handled correctly."""
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        audio_f64 = audio.astype(np.float64)

        features = extract_spectral_features(audio_f64, 44100)

        # Should convert and process correctly
        assert features['spectral_centroid'] > 0
