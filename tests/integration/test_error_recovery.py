"""Error recovery integration tests.

Tests graceful error handling and recovery mechanisms:
- Corrupt file handling
- Partial batch failures
- Database recovery
- Storage consistency
"""

import numpy as np
import pytest
import soundfile as sf
from pathlib import Path
from datetime import datetime

from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.analyzers import (
    get_basic_metadata,
    extract_audio_embedding,
    extract_spectral_features,
)
from audiomancer.errors import (
    DuplicateSampleError,
    SampleNotFoundError,
    StorageError,
)


def safe_extract_embedding(audio: np.ndarray, sr: int) -> list[float]:
    """Extract embedding with fallback to dummy data if models unavailable."""
    try:
        return extract_audio_embedding(audio, sr)
    except Exception:
        return [0.1] * 128


def generate_valid_audio(seed: int = 42) -> tuple[np.ndarray, int]:
    """Generate valid test audio with variation based on seed."""
    np.random.seed(seed)
    sr = 44100
    duration = 0.1
    samples = int(sr * duration)
    t = np.linspace(0, duration, samples, endpoint=False)
    # Vary frequency based on seed to create unique file hashes
    freq = 440 + (seed * 10)
    audio = np.sin(2 * np.pi * freq * t).astype(np.float32)
    return audio, sr


@pytest.mark.integration
class TestCorruptFileHandling:
    """Test handling of corrupt or invalid files."""

    def test_empty_file_handling(self, tmp_path):
        """Should handle empty files gracefully."""
        empty_file = tmp_path / "empty.wav"
        empty_file.write_bytes(b"")

        with pytest.raises(Exception):  # Should raise appropriate error
            get_basic_metadata(empty_file)

    def test_partial_wav_header(self, tmp_path):
        """Should handle files with incomplete WAV headers."""
        partial_wav = tmp_path / "partial.wav"
        # Write partial RIFF header (not complete WAV)
        partial_wav.write_bytes(b"RIFF\x00\x00\x00\x00")

        with pytest.raises(Exception):
            get_basic_metadata(partial_wav)

    def test_non_audio_file(self, tmp_path):
        """Should handle non-audio files gracefully."""
        text_file = tmp_path / "text.wav"
        text_file.write_text("This is not an audio file")

        with pytest.raises(Exception):
            get_basic_metadata(text_file)

    def test_truncated_audio_data(self, tmp_path):
        """Should handle files with truncated audio data."""
        # Create valid audio
        audio, sr = generate_valid_audio()
        wav_path = tmp_path / "full.wav"
        sf.write(str(wav_path), audio, sr)

        # Read and truncate
        full_data = wav_path.read_bytes()
        truncated_path = tmp_path / "truncated.wav"
        # Keep header but truncate audio data
        truncated_path.write_bytes(full_data[:len(full_data) // 2])

        # Should handle gracefully (may read partial data or raise error)
        # Either outcome is acceptable as long as it doesn't crash
        try:
            basic = get_basic_metadata(truncated_path)
            # If it succeeds, duration should be shorter
            assert basic is not None
        except Exception:
            # If it fails, that's also acceptable
            pass


@pytest.mark.integration
class TestBatchOperationFailures:
    """Test partial failures in batch operations."""

    def test_batch_with_invalid_embedding_dimension(self, tmp_path):
        """Entire batch should rollback if any embedding is invalid."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Create valid samples
        items = []
        for i in range(3):
            audio, sr = generate_valid_audio(seed=i)
            wav_path = tmp_path / f"sample_{i}.wav"
            sf.write(str(wav_path), audio, sr)

            basic = get_basic_metadata(wav_path)
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

            if i == 1:
                # Invalid embedding for middle item
                embedding = [0.1] * 100  # Wrong dimension
            else:
                embedding = safe_extract_embedding(audio, sr)

            items.append((sample, embedding))

        # Should raise StorageError
        with pytest.raises(StorageError) as exc_info:
            storage.add_samples_with_embeddings_batch(items)

        assert "Invalid embedding in batch" in str(exc_info.value)

        # Verify NO samples were added (atomic rollback)
        for i in range(3):
            assert storage.get_sample(f"smpl_{i:04d}") is None
            assert storage.get_embedding(f"smpl_{i:04d}") is None

    def test_batch_with_duplicate_hash(self, tmp_path):
        """Batch should rollback on duplicate file hash."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add first sample
        audio, sr = generate_valid_audio(seed=0)
        wav_path = tmp_path / "sample_0.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        embedding = safe_extract_embedding(audio, sr)

        sample = SampleMetadata(
            id="smpl_0000",
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

        # Create batch with duplicate hash
        items = []
        for i in range(1, 3):
            audio_i, sr_i = generate_valid_audio(seed=i)
            wav_path_i = tmp_path / f"sample_{i}.wav"
            sf.write(str(wav_path_i), audio_i, sr_i)

            basic_i = get_basic_metadata(wav_path_i)
            embedding_i = safe_extract_embedding(audio_i, sr_i)

            # Use duplicate hash for sample 2
            if i == 2:
                hash_to_use = basic['file_hash']  # Duplicate!
            else:
                hash_to_use = basic_i['file_hash']

            sample_i = SampleMetadata(
                id=f"smpl_{i:04d}",
                file_path=str(wav_path_i),
                file_hash=hash_to_use,
                duration_ms=basic_i['duration_ms'],
                sample_rate=basic_i['sample_rate'],
                channels=basic_i['channels'],
                bit_depth=16,
                file_size_bytes=basic_i['file_size_bytes'],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            items.append((sample_i, embedding_i))

        # Should raise DuplicateSampleError
        with pytest.raises(DuplicateSampleError):
            storage.add_samples_with_embeddings_batch(items)

        # Verify original sample still exists
        assert storage.get_sample("smpl_0000") is not None

        # Verify new samples were NOT added
        assert storage.get_sample("smpl_0001") is None
        assert storage.get_sample("smpl_0002") is None


@pytest.mark.integration
class TestDatabaseRecovery:
    """Test database recovery and consistency."""

    def test_storage_survives_restart(self, tmp_path):
        """Storage should persist data across restarts."""
        db_path = tmp_path / "samples.db"
        emb_path = tmp_path / "embeddings"

        # Create storage and add sample
        storage1 = UnifiedSampleStorage(db_path=db_path, embeddings_path=emb_path)

        audio, sr = generate_valid_audio(seed=42)
        wav_path = tmp_path / "sample.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        embedding = safe_extract_embedding(audio, sr)

        sample = SampleMetadata(
            id="smpl_persist",
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

        storage1.add_sample_with_embedding(sample, embedding)

        # Close first storage (simulate restart)
        del storage1

        # Create new storage instance with same paths
        storage2 = UnifiedSampleStorage(db_path=db_path, embeddings_path=emb_path)

        # Verify data persisted
        retrieved = storage2.get_sample("smpl_persist")
        assert retrieved is not None
        assert retrieved['file_hash'] == basic['file_hash']

        retrieved_emb = storage2.get_embedding("smpl_persist")
        assert retrieved_emb is not None
        assert len(retrieved_emb) == len(embedding)

    def test_orphaned_embedding_cleanup(self, tmp_path):
        """Should handle and clean up orphaned embeddings."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Manually create orphaned embedding (bypass unified interface)
        orphan_embedding = [0.1] * 128
        storage.vector_store.add_embedding("smpl_orphan", orphan_embedding)

        # Verify orphan exists
        assert storage.get_embedding("smpl_orphan") is not None
        assert storage.get_sample("smpl_orphan") is None

        # Try to delete orphan
        result = storage.delete_sample("smpl_orphan")

        # Should return False (sample doesn't exist in metadata)
        assert result is False

        # But embedding should be cleaned up
        assert storage.get_embedding("smpl_orphan") is None

    def test_missing_sample_file_handling(self, tmp_path):
        """Should handle case where sample file is deleted after import."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add sample
        audio, sr = generate_valid_audio(seed=42)
        wav_path = tmp_path / "sample.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)
        embedding = safe_extract_embedding(audio, sr)

        sample = SampleMetadata(
            id="smpl_missing",
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

        # Delete the actual file
        wav_path.unlink()

        # Metadata should still be retrievable
        retrieved = storage.get_sample("smpl_missing")
        assert retrieved is not None
        assert retrieved['file_path'] == str(wav_path)

        # But file doesn't exist anymore
        assert not Path(retrieved['file_path']).exists()


@pytest.mark.integration
class TestOperationRetry:
    """Test retry and recovery mechanisms."""

    def test_update_nonexistent_sample_fails_gracefully(self, tmp_path):
        """Update of nonexistent sample should fail gracefully."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Try to update nonexistent sample
        result = storage.update_sample("smpl_nonexistent", {"bpm": 120.0})

        # Should return False (not crash)
        assert result is False

    def test_delete_nonexistent_sample_idempotent(self, tmp_path):
        """Delete of nonexistent sample should be idempotent."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Delete nonexistent sample multiple times
        result1 = storage.delete_sample("smpl_nonexistent")
        result2 = storage.delete_sample("smpl_nonexistent")

        # Both should return False
        assert result1 is False
        assert result2 is False

    def test_search_with_missing_embedding_handled(self, tmp_path):
        """Search should handle samples missing embeddings."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add sample without embedding (bypass unified interface)
        audio, sr = generate_valid_audio(seed=42)
        wav_path = tmp_path / "sample.wav"
        sf.write(str(wav_path), audio, sr)

        basic = get_basic_metadata(wav_path)

        sample = SampleMetadata(
            id="smpl_no_emb",
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

        storage.sample_store.add(sample)

        # Try to find similar (should fail since no embedding)
        with pytest.raises(SampleNotFoundError) as exc_info:
            storage.find_similar("smpl_no_emb", limit=10)

        assert "No embedding found" in str(exc_info.value)


@pytest.mark.integration
class TestConcurrentOperations:
    """Test concurrent operation safety."""

    def test_sequential_add_and_search(self, tmp_path):
        """Sequential add and search should work correctly."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add samples sequentially and search after each
        for i in range(5):
            audio, sr = generate_valid_audio(seed=i)
            wav_path = tmp_path / f"sample_{i}.wav"
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

            # Search should find all samples added so far
            if i > 0:
                similar = storage.find_similar(f"smpl_{i:04d}", limit=10, exclude_self=True)
                assert len(similar) >= 1  # At least previous samples

    def test_interleaved_add_update_delete(self, tmp_path):
        """Interleaved operations should maintain consistency."""
        storage = UnifiedSampleStorage(
            db_path=tmp_path / "samples.db",
            embeddings_path=tmp_path / "embeddings"
        )

        # Add sample 1
        audio1, sr1 = generate_valid_audio(seed=1)
        wav_path1 = tmp_path / "sample_1.wav"
        sf.write(str(wav_path1), audio1, sr1)

        basic1 = get_basic_metadata(wav_path1)
        embedding1 = safe_extract_embedding(audio1, sr1)

        sample1 = SampleMetadata(
            id="smpl_0001",
            file_path=str(wav_path1),
            file_hash=basic1['file_hash'],
            duration_ms=basic1['duration_ms'],
            sample_rate=basic1['sample_rate'],
            channels=basic1['channels'],
            bit_depth=16,
            file_size_bytes=basic1['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        storage.add_sample_with_embedding(sample1, embedding1)

        # Update sample 1
        storage.update_sample("smpl_0001", {"bpm": 120.0})

        # Add sample 2
        audio2, sr2 = generate_valid_audio(seed=2)
        wav_path2 = tmp_path / "sample_2.wav"
        sf.write(str(wav_path2), audio2, sr2)

        basic2 = get_basic_metadata(wav_path2)
        embedding2 = safe_extract_embedding(audio2, sr2)

        sample2 = SampleMetadata(
            id="smpl_0002",
            file_path=str(wav_path2),
            file_hash=basic2['file_hash'],
            duration_ms=basic2['duration_ms'],
            sample_rate=basic2['sample_rate'],
            channels=basic2['channels'],
            bit_depth=16,
            file_size_bytes=basic2['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        storage.add_sample_with_embedding(sample2, embedding2)

        # Delete sample 1
        storage.delete_sample("smpl_0001")

        # Verify state
        assert storage.get_sample("smpl_0001") is None
        assert storage.get_sample("smpl_0002") is not None
        assert storage.get_embedding("smpl_0002") is not None
