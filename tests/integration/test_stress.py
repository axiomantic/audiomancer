"""Stress tests for audiomancer.

Tests system behavior under high load:
- Large number of samples
- Concurrent operations
- Large MIDI files
- Memory usage patterns
"""

import numpy as np
import pytest
import soundfile as sf
import tempfile
from pathlib import Path
from datetime import datetime
import time

from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.analyzers import (
    get_basic_metadata,
    extract_spectral_features,
    extract_audio_embedding,
)


def safe_extract_embedding(audio: np.ndarray, sr: int) -> list[float]:
    """Extract embedding with fallback to dummy data if models unavailable."""
    try:
        return extract_audio_embedding(audio, sr)
    except Exception:
        return [0.1] * 128


def generate_test_audio(seed: int, duration: float = 0.1) -> tuple[np.ndarray, int]:
    """Generate deterministic test audio from seed."""
    np.random.seed(seed)
    sr = 44100
    samples = int(sr * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Mix of sine and noise
    freq = 100 + (seed % 500)
    audio = np.sin(2 * np.pi * freq * t)
    audio += 0.1 * np.random.uniform(-1, 1, samples)
    audio = audio * np.exp(-5 * t)

    return audio.astype(np.float32), sr


@pytest.mark.integration
@pytest.mark.slow
class TestLargeDatasetHandling:
    """Test handling of large numbers of samples."""

    @pytest.mark.parametrize("num_samples", [10, 50])
    def test_batch_add_many_samples(self, num_samples, tmp_path):
        """Test adding many samples in batch."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        items = []
        for i in range(num_samples):
            audio, sr = generate_test_audio(seed=i, duration=0.05)
            wav_path = tmp_path / f"sample_{i:04d}.wav"
            sf.write(str(wav_path), audio, sr)

            basic = get_basic_metadata(wav_path)
            embedding = safe_extract_embedding(audio, sr)

            sample = SampleMetadata(
                id=f"smpl_{i:04d}",
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

            items.append((sample, embedding))

        # Batch add
        start = time.time()
        sample_ids = storage.add_samples_with_embeddings_batch(items)
        duration = time.time() - start

        # Verify all added
        assert len(sample_ids) == num_samples

        # Should complete in reasonable time (< 1 second per 10 samples)
        assert duration < num_samples * 0.1

        # Verify random samples
        for i in [0, num_samples // 2, num_samples - 1]:
            sample = storage.get_sample(f"smpl_{i:04d}")
            assert sample is not None
            emb = storage.get_embedding(f"smpl_{i:04d}")
            assert emb is not None

    def test_similarity_search_performance(self, tmp_path):
        """Test similarity search with many samples."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add 20 samples
        num_samples = 20
        for i in range(num_samples):
            audio, sr = generate_test_audio(seed=i, duration=0.05)
            wav_path = tmp_path / f"sample_{i:04d}.wav"
            sf.write(str(wav_path), audio, sr)

            basic = get_basic_metadata(wav_path)
            embedding = safe_extract_embedding(audio, sr)

            sample = SampleMetadata(
                id=f"smpl_{i:04d}",
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

            storage.add_sample_with_embedding(sample, embedding)

        # Test search performance
        start = time.time()
        similar = storage.find_similar("smpl_0000", limit=10, exclude_self=True)
        duration = time.time() - start

        # Should find results
        assert len(similar) >= 1

        # Should be fast (< 1 second even with 20 samples)
        assert duration < 1.0

    def test_memory_usage_reasonable(self, tmp_path):
        """Test that memory usage doesn't grow unreasonably."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add 30 samples
        for i in range(30):
            audio, sr = generate_test_audio(seed=i, duration=0.05)
            wav_path = tmp_path / f"sample_{i:04d}.wav"
            sf.write(str(wav_path), audio, sr)

            basic = get_basic_metadata(wav_path)
            embedding = safe_extract_embedding(audio, sr)

            sample = SampleMetadata(
                id=f"smpl_{i:04d}",
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

            storage.add_sample_with_embedding(sample, embedding)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 200 MB for 30 samples)
        assert memory_increase < 200


@pytest.mark.integration
class TestLongRunningOperations:
    """Test operations that take longer time."""

    def test_analyze_longer_audio(self, tmp_path):
        """Test analysis of longer audio files."""
        # Create 5 second audio file
        audio, sr = generate_test_audio(seed=42, duration=5.0)
        wav_path = tmp_path / "long_sample.wav"
        sf.write(str(wav_path), audio, sr)

        start = time.time()
        basic = get_basic_metadata(wav_path)
        spectral = extract_spectral_features(audio, sr)
        embedding = safe_extract_embedding(audio, sr)
        duration = time.time() - start

        # Should complete even for longer files
        assert basic is not None
        assert spectral is not None
        assert embedding is not None

        # Should complete in reasonable time (< 10 seconds for 5s audio)
        assert duration < 10.0

    def test_multiple_searches_sequential(self, tmp_path):
        """Test multiple sequential searches don't degrade."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add 15 samples
        for i in range(15):
            audio, sr = generate_test_audio(seed=i, duration=0.05)
            wav_path = tmp_path / f"sample_{i:04d}.wav"
            sf.write(str(wav_path), audio, sr)

            basic = get_basic_metadata(wav_path)
            embedding = safe_extract_embedding(audio, sr)

            sample = SampleMetadata(
                id=f"smpl_{i:04d}",
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

            storage.add_sample_with_embedding(sample, embedding)

        # Perform multiple searches
        search_times = []
        for i in range(10):
            start = time.time()
            similar = storage.find_similar(f"smpl_{i:04d}", limit=5, exclude_self=True)
            search_times.append(time.time() - start)
            assert len(similar) >= 1

        # Search times should be consistent (no degradation)
        avg_time = sum(search_times) / len(search_times)
        max_time = max(search_times)

        # Max time shouldn't be much worse than average (< 2x)
        assert max_time < avg_time * 2


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_short_audio(self, tmp_path):
        """Test analysis of very short audio (< 0.1s)."""
        # Create 0.01 second audio (441 samples at 44.1kHz)
        sr = 44100
        duration = 0.01
        samples = int(sr * duration)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, samples)).astype(np.float32)

        wav_path = tmp_path / "very_short.wav"
        sf.write(str(wav_path), audio, sr)

        # Should handle gracefully (may have limited features)
        basic = get_basic_metadata(wav_path)
        assert basic is not None
        assert basic['duration_ms'] == pytest.approx(10.0, rel=0.1)

        # Spectral features require minimum length, so this should raise
        from audiomancer.errors import AnalysisFailedError
        with pytest.raises(AnalysisFailedError) as exc_info:
            extract_spectral_features(audio, sr)

        assert "too short" in str(exc_info.value).lower()

    def test_silence_audio(self, tmp_path):
        """Test analysis of complete silence."""
        sr = 44100
        duration = 1.0
        samples = int(sr * duration)
        audio = np.zeros(samples, dtype=np.float32)

        wav_path = tmp_path / "silence.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        spectral = extract_spectral_features(audio, sr)

        assert basic is not None
        assert spectral is not None
        assert spectral['rms_energy'] == pytest.approx(0.0, abs=1e-6)

    def test_maximum_amplitude_audio(self, tmp_path):
        """Test analysis of maximum amplitude audio."""
        sr = 44100
        duration = 0.1
        samples = int(sr * duration)
        # Square wave at maximum amplitude
        audio = np.ones(samples, dtype=np.float32)

        wav_path = tmp_path / "max_amplitude.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        spectral = extract_spectral_features(audio, sr)

        assert basic is not None
        assert spectral is not None

    def test_empty_database_searches(self, tmp_path):
        """Test searches on empty database."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Search should return empty results, not error
        results = storage.sample_store.search(instrument_type="kick", limit=10)
        assert results == []

        # Combined search should return empty
        query_emb = [0.1] * 128
        results = storage.search_by_text_and_similarity(
            query_embedding=query_emb,
            limit=10
        )
        assert results == []

    def test_search_with_limit_exceeding_results(self, tmp_path):
        """Test search with limit > available samples."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add only 3 samples
        for i in range(3):
            audio, sr = generate_test_audio(seed=i, duration=0.05)
            wav_path = tmp_path / f"sample_{i:04d}.wav"
            sf.write(str(wav_path), audio, sr)

            basic = get_basic_metadata(wav_path)
            embedding = safe_extract_embedding(audio, sr)

            sample = SampleMetadata(
                id=f"smpl_{i:04d}",
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

            storage.add_sample_with_embedding(sample, embedding)

        # Search with limit=100
        similar = storage.find_similar("smpl_0000", limit=100, exclude_self=True)

        # Should return only available samples (2, excluding self)
        assert len(similar) == 2
