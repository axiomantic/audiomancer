"""Integration tests for end-to-end sample workflow."""
import pytest
from pathlib import Path


@pytest.mark.integration
@pytest.mark.audio
class TestSampleImportWorkflow:
    """Tests for importing and analyzing samples."""

    @pytest.mark.skip(reason="Requires implementation of SampleImporter")
    def test_import_single_sample(self, temp_dir, sample_audio_data, mock_config):
        """Should import a single sample file."""
        from audiomancer.importers import SampleImporter

        # Create test audio file
        audio_path = temp_dir / "test.wav"
        # TODO: Save sample_audio_data to WAV file

        importer = SampleImporter(mock_config)
        result = importer.import_sample(audio_path)

        assert result["id"] is not None
        assert result["semantic_id"] is not None
        assert result["duration_ms"] > 0

    @pytest.mark.skip(reason="Requires implementation of SampleImporter")
    def test_import_with_metadata(self, temp_dir, mock_config):
        """Should import sample with custom metadata."""
        from audiomancer.importers import SampleImporter

        audio_path = temp_dir / "kick.wav"
        # TODO: Create test audio file

        importer = SampleImporter(mock_config)
        result = importer.import_sample(
            audio_path,
            metadata={
                "category": "bd",
                "source_pack": "Test Pack",
                "tags": ["kick", "808"],
            }
        )

        assert result["category"] == "bd"
        assert result["source_pack"] == "Test Pack"
        assert "kick" in result["tags"]


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseWorkflow:
    """Tests for database operations."""

    @pytest.mark.skip(reason="Requires implementation of Database")
    def test_store_and_retrieve_sample(self, mock_config, mock_sample_metadata):
        """Should store and retrieve sample metadata."""
        from audiomancer.storage import Database

        db = Database(mock_config)
        db.initialize()

        # Store
        sample_id = db.store_sample(mock_sample_metadata)
        assert sample_id is not None

        # Retrieve
        retrieved = db.get_sample(sample_id)
        assert retrieved["id"] == sample_id
        assert retrieved["semantic_id"] == mock_sample_metadata["semantic_id"]

    @pytest.mark.skip(reason="Requires implementation of Database")
    def test_search_samples_by_category(self, mock_config):
        """Should search samples by category."""
        from audiomancer.storage import Database

        db = Database(mock_config)
        db.initialize()

        # Store multiple samples
        db.store_sample({"semantic_id": "kick_1", "category": "bd"})
        db.store_sample({"semantic_id": "snare_1", "category": "sn"})
        db.store_sample({"semantic_id": "kick_2", "category": "bd"})

        # Search
        results = db.search_samples(category="bd")
        assert len(results) == 2
        assert all(s["category"] == "bd" for s in results)


@pytest.mark.integration
@pytest.mark.embeddings
class TestEmbeddingWorkflow:
    """Tests for embedding generation and search."""

    @pytest.mark.skip(reason="Requires implementation of EmbeddingEngine")
    def test_generate_embedding_for_sample(self, mock_config, sample_audio_data):
        """Should generate embedding for audio sample."""
        from audiomancer.embeddings import EmbeddingEngine

        engine = EmbeddingEngine(mock_config)
        audio = sample_audio_data["sine_440"]
        embedding = engine.generate_embedding(audio)

        assert embedding is not None
        assert len(embedding.shape) == 1  # 1D vector
        assert embedding.shape[0] > 0

    @pytest.mark.skip(reason="Requires implementation of EmbeddingEngine")
    def test_semantic_search(self, mock_config):
        """Should find similar samples using embeddings."""
        from audiomancer.embeddings import EmbeddingEngine

        engine = EmbeddingEngine(mock_config)

        # Index some samples
        engine.index_sample("kick_1", embedding=[0.1, 0.2, 0.3])
        engine.index_sample("kick_2", embedding=[0.11, 0.21, 0.31])
        engine.index_sample("snare_1", embedding=[0.8, 0.9, 0.7])

        # Search
        results = engine.search_similar(
            query_embedding=[0.1, 0.2, 0.3],
            top_k=2
        )

        assert len(results) == 2
        assert results[0]["sample_id"] == "kick_1"
        assert results[1]["sample_id"] == "kick_2"


@pytest.mark.integration
class TestPatternGenerationWorkflow:
    """Tests for pattern generation workflow."""

    @pytest.mark.skip(reason="Requires implementation of PatternGenerator")
    def test_generate_tidal_pattern_from_samples(self, mock_config):
        """Should generate TidalCycles pattern from sample list."""
        from audiomancer.generators import PatternGenerator

        generator = PatternGenerator(mock_config)
        samples = ["kick_808", "snare_909", "hat_closed"]

        pattern = generator.generate_tidal_pattern(
            samples=samples,
            bpm=120.0,
            bars=4,
        )

        from tests.utils import assert_valid_tidal_pattern
        assert_valid_tidal_pattern(pattern)

    @pytest.mark.skip(reason="Requires implementation of PatternGenerator")
    def test_generate_supercollider_pbind(self, mock_config):
        """Should generate SuperCollider Pbind from sample list."""
        from audiomancer.generators import PatternGenerator

        generator = PatternGenerator(mock_config)
        samples = ["kick_808", "snare_909"]

        pbind = generator.generate_supercollider_pbind(
            samples=samples,
            bpm=140.0,
        )

        from tests.utils import assert_valid_supercollider_code
        assert_valid_supercollider_code(pbind)
