"""Golden file regression tests for audio analysis."""
import pytest
import json
import soundfile as sf
from pathlib import Path
from audiomancer.analyzers.basic import get_basic_metadata
from audiomancer.analyzers.spectral import extract_spectral_features
from tests.utils import create_test_audio
import librosa


class TestGoldenAnalysis:
    """Test that analysis results match expected golden file values."""

    def test_kick_basic_metadata_golden(self, tmp_path, golden_dir):
        """Test basic metadata matches golden file expectations."""
        # Load golden file
        golden_path = golden_dir / "kick_analysis.json"
        with open(golden_path) as f:
            golden = json.load(f)

        # Create test audio matching golden spec
        spec = golden['test_audio']
        audio = create_test_audio(
            duration=spec['duration'],
            sample_rate=spec['sample_rate'],
            frequency=spec['frequency'],
            waveform=spec['waveform']
        )

        # Save to file
        test_path = tmp_path / "test_kick.wav"
        sf.write(str(test_path), audio, spec['sample_rate'])

        # Extract metadata
        metadata = get_basic_metadata(test_path)

        # Validate against golden expectations
        expected = golden['basic_metadata']

        # Duration should match within 1ms tolerance
        assert abs(metadata['duration_ms'] - expected['duration_ms']) < 1.0

        # Exact matches for these fields
        assert metadata['sample_rate'] == expected['sample_rate']
        assert metadata['channels'] == expected['channels']
        assert metadata['bit_depth'] == expected['bit_depth']

        # File size should be positive
        assert metadata['file_size_bytes'] > 0

        # Hash should be valid SHA256 (64 hex chars)
        assert len(metadata['file_hash']) == 64

    def test_kick_spectral_features_golden(self, golden_dir):
        """Test spectral features match golden file expectations."""
        # Load golden file
        golden_path = golden_dir / "kick_analysis.json"
        with open(golden_path) as f:
            golden = json.load(f)

        # Create test audio matching golden spec
        spec = golden['test_audio']
        audio = create_test_audio(
            duration=spec['duration'],
            sample_rate=spec['sample_rate'],
            frequency=spec['frequency'],
            waveform=spec['waveform']
        )

        # Extract spectral features
        features = extract_spectral_features(audio, spec['sample_rate'])

        # Validate against golden expectations (using ranges)
        expected = golden['spectral_features']

        # Check each feature is within expected range
        for feature_name, feature_value in features.items():
            if feature_name in expected:
                expected_range = expected[feature_name]
                min_val = expected_range['min']
                max_val = expected_range['max']

                assert min_val <= feature_value <= max_val, (
                    f"{feature_name} = {feature_value} is outside expected range "
                    f"[{min_val}, {max_val}]. {expected_range.get('description', '')}"
                )

    def test_spectral_centroid_tracks_frequency(self):
        """Test that spectral centroid tracks different frequencies correctly."""
        # Create pure sines at different frequencies
        frequencies = [100, 440, 1000, 4000]
        centroids = []

        for freq in frequencies:
            audio = create_test_audio(
                duration=0.5,
                sample_rate=44100,
                frequency=freq,
                waveform='sine'
            )
            features = extract_spectral_features(audio, 44100)
            centroids.append(features['spectral_centroid'])

        # Centroids should increase monotonically with frequency
        for i in range(len(centroids) - 1):
            assert centroids[i] < centroids[i + 1], (
                f"Centroid should increase with frequency: "
                f"{frequencies[i]}Hz → {centroids[i]}, "
                f"{frequencies[i+1]}Hz → {centroids[i+1]}"
            )

    def test_rms_energy_consistency(self):
        """Test that RMS energy is consistent for same amplitude signals."""
        # Create different waveforms with same amplitude
        waveforms = ['sine', 'square', 'saw']
        rms_values = []

        for waveform in waveforms:
            audio = create_test_audio(
                duration=0.5,
                sample_rate=44100,
                frequency=440,
                waveform=waveform
            )
            features = extract_spectral_features(audio, 44100)
            rms_values.append(features['rms_energy'])

        # All should have reasonable energy (between 0.5 and 1.0)
        for rms in rms_values:
            assert 0.5 <= rms <= 1.0

    def test_analysis_pipeline_integration(self, tmp_path):
        """Test full analysis pipeline: metadata + spectral."""
        # Create test audio
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        test_path = tmp_path / "integration_test.wav"
        sf.write(str(test_path), audio, 44100)

        # Run both analyzers
        metadata = get_basic_metadata(test_path)

        # Load audio for spectral analysis
        y, sr = librosa.load(str(test_path), sr=None)
        features = extract_spectral_features(y, sr)

        # Verify we can combine results
        complete_analysis = {
            'basic': dict(metadata),
            'spectral': dict(features)
        }

        # Should have all expected fields
        assert 'basic' in complete_analysis
        assert 'spectral' in complete_analysis
        assert 'duration_ms' in complete_analysis['basic']
        assert 'spectral_centroid' in complete_analysis['spectral']

        # Consistency checks
        assert complete_analysis['basic']['sample_rate'] == sr
        assert complete_analysis['basic']['duration_ms'] > 0
        assert complete_analysis['spectral']['rms_energy'] > 0
