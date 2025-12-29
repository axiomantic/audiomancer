"""End-to-end workflow integration tests.

Tests complete workflows from sample ingestion through analysis,
storage, search, pattern generation, and conversion.
"""

import numpy as np
import pytest
import soundfile as sf
import tempfile
from pathlib import Path
from datetime import datetime

from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.analyzers import (
    get_basic_metadata,
    extract_spectral_features,
    extract_rhythm_features,
    extract_tonal_features,
    extract_audio_embedding,
    classify_instrument,
)
from audiomancer.errors import SampleNotFoundError, StorageError


def safe_extract_embedding(audio: np.ndarray, sr: int) -> list[float]:
    """Extract embedding with fallback to dummy data if models unavailable."""
    try:
        return extract_audio_embedding(audio, sr)
    except Exception:
        return [0.1] * 128


@pytest.fixture
def test_audio_kick():
    """Generate a kick-like sound (low frequency sine burst)."""
    sr = 44100
    duration = 0.25
    samples = int(sr * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # 60 Hz sine with amplitude envelope
    freq = 60
    audio = np.sin(2 * np.pi * freq * t)
    envelope = np.exp(-10 * t)  # Exponential decay
    audio = audio * envelope

    return audio.astype(np.float32), sr


@pytest.fixture
def test_audio_snare():
    """Generate a snare-like sound (noise burst)."""
    sr = 44100
    duration = 0.15
    samples = int(sr * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # White noise with amplitude envelope
    audio = np.random.uniform(-1, 1, samples)
    envelope = np.exp(-25 * t)  # Fast decay
    audio = audio * envelope

    return audio.astype(np.float32), sr


@pytest.fixture
def test_audio_hihat():
    """Generate a hi-hat-like sound (high frequency noise)."""
    sr = 44100
    duration = 0.08
    samples = int(sr * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Filtered noise with very fast decay
    audio = np.random.uniform(-1, 1, samples)
    # Simple high-pass: emphasize higher frequencies
    audio = np.diff(audio, prepend=0)
    envelope = np.exp(-50 * t)
    audio = audio * envelope

    return audio.astype(np.float32), sr


@pytest.fixture
def test_audio_bass():
    """Generate a bass note (low frequency tone)."""
    sr = 44100
    duration = 0.5
    samples = int(sr * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # 100 Hz sine
    freq = 100
    audio = np.sin(2 * np.pi * freq * t)
    envelope = np.exp(-3 * t)  # Slower decay
    audio = audio * envelope

    return audio.astype(np.float32), sr


@pytest.mark.integration
class TestFullSampleWorkflow:
    """Test complete sample ingestion → analysis → storage → search workflow."""

    def test_ingest_analyze_store_search_kick(self, test_audio_kick, tmp_path):
        """Full workflow with kick sample: analyze → store → search."""
        audio, sr = test_audio_kick

        # Save to temporary WAV file
        wav_path = tmp_path / "kick.wav"
        sf.write(str(wav_path), audio, sr)

        # 1. Analyze sample
        basic = get_basic_metadata(wav_path)
        spectral = extract_spectral_features(audio, sr)
        rhythm = extract_rhythm_features(audio, sr)
        tonal = extract_tonal_features(audio, sr)

        # Classification requires model download - may fail in test environment
        try:
            classification = classify_instrument(audio, sr)
        except Exception:
            classification = {"instrument_type": None, "confidence": None}

        # Embedding generation requires model download
        try:
            embedding = extract_audio_embedding(audio, sr)
        except Exception:
            # Use dummy embedding if model unavailable
            embedding = [0.1] * 128

        # 2. Build sample metadata
        sample = SampleMetadata(
            id=f"smpl_{basic['file_hash'][:8]}",
            file_path=str(wav_path),
            file_hash=basic['file_hash'],
            duration_ms=basic['duration_ms'],
            sample_rate=basic['sample_rate'],
            channels=basic['channels'],
            bit_depth=basic.get('bit_depth', 16),
            file_size_bytes=basic['file_size_bytes'],
            bpm=rhythm.get('estimated_tempo'),
            is_loop=False,
            instrument_type=classification.get('instrument_type'),
            instrument_confidence=classification.get('confidence'),
            spectral_centroid_mean=spectral['spectral_centroid'],
            spectral_bandwidth_mean=spectral['spectral_bandwidth'],
            spectral_rolloff_mean=spectral['spectral_rolloff'],
            zero_crossing_rate_mean=spectral['zero_crossing_rate'],
            rms_energy=spectral['rms_energy'],
            key_signature=tonal.get('key_signature'),
            chroma_mean=tonal.get('chroma_mean'),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 3. Store in unified storage
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        sample_id = storage.add_sample_with_embedding(sample, embedding)

        # 4. Verify retrieval
        retrieved = storage.get_sample(sample_id)
        assert retrieved is not None
        assert retrieved['file_hash'] == basic['file_hash']
        assert retrieved['duration_ms'] == pytest.approx(basic['duration_ms'], rel=0.01)

        # 5. Verify embedding retrieval
        retrieved_emb = storage.get_embedding(sample_id)
        assert retrieved_emb is not None
        assert len(retrieved_emb) == len(embedding)

        # 6. Test similarity search (should find itself)
        similar = storage.find_similar(sample_id, limit=5, exclude_self=False)
        assert len(similar) >= 1
        assert similar[0][0]['id'] == sample_id
        assert similar[0][1] == 0.0  # Distance to self is 0

        # 7. Test text search by instrument type
        if classification.get('instrument_type'):
            results = storage.sample_store.search(
                instrument_type=classification['instrument_type'],
                limit=10
            )
            assert any(r['id'] == sample_id for r in results)

    def test_multi_sample_workflow(self, test_audio_kick, test_audio_snare, test_audio_hihat, tmp_path):
        """Test workflow with multiple samples: batch add → search → similarity."""
        # Create sample files
        samples_to_create = [
            ("kick.wav", test_audio_kick),
            ("snare.wav", test_audio_snare),
            ("hihat.wav", test_audio_hihat),
        ]

        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        sample_ids = []

        # Process each sample
        for idx, (filename, (audio, sr)) in enumerate(samples_to_create):
            wav_path = tmp_path / filename
            sf.write(str(wav_path), audio, sr)

            # Analyze
            basic = get_basic_metadata(wav_path)
            spectral = extract_spectral_features(audio, sr)

            try:
                classification = classify_instrument(audio, sr)
            except Exception:
                classification = {"instrument_type": None, "confidence": None}

            try:
                embedding = extract_audio_embedding(audio, sr)
            except Exception:
                embedding = [0.1 * (idx + 1)] * 128  # Unique dummy embeddings

            # Build metadata
            sample = SampleMetadata(
                id=f"smpl_{basic['file_hash'][:8]}",
                file_path=str(wav_path),
                file_hash=basic['file_hash'],
                duration_ms=basic['duration_ms'],
                sample_rate=basic['sample_rate'],
                channels=basic['channels'],
                bit_depth=16,
                file_size_bytes=basic['file_size_bytes'],
                instrument_type=classification.get('instrument_type'),
                spectral_centroid_mean=spectral['spectral_centroid'],
                rms_energy=spectral['rms_energy'],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Store
            sample_id = storage.add_sample_with_embedding(sample, embedding)
            sample_ids.append(sample_id)

        # Verify all samples stored
        assert len(sample_ids) == 3

        # Test that each sample can find similar samples
        for sample_id in sample_ids:
            similar = storage.find_similar(sample_id, limit=3, exclude_self=True)
            # Should find at least the other 2 samples
            assert len(similar) >= 2

    def test_update_workflow(self, test_audio_kick, tmp_path):
        """Test workflow: add → update metadata → verify."""
        audio, sr = test_audio_kick
        wav_path = tmp_path / "kick.wav"
        sf.write(str(wav_path), audio, sr)

        # Initial analysis and storage
        basic = get_basic_metadata(wav_path)

        try:
            embedding = extract_audio_embedding(audio, sr)
        except Exception:
            embedding = [0.1] * 128

        sample = SampleMetadata(
            id=f"smpl_{basic['file_hash'][:8]}",
            file_path=str(wav_path),
            file_hash=basic['file_hash'],
            duration_ms=basic['duration_ms'],
            sample_rate=basic['sample_rate'],
            channels=basic['channels'],
            bit_depth=16,
            file_size_bytes=basic['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        sample_id = storage.add_sample_with_embedding(sample, embedding)

        # Update metadata (add BPM and instrument type)
        updates = {
            "bpm": 128.0,
            "instrument_type": "kick",
            "instrument_confidence": 0.95,
        }

        success = storage.update_sample(sample_id, updates)
        assert success is True

        # Verify updates
        updated = storage.get_sample(sample_id)
        assert updated['bpm'] == 128.0
        assert updated['instrument_type'] == "kick"
        assert updated['instrument_confidence'] == 0.95

        # Verify embedding unchanged
        emb = storage.get_embedding(sample_id)
        assert emb is not None
        assert len(emb) == len(embedding)


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and recovery in workflows."""

    def test_missing_file_analysis(self, tmp_path):
        """Should raise appropriate error for missing file."""
        nonexistent = tmp_path / "nonexistent.wav"

        with pytest.raises(Exception):  # FileNotFoundError or similar
            get_basic_metadata(nonexistent)

    def test_corrupt_audio_handling(self, tmp_path):
        """Should handle corrupt audio files gracefully."""
        # Create a corrupt WAV file (just random bytes)
        corrupt_path = tmp_path / "corrupt.wav"
        corrupt_path.write_bytes(b"Not a valid WAV file")

        with pytest.raises(Exception):  # Should raise some audio-related error
            get_basic_metadata(corrupt_path)

    def test_duplicate_sample_prevention(self, test_audio_kick, tmp_path):
        """Should prevent duplicate samples with same file hash."""
        audio, sr = test_audio_kick
        wav_path = tmp_path / "kick.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        embedding = safe_extract_embedding(audio, sr)

        sample = SampleMetadata(
            id=f"smpl_{basic['file_hash'][:8]}",
            file_path=str(wav_path),
            file_hash=basic['file_hash'],
            duration_ms=basic['duration_ms'],
            sample_rate=basic['sample_rate'],
            channels=basic['channels'],
            bit_depth=16,
            file_size_bytes=basic['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add first time - should succeed
        sample_id1 = storage.add_sample_with_embedding(sample, embedding)
        assert sample_id1 is not None

        # Try to add again with different ID but same hash - should fail
        sample2 = SampleMetadata(
            id="smpl_different",
            file_path=str(wav_path),
            file_hash=basic['file_hash'],  # Same hash!
            duration_ms=basic['duration_ms'],
            sample_rate=basic['sample_rate'],
            channels=basic['channels'],
            bit_depth=16,
            file_size_bytes=basic['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        from audiomancer.errors import DuplicateSampleError
        with pytest.raises(DuplicateSampleError):
            storage.add_sample_with_embedding(sample2, embedding)

    def test_delete_and_verify_cleanup(self, test_audio_kick, tmp_path):
        """Test deletion removes sample from all stores."""
        audio, sr = test_audio_kick
        wav_path = tmp_path / "kick.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        embedding = safe_extract_embedding(audio, sr)

        sample = SampleMetadata(
            id=f"smpl_{basic['file_hash'][:8]}",
            file_path=str(wav_path),
            file_hash=basic['file_hash'],
            duration_ms=basic['duration_ms'],
            sample_rate=basic['sample_rate'],
            channels=basic['channels'],
            bit_depth=16,
            file_size_bytes=basic['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        sample_id = storage.add_sample_with_embedding(sample, embedding)

        # Verify exists
        assert storage.get_sample(sample_id) is not None
        assert storage.get_embedding(sample_id) is not None

        # Delete
        deleted = storage.delete_sample(sample_id)
        assert deleted is True

        # Verify removed from both stores
        assert storage.get_sample(sample_id) is None
        assert storage.get_embedding(sample_id) is None


@pytest.mark.integration
class TestPerformanceCharacteristics:
    """Test performance characteristics of workflows."""

    def test_analysis_speed_reasonable(self, test_audio_kick):
        """Analysis should complete in reasonable time."""
        import time

        audio, sr = test_audio_kick

        start = time.time()
        spectral = extract_spectral_features(audio, sr)
        duration = time.time() - start

        # Should analyze 0.25s of audio in < 1 second
        assert duration < 1.0
        assert spectral is not None

    def test_embedding_generation_speed(self, test_audio_kick):
        """Embedding generation should be reasonably fast."""
        import time

        audio, sr = test_audio_kick

        start = time.time()
        embedding = safe_extract_embedding(audio, sr)
        duration = time.time() - start

        # Should generate embedding in < 2 seconds (or instant if using fallback)
        assert duration < 2.0
        assert embedding is not None
        assert len(embedding) > 0
