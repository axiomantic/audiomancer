"""Tests for LibraryManager class."""

import pytest
from pathlib import Path

from audiomancer.library.manager import LibraryManager
from audiomancer.library.schema import PackInfo, PackStatus, SampleInfo
from audiomancer.errors import PackNotFoundError, SourceNotAvailableError


@pytest.fixture
def test_dirs(tmp_path):
    """Create test directories."""
    source_dir = tmp_path / "source"
    samples_dir = tmp_path / "samples"
    library_dir = tmp_path / "library"

    source_dir.mkdir()
    samples_dir.mkdir()
    library_dir.mkdir()

    return {
        "source_dir": source_dir,
        "samples_dir": samples_dir,
        "library_dir": library_dir,
    }


def make_manager(dirs):
    """Create a LibraryManager from directory dict."""
    return LibraryManager(
        source_dir=dirs["source_dir"],
        samples_dir=dirs["samples_dir"],
        library_dir=dirs["library_dir"],
    )


@pytest.fixture
def library_manager(test_dirs):
    """Create a LibraryManager with empty test directories."""
    return make_manager(test_dirs)


@pytest.fixture
def source_with_packs(test_dirs):
    """Create source directory with sample packs."""
    source_dir = test_dirs["source_dir"]

    # Create pack 1 - use names that match category patterns
    # Pattern needs word boundary, so use space or hyphen instead of underscore
    pack1 = source_dir / "808 Drum Kit"
    pack1.mkdir()
    (pack1 / "bd 01.wav").write_bytes(b"fake audio data")
    (pack1 / "bd 02.wav").write_bytes(b"fake audio data")
    (pack1 / "snare 01.wav").write_bytes(b"fake audio data")
    (pack1 / "hh 01.wav").write_bytes(b"fake audio data")

    # Create pack 2
    pack2 = source_dir / "Vinyl House Drums"
    pack2.mkdir()
    (pack2 / "VH bd.wav").write_bytes(b"fake audio data")
    (pack2 / "VH snare.wav").write_bytes(b"fake audio data")

    # Create pack 3 with loops
    pack3 = source_dir / "Tech Loops 125"
    pack3.mkdir()
    (pack3 / "drum loop 125bpm.wav").write_bytes(b"fake audio data")
    (pack3 / "perc loop.wav").write_bytes(b"fake audio data")

    return test_dirs


class TestLibraryManagerInit:
    """Tests for LibraryManager initialization."""

    def test_init_with_paths(self, test_dirs):
        """Initialize manager with paths."""
        manager = make_manager(test_dirs)
        assert manager.source_dir == test_dirs["source_dir"]
        assert manager.samples_dir == test_dirs["samples_dir"]
        assert manager.library_dir == test_dirs["library_dir"]

    def test_init_stores_paths(self, tmp_path):
        """Manager stores resolved paths."""
        source_dir = tmp_path / "source"
        samples_dir = tmp_path / "samples"
        library_dir = tmp_path / "library"

        source_dir.mkdir()
        samples_dir.mkdir()
        library_dir.mkdir()

        manager = LibraryManager(
            source_dir=source_dir,
            samples_dir=samples_dir,
            library_dir=library_dir,
        )

        assert manager.source_dir == source_dir.resolve()
        assert manager.samples_dir == samples_dir.resolve()
        assert manager.library_dir == library_dir.resolve()


class TestListPacks:
    """Tests for list_packs method."""

    def test_list_empty_source(self, library_manager):
        """List packs from empty source directory."""
        packs = library_manager.list_packs()
        assert packs == []

    def test_list_packs_with_content(self, source_with_packs):
        """List packs from populated source directory."""
        manager = make_manager(source_with_packs)
        packs = manager.list_packs()

        assert len(packs) == 3
        pack_names = {p["name"] for p in packs}
        assert "808 Drum Kit" in pack_names
        assert "Vinyl House Drums" in pack_names
        assert "Tech Loops 125" in pack_names

    def test_list_packs_returns_packinfo(self, source_with_packs):
        """Returned packs have PackInfo structure."""
        manager = make_manager(source_with_packs)
        packs = manager.list_packs()

        for pack in packs:
            assert "name" in pack
            assert "file_count" in pack
            assert "size_mb" in pack
            assert "sample_ids" in pack

    def test_list_packs_source_unavailable(self, tmp_path):
        """Raise error when source directory is unavailable."""
        manager = LibraryManager(
            source_dir=Path("/nonexistent/path"),
            samples_dir=tmp_path / "samples",
            library_dir=tmp_path / "library",
        )

        with pytest.raises(SourceNotAvailableError):
            manager.list_packs()


class TestSearchPacks:
    """Tests for search_packs method."""

    def test_search_by_name(self, source_with_packs):
        """Search packs by name pattern."""
        manager = make_manager(source_with_packs)

        results = manager.search_packs("808")
        assert len(results) == 1
        assert results[0]["name"] == "808 Drum Kit"

    def test_search_case_insensitive(self, source_with_packs):
        """Search is case insensitive."""
        manager = make_manager(source_with_packs)

        results = manager.search_packs("vinyl")
        assert len(results) == 1
        assert results[0]["name"] == "Vinyl House Drums"

    def test_search_partial_match(self, source_with_packs):
        """Search matches partial names."""
        manager = make_manager(source_with_packs)

        results = manager.search_packs("drum")
        assert len(results) == 2  # Both 808 Drum Kit and Vinyl House Drums

    def test_search_no_matches(self, source_with_packs):
        """Search with no matches returns empty list."""
        manager = make_manager(source_with_packs)

        results = manager.search_packs("nonexistent")
        assert results == []


class TestGetPackStatus:
    """Tests for get_pack_status method."""

    def test_get_status_remote_pack(self, source_with_packs):
        """Get status of remote (not cached) pack."""
        manager = make_manager(source_with_packs)

        status = manager.get_pack_status("808 Drum Kit")

        assert status["name"] == "808 Drum Kit"
        assert status["status"] == "remote"
        assert status["file_count"] == 4

    def test_get_status_nonexistent_pack(self, source_with_packs):
        """Raise error for nonexistent pack."""
        manager = make_manager(source_with_packs)

        with pytest.raises(PackNotFoundError):
            manager.get_pack_status("Nonexistent Pack")

    def test_get_status_cached_pack(self, source_with_packs):
        """Get status of cached (copied but not enabled) pack."""
        manager = make_manager(source_with_packs)

        # Enable pack first to create cache, then check status
        manager.enable_pack("808 Drum Kit")

        # Now disable it (removes symlinks but keeps cache)
        manager.disable_pack("808 Drum Kit")

        status = manager.get_pack_status("808 Drum Kit")
        assert status["status"] == "cached"

    def test_get_status_enabled_pack(self, source_with_packs):
        """Get status of enabled pack (has symlinks)."""
        manager = make_manager(source_with_packs)

        # Enable the pack
        manager.enable_pack("808 Drum Kit")

        status = manager.get_pack_status("808 Drum Kit")
        assert status["status"] == "enabled"


class TestEnablePack:
    """Tests for enable_pack method."""

    def test_enable_pack_copies_files(self, source_with_packs):
        """Enable pack copies files from source to cache."""
        manager = make_manager(source_with_packs)

        result = manager.enable_pack("808 Drum Kit")

        assert result["pack_name"] == "808 Drum Kit"
        assert result["samples_enabled"] > 0
        assert result["copy_stats"]["copied"] > 0

        # Check files were copied (to sample ID directories, not pack name)
        samples_dir = source_with_packs["samples_dir"]
        cached_dirs = [d for d in samples_dir.iterdir() if d.is_dir()]
        assert len(cached_dirs) > 0

    def test_enable_pack_creates_symlinks(self, source_with_packs):
        """Enable pack creates symlinks in library directory."""
        manager = make_manager(source_with_packs)

        manager.enable_pack("808 Drum Kit")

        # Check symlinks were created
        library_dir = source_with_packs["library_dir"]
        symlink_dirs = list(library_dir.iterdir())
        assert len(symlink_dirs) > 0

    def test_enable_nonexistent_pack(self, source_with_packs):
        """Raise error when enabling nonexistent pack."""
        manager = make_manager(source_with_packs)

        with pytest.raises(PackNotFoundError):
            manager.enable_pack("Nonexistent Pack")

    def test_enable_already_enabled_pack(self, source_with_packs):
        """Re-enabling pack is idempotent."""
        manager = make_manager(source_with_packs)

        manager.enable_pack("808 Drum Kit")
        result2 = manager.enable_pack("808 Drum Kit")

        # Should succeed without duplicating files
        assert result2["pack_name"] == "808 Drum Kit"


class TestDisablePack:
    """Tests for disable_pack method."""

    def test_disable_enabled_pack(self, source_with_packs):
        """Disable pack removes symlinks but keeps cache."""
        manager = make_manager(source_with_packs)

        # First enable
        result = manager.enable_pack("808 Drum Kit")
        sample_ids = result["sample_ids"]

        # Then disable
        count = manager.disable_pack("808 Drum Kit")

        assert count > 0

        # Cache should still exist (sample ID directories)
        samples_dir = source_with_packs["samples_dir"]
        for sample_id in sample_ids:
            assert (samples_dir / sample_id).exists()

        # But library symlinks should be removed
        library_dir = source_with_packs["library_dir"]
        remaining = [d for d in library_dir.iterdir() if "808dk" in d.name]
        assert len(remaining) == 0

    def test_disable_not_enabled_pack(self, source_with_packs):
        """Disabling not-enabled pack returns 0."""
        manager = make_manager(source_with_packs)

        count = manager.disable_pack("808 Drum Kit")
        assert count == 0


class TestPurgePack:
    """Tests for purge_pack method."""

    def test_purge_cached_pack(self, source_with_packs):
        """Purge removes pack from cache entirely."""
        manager = make_manager(source_with_packs)

        # First enable (which caches)
        enable_result = manager.enable_pack("808 Drum Kit")
        sample_ids = enable_result["sample_ids"]

        # Then purge
        result = manager.purge_pack("808 Drum Kit")

        assert result is True

        # Cache should be gone (sample ID directories removed)
        samples_dir = source_with_packs["samples_dir"]
        for sample_id in sample_ids:
            assert not (samples_dir / sample_id).exists()

    def test_purge_not_cached_pack(self, source_with_packs):
        """Purging not-cached pack returns False."""
        manager = make_manager(source_with_packs)

        result = manager.purge_pack("808 Drum Kit")
        assert result is False


class TestListEnabledSamples:
    """Tests for list_enabled_samples method."""

    def test_list_no_enabled(self, library_manager):
        """List returns empty when nothing enabled."""
        samples = library_manager.list_enabled_samples()
        assert samples == []

    def test_list_enabled_samples(self, source_with_packs):
        """List all enabled samples."""
        manager = make_manager(source_with_packs)
        manager.enable_pack("808 Drum Kit")

        samples = manager.list_enabled_samples()

        assert len(samples) > 0
        for sample in samples:
            assert "id" in sample
            assert "category" in sample
            assert "enabled" in sample
            assert sample["enabled"] is True


class TestGetSamplesByType:
    """Tests for get_samples_by_type method (SampleLookup interface)."""

    def test_get_samples_by_type_empty(self, library_manager):
        """Get samples returns empty when nothing enabled."""
        samples = library_manager.get_samples_by_type("bd")
        assert samples == []

    def test_get_samples_by_category(self, source_with_packs):
        """Get samples by drum category."""
        manager = make_manager(source_with_packs)
        manager.enable_pack("808 Drum Kit")

        kicks = manager.get_samples_by_type("bd")
        assert len(kicks) > 0

        snares = manager.get_samples_by_type("sn")
        assert len(snares) > 0

    def test_get_samples_with_limit(self, source_with_packs):
        """Limit number of returned samples."""
        manager = make_manager(source_with_packs)
        manager.enable_pack("808 Drum Kit")

        samples = manager.get_samples_by_type("bd", limit=1)
        assert len(samples) <= 1

    def test_get_samples_returns_ids(self, source_with_packs):
        """Returns sample IDs (strings), not SampleInfo."""
        manager = make_manager(source_with_packs)
        manager.enable_pack("808 Drum Kit")

        samples = manager.get_samples_by_type("bd")
        assert all(isinstance(s, str) for s in samples)
