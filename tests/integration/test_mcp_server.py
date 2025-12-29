"""Integration tests for MCP server.

Tests all MCP tools with realistic data and error scenarios.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.types import TextContent

from audiomancer.server import (
    search_samples,
    find_similar,
    describe_sample,
    analyze_file,
    list_synths,
    get_synth,
    get_stats,
    storage,
    synth_store,
)
from audiomancer.errors import SampleNotFoundError, AnalysisError, AudiomancerError


@pytest.fixture
def mock_storage(monkeypatch):
    """Mock storage with sample data."""
    mock_store = MagicMock()

    # Mock sample data
    sample_data = {
        "id": "smpl_test123",
        "file_path": "/samples/kick.wav",
        "instrument_type": "kick",
        "bpm": 128.0,
        "key": "C",
        "duration_ms": 250.5,
        "sample_rate": 44100,
        "channels": 1,
        "mood": ["dark", "punchy"],
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    mock_store.sample_store.search.return_value = [sample_data]
    mock_store.sample_store.get.return_value = sample_data
    mock_store.get_sample.return_value = sample_data
    mock_store.find_similar.return_value = [
        (sample_data, 0.1),
        (sample_data, 0.2),
    ]

    # Patch the global storage
    monkeypatch.setattr("audiomancer.server.storage", mock_store)

    return mock_store


@pytest.fixture
def mock_synth_store(monkeypatch):
    """Mock synth store with synth data."""
    mock_store = MagicMock()

    synth_data = {
        "id": "synth_test123",
        "name": "tb303",
        "category": "bass",
        "controls": [
            {"name": "freq", "default": 440.0},
            {"name": "resonance", "default": 0.7},
        ],
        "has_gate": True,
        "characteristics": {"has_gate": True, "num_channels": 2},
        "categorization": {"category": "bass"},
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    mock_store.list_all.return_value = [synth_data]
    mock_store.get_by_name.return_value = synth_data
    mock_store.count.return_value = 1

    monkeypatch.setattr("audiomancer.server.synth_store", mock_store)

    return mock_store


class TestSearchSamples:
    """Test search_samples tool."""

    @pytest.mark.asyncio
    async def test_search_basic_query(self, mock_storage):
        """Test basic text search."""
        result = await search_samples(query="kick")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "results" in data
        assert data["count"] == 1
        assert data["results"][0]["instrument_type"] == "kick"
        assert data["query"]["text"] == "kick"

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_storage):
        """Test search with multiple filters."""
        result = await search_samples(
            query="kick",
            instrument_type="kick",
            bpm_min=120.0,
            bpm_max=130.0,
            key="C",
            limit=10
        )

        data = json.loads(result[0].text)
        assert data["query"]["instrument_type"] == "kick"
        assert data["query"]["bpm_range"] == [120.0, 130.0]
        assert data["query"]["key"] == "C"

        # Verify filters were passed to storage
        mock_storage.sample_store.search.assert_called_once_with(
            query="kick",
            instrument_type="kick",
            bpm_min=120.0,
            bpm_max=130.0,
            key="C",
            mood=None,
            limit=10
        )

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_storage):
        """Test search with no results."""
        mock_storage.sample_store.search.return_value = []

        result = await search_samples(query="nonexistent")

        data = json.loads(result[0].text)
        assert data["count"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_storage_not_initialized(self, monkeypatch):
        """Test error when storage not initialized."""
        monkeypatch.setattr("audiomancer.server.storage", None)

        with pytest.raises(AudiomancerError) as exc_info:
            await search_samples(query="kick")

        assert "Storage not initialized" in str(exc_info.value)


class TestFindSimilar:
    """Test find_similar tool."""

    @pytest.mark.asyncio
    async def test_find_similar_basic(self, mock_storage):
        """Test finding similar samples."""
        result = await find_similar(sample_id="smpl_test123", limit=5)

        data = json.loads(result[0].text)
        assert data["query_sample_id"] == "smpl_test123"
        assert data["count"] == 2
        assert len(data["similar_samples"]) == 2
        assert data["similar_samples"][0]["distance"] == 0.1
        assert data["similar_samples"][1]["distance"] == 0.2

    @pytest.mark.asyncio
    async def test_find_similar_sample_not_found(self, mock_storage):
        """Test error when sample not found."""
        mock_storage.find_similar.side_effect = SampleNotFoundError("nonexistent")

        with pytest.raises(SampleNotFoundError) as exc_info:
            await find_similar(sample_id="nonexistent")

        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_similar_custom_limit(self, mock_storage):
        """Test custom limit parameter."""
        await find_similar(sample_id="smpl_test123", limit=3)

        mock_storage.find_similar.assert_called_once_with(
            sample_id="smpl_test123",
            limit=3,
            exclude_self=True
        )


class TestDescribeSample:
    """Test describe_sample tool."""

    @pytest.mark.asyncio
    async def test_describe_sample_found(self, mock_storage):
        """Test describing an existing sample."""
        result = await describe_sample(sample_id="smpl_test123")

        data = json.loads(result[0].text)
        assert data["id"] == "smpl_test123"
        assert data["file_path"] == "/samples/kick.wav"
        assert data["instrument_type"] == "kick"
        assert data["bpm"] == 128.0

    @pytest.mark.asyncio
    async def test_describe_sample_not_found(self, mock_storage):
        """Test error when sample not found."""
        mock_storage.get_sample.return_value = None

        with pytest.raises(SampleNotFoundError) as exc_info:
            await describe_sample(sample_id="nonexistent")

        assert "Sample not found" in str(exc_info.value)


class TestAnalyzeFile:
    """Test analyze_file tool."""

    @pytest.mark.asyncio
    async def test_analyze_file_success(self, mock_storage, tmp_path):
        """Test successful file analysis."""
        # Create a dummy audio file
        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"RIFF" + b"\x00" * 100)

        # Mock all analyzer functions
        with patch("audiomancer.server.get_basic_metadata") as mock_basic, \
             patch("audiomancer.server.extract_spectral_features") as mock_spectral, \
             patch("audiomancer.server.extract_rhythm_features") as mock_rhythm, \
             patch("audiomancer.server.extract_tonal_features") as mock_tonal, \
             patch("audiomancer.server.extract_audio_embedding") as mock_embedding, \
             patch("audiomancer.server.classify_instrument") as mock_classify:

            # Setup mocks
            mock_basic.return_value = MagicMock(
                id="smpl_new123",
                file_hash="abc123",
                duration_ms=250.5,
                sample_rate=44100,
                channels=1,
                bit_depth=16,
                file_size_bytes=44100
            )
            mock_spectral.return_value = MagicMock(
                spectral_centroid=1000.0,
                spectral_bandwidth=500.0,
                spectral_rolloff=2000.0,
                zero_crossing_rate=0.1,
                rms_energy=0.5,
                dynamic_range=60.0
            )
            mock_rhythm.return_value = MagicMock(
                bpm=128.0,
                confidence=0.9,
                is_loop=True
            )
            mock_tonal.return_value = MagicMock(
                key="C",
                key_confidence=0.8,
                tuning_frequency=440.0,
                pitch_salience=0.7
            )
            mock_embedding.return_value = MagicMock(
                embedding=[0.1] * 128
            )
            mock_classify.return_value = MagicMock(
                primary_class="kick",
                confidence=0.95
            )

            mock_storage.add_sample_with_embedding.return_value = "smpl_new123"

            result = await analyze_file(path=str(test_file))

            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["sample_id"] == "smpl_new123"
            assert data["analysis"]["instrument_type"] == "kick"
            assert data["analysis"]["bpm"] == 128.0

    @pytest.mark.asyncio
    async def test_analyze_file_not_found(self, mock_storage):
        """Test error when file doesn't exist."""
        with pytest.raises(AnalysisError) as exc_info:
            await analyze_file(path="/nonexistent/file.wav")

        assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_file_analysis_fails(self, mock_storage, tmp_path):
        """Test error when analysis fails."""
        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"invalid data")

        with patch("audiomancer.server.get_basic_metadata") as mock_basic:
            mock_basic.side_effect = Exception("Analysis failed")

            with pytest.raises(AnalysisError) as exc_info:
                await analyze_file(path=str(test_file))

            assert "Analysis failed" in str(exc_info.value)


class TestListSynths:
    """Test list_synths tool."""

    @pytest.mark.asyncio
    async def test_list_synths_all(self, mock_synth_store):
        """Test listing all synths."""
        result = await list_synths()

        data = json.loads(result[0].text)
        assert data["count"] == 1
        assert len(data["synths"]) == 1
        assert data["synths"][0]["name"] == "tb303"
        assert data["synths"][0]["category"] == "bass"

    @pytest.mark.asyncio
    async def test_list_synths_filtered(self, mock_synth_store):
        """Test listing synths with category filter."""
        result = await list_synths(category="bass")

        data = json.loads(result[0].text)
        assert data["filter"]["category"] == "bass"
        assert all(s["category"] == "bass" for s in data["synths"])

    @pytest.mark.asyncio
    async def test_list_synths_custom_limit(self, mock_synth_store):
        """Test custom limit parameter."""
        await list_synths(limit=10)

        mock_synth_store.list_all.assert_called_once_with(limit=10)


class TestGetSynth:
    """Test get_synth tool."""

    @pytest.mark.asyncio
    async def test_get_synth_found(self, mock_synth_store):
        """Test getting an existing synth."""
        result = await get_synth(name="tb303")

        data = json.loads(result[0].text)
        assert data["name"] == "tb303"
        assert len(data["controls"]) == 2

    @pytest.mark.asyncio
    async def test_get_synth_not_found(self, mock_synth_store):
        """Test error when synth not found."""
        mock_synth_store.get_by_name.return_value = None

        with pytest.raises(AudiomancerError) as exc_info:
            await get_synth(name="nonexistent")

        assert "SynthDef not found" in str(exc_info.value)


class TestGetStats:
    """Test get_stats tool."""

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_storage, mock_synth_store):
        """Test getting library statistics."""
        mock_storage.sample_store.count.return_value = 100
        mock_storage.sample_store.get_instrument_distribution.return_value = {
            "kick": 30,
            "snare": 25,
            "hat": 45
        }
        mock_synth_store.count.return_value = 10

        result = await get_stats()

        data = json.loads(result[0].text)
        assert data["samples"]["total"] == 100
        assert data["samples"]["by_instrument"]["kick"] == 30
        assert data["synths"]["total"] == 10


class TestErrorHandling:
    """Test error handling and serialization."""

    @pytest.mark.asyncio
    async def test_audiomancer_error_serialization(self, monkeypatch):
        """Test that AudiomancerError is properly serialized to JSON."""
        monkeypatch.setattr("audiomancer.server.storage", None)

        with pytest.raises(AudiomancerError) as exc_info:
            await search_samples(query="test")

        error_dict = exc_info.value.to_dict()
        assert error_dict["type"] == "AudiomancerError"
        assert "Storage not initialized" in error_dict["message"]
        assert isinstance(error_dict["details"], dict)

    @pytest.mark.asyncio
    async def test_sample_not_found_error_details(self, mock_storage):
        """Test SampleNotFoundError includes proper details."""
        mock_storage.find_similar.side_effect = SampleNotFoundError(
            "missing123",
            details={"reason": "No embedding"}
        )

        with pytest.raises(SampleNotFoundError) as exc_info:
            await find_similar(sample_id="missing123")

        error_dict = exc_info.value.to_dict()
        assert error_dict["details"]["sample_id"] == "missing123"
        # Reason gets overridden by find_similar, so check it exists
        assert "reason" in error_dict["details"]
