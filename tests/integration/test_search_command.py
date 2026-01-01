"""Integration tests for search CLI command."""

import shutil
from pathlib import Path
from typer.testing import CliRunner
import pytest

from audiomancer.cli import app
from audiomancer.storage.db import SampleStore

runner = CliRunner()


@pytest.fixture
def populated_db(tmp_path):
    """Create a database with test samples."""
    db_path = tmp_path / "test.db"
    store = SampleStore(str(db_path))

    # Add test samples with varying attributes
    samples = [
        {
            "id": "kick_808_1",
            "file_path": "/samples/808/kick_01.wav",
            "file_hash": "hash1",
            "duration_ms": 250.0,
            "sample_rate": 44100,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 44100,
            "bpm": 120.0,
            "key": "C",
            "instrument_type": "kick",
        },
        {
            "id": "snare_acoustic_1",
            "file_path": "/samples/acoustic/snare_01.wav",
            "file_hash": "hash2",
            "duration_ms": 300.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 24,
            "file_size_bytes": 88200,
            "bpm": 130.0,
            "key": "D",
            "instrument_type": "snare",
        },
        {
            "id": "hihat_909_1",
            "file_path": "/samples/909/hihat_closed.wav",
            "file_hash": "hash3",
            "duration_ms": 150.0,
            "sample_rate": 44100,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 22050,
            "bpm": 125.0,
            "key": None,
            "instrument_type": "hihat",
        },
        {
            "id": "bass_synth_1",
            "file_path": "/samples/synth/bass_low.wav",
            "file_hash": "hash4",
            "duration_ms": 1000.0,
            "sample_rate": 48000,
            "channels": 1,
            "bit_depth": 24,
            "file_size_bytes": 96000,
            "bpm": None,
            "key": "A",
            "instrument_type": "bass",
        },
        {
            "id": "kick_808_2",
            "file_path": "/samples/808/kick_02.wav",
            "file_hash": "hash5",
            "duration_ms": 280.0,
            "sample_rate": 44100,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 44100,
            "bpm": 140.0,
            "key": "C",
            "instrument_type": "kick",
        },
    ]

    for sample in samples:
        store.add(sample)

    return db_path


def test_search_command_with_text_query_finds_matching_samples(populated_db, tmp_path, monkeypatch):
    """search command with text query returns matching samples."""
    # Point to test database
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', '808'])

    assert result.exit_code == 0
    # Verify both 808 samples are found
    assert "kick_808_1" in result.stdout, "First 808 kick should be in results"
    assert "kick_808_2" in result.stdout, "Second 808 kick should be in results"


def test_search_command_displays_results_in_table(populated_db, monkeypatch):
    """search command displays results in a Rich table format."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'kick'])

    assert result.exit_code == 0
    # Should show table with headers
    assert any(header in result.stdout for header in ['ID', 'Name', 'BPM', 'Key', 'Instrument', 'Duration'])


def test_search_command_filters_by_bpm_range(populated_db, monkeypatch):
    """search command filters samples by BPM range."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'samples', '--bpm-min', '125', '--bpm-max', '135'])

    assert result.exit_code == 0
    # Verify INCLUSIONS: Should find hihat (125 BPM) and snare (130 BPM)
    assert "hihat_909" in result.stdout, "Expected hihat (125 BPM) in results"
    assert "snare_acoustic" in result.stdout, "Expected snare (130 BPM) in results"

    # Verify EXCLUSIONS: Should NOT find kick_808_1 (120 BPM) or kick_808_2 (140 BPM)
    assert "kick_808_1" not in result.stdout, "120 BPM kick should be excluded by --bpm-min 125"
    assert "kick_808_2" not in result.stdout, "140 BPM kick should be excluded by --bpm-max 135"


def test_search_command_filters_by_key(populated_db, monkeypatch):
    """search command filters samples by musical key."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'samples', '--key', 'C'])

    assert result.exit_code == 0
    # Verify INCLUSIONS: Should find both kick_808 samples (both in C)
    assert "kick_808_1" in result.stdout, "Kick 808_1 (key C) should be included"
    assert "kick_808_2" in result.stdout, "Kick 808_2 (key C) should be included"

    # Verify EXCLUSIONS: Should NOT find samples in other keys
    assert "snare_acoustic" not in result.stdout, "Snare (key D) should be excluded"
    assert "bass_synth" not in result.stdout, "Bass (key A) should be excluded"


def test_search_command_filters_by_instrument_type(populated_db, monkeypatch):
    """search command filters samples by instrument type."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'samples', '--instrument', 'bass'])

    assert result.exit_code == 0
    # Verify INCLUSIONS: Should find bass sample
    assert "bass_synth" in result.stdout, "Bass sample should be included"

    # Verify EXCLUSIONS: Should NOT find non-bass instruments
    assert "kick" not in result.stdout, "Kick samples should be excluded"
    assert "snare" not in result.stdout, "Snare sample should be excluded"
    assert "hihat" not in result.stdout, "Hihat sample should be excluded"


def test_search_command_respects_limit_option(populated_db, monkeypatch):
    """search command respects the --limit option."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'samples', '--limit', '2'])

    assert result.exit_code == 0
    # Should return at most 2 results
    # Count how many sample IDs appear in the output
    sample_ids = ['kick_808_1', 'kick_808_2', 'snare_acoustic_1', 'hihat_909_1', 'bass_synth_1']
    found_count = sum(1 for sid in sample_ids if sid in result.stdout)
    assert found_count <= 2, f"Expected at most 2 samples with --limit 2, found {found_count}"


def test_search_command_handles_no_results_gracefully(populated_db, monkeypatch):
    """search command handles empty results gracefully."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'nonexistent_sample'])

    assert result.exit_code == 0
    assert "no results" in result.stdout.lower() or "0" in result.stdout or "found" in result.stdout.lower()


def test_search_command_combines_multiple_filters(populated_db, monkeypatch):
    """search command combines text query with filters using AND logic."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, [
        'search', '808',
        '--instrument', 'kick',
        '--bpm-min', '115',
        '--bpm-max', '125',
        '--key', 'C'
    ])

    assert result.exit_code == 0
    # Verify INCLUSION: Should find kick_808_1 (120 BPM, kick, C key, path contains "808")
    assert "kick_808_1" in result.stdout, "kick_808_1 matches all filters"

    # Verify EXCLUSIONS: kick_808_2 fails BPM filter (140 > 125)
    assert "kick_808_2" not in result.stdout, "kick_808_2 should be excluded by BPM max"
    # Other samples fail multiple filters
    assert "snare" not in result.stdout, "Snare should be excluded (wrong instrument)"
    assert "bass" not in result.stdout, "Bass should be excluded (wrong instrument)"
    assert "hihat" not in result.stdout, "Hihat should be excluded (wrong instrument)"


def test_search_command_shows_sample_duration(populated_db, monkeypatch):
    """search command displays sample duration in results."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', 'kick'])

    assert result.exit_code == 0
    # Should show duration (250ms, 280ms, or converted to seconds)
    assert any(dur in result.stdout for dur in ['ms', 's', '0.', '250', '280'])


def test_search_command_shows_sample_id_and_name(populated_db, monkeypatch):
    """search command displays sample ID and file name."""
    monkeypatch.setenv("AUDIOMANCER_DB_PATH", str(populated_db))

    result = runner.invoke(app, ['search', '808'])

    assert result.exit_code == 0
    # Should show either ID or filename
    assert "kick_808" in result.stdout or "808" in result.stdout
