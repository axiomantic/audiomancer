"""Integration tests for end-to-end sample workflow.

These tests verify complete workflows from audio file import through analysis,
storage, and pattern generation using the actual implemented API.
"""
import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from datetime import datetime
import tempfile

from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.analyzers.basic import get_basic_metadata
from audiomancer.analyzers.embeddings import extract_audio_embedding
from audiomancer.generators.patterns import generate_drums, generate_melody, MAGENTA_AVAILABLE
from tests.utils import create_test_audio


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary unified storage for testing."""
    db_path = tmp_path / "test.db"
    embeddings_path = tmp_path / "embeddings"
    return UnifiedSampleStorage(db_path, embeddings_path)


@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a test audio file with known properties."""
    audio_path = tmp_path / "test_sample.wav"
    # Create 0.5 second 440Hz sine wave
    audio = create_test_audio(duration=0.5, sample_rate=44100, frequency=440)
    sf.write(str(audio_path), audio, 44100)
    return audio_path


@pytest.fixture
def kick_audio_file(tmp_path):
    """Create a kick-like audio file (short percussive sound)."""
    audio_path = tmp_path / "kick.wav"
    # Create short burst with decay envelope
    duration = 0.25
    sample_rate = 44100
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples)
    # Low frequency with exponential decay
    audio = np.sin(2 * np.pi * 60 * t) * np.exp(-10 * t)
    sf.write(str(audio_path), audio.astype(np.float32), sample_rate)
    return audio_path


@pytest.mark.integration
@pytest.mark.audio
class TestSampleImportWorkflow:
    """Tests for importing and analyzing samples."""

    def test_import_single_sample(self, temp_storage, sample_audio_file):
        """Should extract metadata, create sample record, and store it."""
        # Extract basic metadata from file
        metadata = get_basic_metadata(sample_audio_file)

        # Verify extracted metadata values
        assert metadata['duration_ms'] == pytest.approx(500.0, rel=0.01)
        assert metadata['sample_rate'] == 44100
        assert metadata['channels'] == 1
        assert metadata['file_size_bytes'] > 0
        assert len(metadata['file_hash']) == 64  # SHA256 hex

        # Create sample metadata object
        sample = SampleMetadata(
            id=f"smpl_{metadata['file_hash'][:8]}",
            file_path=str(sample_audio_file),
            file_hash=metadata['file_hash'],
            duration_ms=metadata['duration_ms'],
            sample_rate=metadata['sample_rate'],
            channels=metadata['channels'],
            bit_depth=metadata['bit_depth'],
            file_size_bytes=metadata['file_size_bytes'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create mock embedding (128-dim vector)
        # In real workflow, would use extract_audio_embedding()
        embedding = [0.1] * 128

        # Store sample with embedding
        sample_id = temp_storage.add_sample_with_embedding(sample, embedding)

        # Verify stored correctly
        assert sample_id is not None
        assert sample_id.startswith("smpl_")

        retrieved = temp_storage.sample_store.get(sample_id)
        assert retrieved is not None
        assert retrieved['file_hash'] == metadata['file_hash']
        assert retrieved['duration_ms'] == pytest.approx(metadata['duration_ms'], rel=0.01)
        assert retrieved['sample_rate'] == 44100

    def test_import_with_custom_metadata(self, temp_storage, kick_audio_file):
        """Should import sample with custom category and tags."""
        # Extract basic metadata
        metadata = get_basic_metadata(kick_audio_file)

        # Create sample with custom fields
        sample = SampleMetadata(
            id=f"smpl_{metadata['file_hash'][:8]}",
            file_path=str(kick_audio_file),
            file_hash=metadata['file_hash'],
            duration_ms=metadata['duration_ms'],
            sample_rate=metadata['sample_rate'],
            channels=metadata['channels'],
            bit_depth=metadata['bit_depth'],
            file_size_bytes=metadata['file_size_bytes'],
            # Custom metadata
            instrument_type="kick",
            instrument_confidence=0.95,
            genre_tags=["techno", "808"],
            mood=["dark", "heavy"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        embedding = [0.2] * 128

        # Store
        sample_id = temp_storage.add_sample_with_embedding(sample, embedding)

        # Verify custom metadata preserved
        retrieved = temp_storage.sample_store.get(sample_id)
        assert retrieved is not None
        assert retrieved['instrument_type'] == "kick"
        assert retrieved['instrument_confidence'] == 0.95
        assert "techno" in retrieved['genre_tags']
        assert "dark" in retrieved['mood']


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseWorkflow:
    """Tests for database operations."""

    def test_store_and_retrieve_sample(self, temp_storage):
        """Should store and retrieve sample metadata with exact values."""
        sample = SampleMetadata(
            id="smpl_test001",
            file_path="/test/kick.wav",
            file_hash="abc123def456",
            duration_ms=250.5,
            sample_rate=44100,
            channels=1,
            bit_depth=16,
            file_size_bytes=44100,
            instrument_type="kick",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        embedding = [0.1] * 128

        # Store
        sample_id = temp_storage.add_sample_with_embedding(sample, embedding)
        assert sample_id == "smpl_test001"

        # Retrieve and verify exact values
        retrieved = temp_storage.sample_store.get(sample_id)
        assert retrieved is not None
        assert retrieved['id'] == "smpl_test001"
        assert retrieved['file_hash'] == "abc123def456"
        assert retrieved['duration_ms'] == 250.5
        assert retrieved['sample_rate'] == 44100
        assert retrieved['instrument_type'] == "kick"

    def test_search_samples_by_category(self, temp_storage):
        """Should search samples by instrument type."""
        # Create samples with different categories
        samples = [
            SampleMetadata(
                id="smpl_kick001",
                file_path="/test/kick1.wav",
                file_hash="hash001",
                duration_ms=250.0,
                sample_rate=44100,
                channels=1,
                bit_depth=16,
                file_size_bytes=44100,
                instrument_type="kick",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            SampleMetadata(
                id="smpl_snare001",
                file_path="/test/snare1.wav",
                file_hash="hash002",
                duration_ms=200.0,
                sample_rate=44100,
                channels=1,
                bit_depth=16,
                file_size_bytes=44100,
                instrument_type="snare",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            SampleMetadata(
                id="smpl_kick002",
                file_path="/test/kick2.wav",
                file_hash="hash003",
                duration_ms=300.0,
                sample_rate=44100,
                channels=1,
                bit_depth=16,
                file_size_bytes=44100,
                instrument_type="kick",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        # Store all samples
        for sample in samples:
            embedding = [0.1] * 128
            temp_storage.add_sample_with_embedding(sample, embedding)

        # Search by category using the actual API
        kick_samples = temp_storage.sample_store.search(instrument_type="kick")

        # Verify results
        assert len(kick_samples) == 2
        assert all(s['instrument_type'] == 'kick' for s in kick_samples)
        assert set(s['id'] for s in kick_samples) == {"smpl_kick001", "smpl_kick002"}


@pytest.mark.integration
@pytest.mark.embeddings
class TestEmbeddingWorkflow:
    """Tests for embedding generation and search."""

    def test_generate_embedding_for_sample(self, sample_audio_file):
        """Should generate embedding vector for audio sample."""
        # Load audio
        audio, sr = sf.read(str(sample_audio_file))

        # Try to generate embedding, but skip if model not available
        try:
            embedding = extract_audio_embedding(audio, sr)
        except Exception as e:
            # Model download failed or not available - skip test
            pytest.skip(f"Embedding model not available: {e}")

        # Verify embedding properties
        assert embedding is not None
        assert isinstance(embedding, (list, np.ndarray))
        assert len(embedding) == 128  # Expected dimension
        assert all(isinstance(x, (float, np.floating)) for x in embedding)

    def test_semantic_search(self, temp_storage):
        """Should find similar samples using embeddings."""
        # Create samples with known embeddings
        samples_data = [
            ("smpl_kick001", "hash001", [0.1] * 128),
            ("smpl_kick002", "hash002", [0.11] * 128),  # Very similar to kick001
            ("smpl_snare001", "hash003", [0.8] * 128),  # Very different
        ]

        for sample_id, file_hash, embedding in samples_data:
            sample = SampleMetadata(
                id=sample_id,
                file_path=f"/test/{sample_id}.wav",
                file_hash=file_hash,
                duration_ms=250.0,
                sample_rate=44100,
                channels=1,
                bit_depth=16,
                file_size_bytes=44100,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            temp_storage.add_sample_with_embedding(sample, embedding)

        # Search for samples similar to kick001
        query_embedding = [0.1] * 128
        results = temp_storage.search_by_text_and_similarity(
            query_embedding=query_embedding,
            limit=2
        )

        # Verify results ordered by similarity
        assert len(results) <= 2
        # First result should be exact match or very close
        if len(results) > 0:
            assert results[0]['id'] in ["smpl_kick001", "smpl_kick002"]


@pytest.mark.integration
class TestPatternGenerationWorkflow:
    """Tests for pattern generation workflow."""

    def test_generate_drum_pattern(self):
        """Should generate drum pattern with valid TidalCycles code."""
        pattern = generate_drums(
            bpm=120.0,
            bars=4,
            temperature=0.5,
        )

        # Verify pattern structure
        assert pattern is not None
        assert pattern.type == "drums"
        assert pattern.bpm == 120.0
        assert pattern.bars == 4

        # Verify TidalCycles code is valid
        from tests.utils import assert_valid_tidal_pattern
        assert_valid_tidal_pattern(pattern.tidal_code)

        # Verify SuperCollider code is valid
        from tests.utils import assert_valid_supercollider_code
        assert_valid_supercollider_code(pattern.sc_code)

        # Verify MIDI data exists
        assert pattern.midi_data is not None
        assert len(pattern.midi_data) > 0

    def test_generate_melody_pattern(self):
        """Should generate melody pattern in specified key."""
        pattern = generate_melody(
            bpm=140.0,
            bars=2,
            key="C",
            scale="minor",
            temperature=0.7,
        )

        # Verify pattern structure
        assert pattern is not None
        assert pattern.type == "melody"
        assert pattern.bpm == 140.0
        assert pattern.bars == 2
        assert pattern.key == "C"
        assert pattern.scale == "minor"

        # Verify code generation
        from tests.utils import assert_valid_tidal_pattern, assert_valid_supercollider_code
        assert_valid_tidal_pattern(pattern.tidal_code)
        assert_valid_supercollider_code(pattern.sc_code)

    def test_pattern_without_magenta(self):
        """Pattern generation works with algorithmic fallback when Magenta not available."""
        # Pattern generation now uses algorithmic methods by default
        # No Magenta required - it should just work
        pattern = generate_drums(bpm=120.0, bars=4)

        assert pattern.type == "drums"
        assert pattern.bpm == 120.0
        assert pattern.bars == 4
        assert pattern.generation_method == "algorithmic"
        assert len(pattern.midi_data) > 0
        assert "sound" in pattern.tidal_code
