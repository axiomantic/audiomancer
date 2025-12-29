"""Tests for basic audio metadata extraction."""
import pytest
from pathlib import Path
import soundfile as sf
import numpy as np
from audiomancer.analyzers.basic import get_basic_metadata
from audiomancer.errors import UnsupportedFormatError, AnalysisFailedError
from tests.utils import create_test_audio


class TestBasicMetadataExtraction:
    """Test suite for basic metadata extraction."""

    def test_valid_mono_audio(self, tmp_path):
        """Test metadata extraction from mono audio file."""
        # Create test audio file
        audio_path = tmp_path / "test_mono.wav"
        audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
        sf.write(str(audio_path), audio, 44100)

        # Extract metadata
        metadata = get_basic_metadata(audio_path)

        # Verify basic fields exist
        assert 'duration_ms' in metadata
        assert 'sample_rate' in metadata
        assert 'channels' in metadata
        assert 'bit_depth' in metadata
        assert 'file_size_bytes' in metadata
        assert 'file_hash' in metadata

        # Verify values
        assert metadata['sample_rate'] == 44100
        assert metadata['channels'] == 1
        assert metadata['bit_depth'] == 16
        assert 499 <= metadata['duration_ms'] <= 501  # ~500ms with tolerance
        assert metadata['file_size_bytes'] > 0
        assert len(metadata['file_hash']) == 64  # SHA256 hex length

    def test_valid_stereo_audio(self, tmp_path):
        """Test metadata extraction from stereo audio file."""
        # Create stereo test audio
        audio_path = tmp_path / "test_stereo.wav"
        mono = create_test_audio(duration=1.0, sample_rate=48000, frequency=880)
        stereo = np.stack([mono, mono])  # Duplicate to stereo
        sf.write(str(audio_path), stereo.T, 48000)  # Transpose for soundfile

        # Extract metadata
        metadata = get_basic_metadata(audio_path)

        # Verify stereo detection
        assert metadata['sample_rate'] == 48000
        assert metadata['channels'] == 2
        assert 999 <= metadata['duration_ms'] <= 1001  # ~1000ms

    def test_different_sample_rates(self, tmp_path):
        """Test that native sample rate is preserved."""
        sample_rates = [22050, 44100, 48000, 96000]

        for sr in sample_rates:
            audio_path = tmp_path / f"test_{sr}.wav"
            audio = create_test_audio(duration=0.1, sample_rate=sr)
            sf.write(str(audio_path), audio, sr)

            metadata = get_basic_metadata(audio_path)
            assert metadata['sample_rate'] == sr

    def test_hash_consistency(self, tmp_path):
        """Test that identical files produce identical hashes."""
        # Create two identical files
        audio = create_test_audio(duration=0.5, sample_rate=44100)

        path1 = tmp_path / "file1.wav"
        path2 = tmp_path / "file2.wav"

        sf.write(str(path1), audio, 44100)
        sf.write(str(path2), audio, 44100)

        meta1 = get_basic_metadata(path1)
        meta2 = get_basic_metadata(path2)

        assert meta1['file_hash'] == meta2['file_hash']

    def test_hash_uniqueness(self, tmp_path):
        """Test that different files produce different hashes."""
        audio1 = create_test_audio(duration=0.5, frequency=440)
        audio2 = create_test_audio(duration=0.5, frequency=880)

        path1 = tmp_path / "file1.wav"
        path2 = tmp_path / "file2.wav"

        sf.write(str(path1), audio1, 44100)
        sf.write(str(path2), audio2, 44100)

        meta1 = get_basic_metadata(path1)
        meta2 = get_basic_metadata(path2)

        assert meta1['file_hash'] != meta2['file_hash']

    def test_nonexistent_file(self, tmp_path):
        """Test error handling for nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.wav"

        with pytest.raises(UnsupportedFormatError) as exc_info:
            get_basic_metadata(nonexistent)

        assert "does not exist" in str(exc_info.value)
        assert exc_info.value.details['path'] == str(nonexistent)

    def test_invalid_format(self, tmp_path):
        """Test error handling for unsupported format."""
        # Create a text file with .wav extension
        invalid_path = tmp_path / "invalid.wav"
        invalid_path.write_text("not an audio file")

        with pytest.raises(UnsupportedFormatError) as exc_info:
            get_basic_metadata(invalid_path)

        assert "Cannot load audio file" in str(exc_info.value)
        assert exc_info.value.details['path'] == str(invalid_path)

    def test_empty_audio_file(self, tmp_path):
        """Test error handling for empty audio file."""
        # Create file with zero samples
        empty_path = tmp_path / "empty.wav"
        sf.write(str(empty_path), np.array([], dtype=np.float32), 44100)

        with pytest.raises(AnalysisFailedError) as exc_info:
            get_basic_metadata(empty_path)

        assert "empty" in str(exc_info.value).lower()
        assert exc_info.value.details['reason'] == "zero samples"

    def test_very_short_audio(self, tmp_path):
        """Test metadata extraction from very short audio (< 10ms)."""
        # Create extremely short audio (1ms = 44 samples at 44.1kHz)
        short_path = tmp_path / "very_short.wav"
        audio = create_test_audio(duration=0.001, sample_rate=44100)
        sf.write(str(short_path), audio, 44100)

        metadata = get_basic_metadata(short_path)

        # Should succeed and have approximately correct duration
        assert 0.9 <= metadata['duration_ms'] <= 1.1
        assert metadata['sample_rate'] == 44100

    def test_different_waveforms(self, tmp_path):
        """Test metadata extraction works for different waveform types."""
        waveforms = ['sine', 'square', 'saw', 'noise']

        for waveform in waveforms:
            audio_path = tmp_path / f"test_{waveform}.wav"
            audio = create_test_audio(
                duration=0.25,
                sample_rate=44100,
                waveform=waveform
            )
            sf.write(str(audio_path), audio, 44100)

            metadata = get_basic_metadata(audio_path)

            # All waveforms should produce valid metadata
            assert metadata['sample_rate'] == 44100
            assert metadata['channels'] == 1
            assert 249 <= metadata['duration_ms'] <= 251

    def test_silence(self, tmp_path):
        """Test metadata extraction from silent audio."""
        silence_path = tmp_path / "silence.wav"
        audio = create_test_audio(duration=0.5, waveform='silence')
        sf.write(str(silence_path), audio, 44100)

        metadata = get_basic_metadata(silence_path)

        # Silence should still produce valid metadata
        assert metadata['sample_rate'] == 44100
        assert metadata['duration_ms'] > 0
        assert metadata['file_size_bytes'] > 0


class TestBasicMetadataTypes:
    """Test that metadata values have correct types."""

    def test_metadata_types(self, tmp_path):
        """Verify all metadata fields have expected types."""
        audio_path = tmp_path / "test.wav"
        audio = create_test_audio(duration=0.5, sample_rate=44100)
        sf.write(str(audio_path), audio, 44100)

        metadata = get_basic_metadata(audio_path)

        # Type checks
        assert isinstance(metadata['duration_ms'], float)
        assert isinstance(metadata['sample_rate'], int)
        assert isinstance(metadata['channels'], int)
        assert isinstance(metadata['bit_depth'], int)
        assert isinstance(metadata['file_size_bytes'], int)
        assert isinstance(metadata['file_hash'], str)

    def test_metadata_value_ranges(self, tmp_path):
        """Verify metadata values are in reasonable ranges."""
        audio_path = tmp_path / "test.wav"
        audio = create_test_audio(duration=0.5, sample_rate=44100)
        sf.write(str(audio_path), audio, 44100)

        metadata = get_basic_metadata(audio_path)

        # Value range checks
        assert metadata['duration_ms'] > 0
        assert metadata['sample_rate'] > 0
        assert metadata['channels'] > 0
        assert metadata['bit_depth'] > 0
        assert metadata['file_size_bytes'] > 0
        assert len(metadata['file_hash']) == 64  # SHA256


class TestBasicMetadataEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_maximum_sample_rate(self, tmp_path):
        """Test with very high sample rate (192kHz)."""
        audio_path = tmp_path / "high_sr.wav"
        audio = create_test_audio(duration=0.1, sample_rate=192000)
        sf.write(str(audio_path), audio, 192000)

        metadata = get_basic_metadata(audio_path)
        assert metadata['sample_rate'] == 192000

    def test_pathlib_path(self, tmp_path):
        """Test that function accepts pathlib.Path objects."""
        audio_path = tmp_path / "test.wav"
        audio = create_test_audio(duration=0.5, sample_rate=44100)
        sf.write(str(audio_path), audio, 44100)

        # Should work with Path object
        metadata = get_basic_metadata(audio_path)
        assert metadata['sample_rate'] == 44100

    def test_long_duration(self, tmp_path):
        """Test with longer audio file (10 seconds)."""
        audio_path = tmp_path / "long.wav"
        audio = create_test_audio(duration=10.0, sample_rate=44100)
        sf.write(str(audio_path), audio, 44100)

        metadata = get_basic_metadata(audio_path)

        # Should handle long files correctly
        assert 9990 <= metadata['duration_ms'] <= 10010  # ~10000ms
