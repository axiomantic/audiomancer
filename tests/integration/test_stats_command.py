"""Integration tests for stats CLI command."""

from pathlib import Path
from typer.testing import CliRunner
import pytest
import os
import yaml

from audiomancer.cli import app
from audiomancer.storage.db import SampleStore
from audiomancer.config import load_config

runner = CliRunner()


@pytest.fixture
def populated_db(tmp_path, monkeypatch):
    """Create a database with sample data for testing stats."""
    db_path = tmp_path / "test.db"

    # Create config directory and file (XDG_CONFIG_HOME/audiomancer/config.yaml)
    config_dir = tmp_path / "audiomancer"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Write minimal config pointing to test database
    config_data = {
        "storage": {
            "db_path": str(db_path),
            "embeddings_path": str(tmp_path / "embeddings"),
            "models_path": str(tmp_path / "models"),
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Set XDG_CONFIG_HOME to use our test config (it will append /audiomancer)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    store = SampleStore(str(db_path))

    # Create sample data with various characteristics
    samples = [
        # Kicks with different BPMs and keys
        {
            "id": "kick_1",
            "file_path": "/samples/kick1.wav",
            "file_hash": "hash_kick_1",
            "duration_ms": 500.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 88200,
            "instrument_type": "kick",
            "bpm": 120.0,
            "key": "C",
        },
        {
            "id": "kick_2",
            "file_path": "/samples/kick2.wav",
            "file_hash": "hash_kick_2",
            "duration_ms": 500.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 88200,
            "instrument_type": "kick",
            "bpm": 90.0,
            "key": "A",
        },
        {
            "id": "kick_3",
            "file_path": "/samples/kick3.wav",
            "file_hash": "hash_kick_3",
            "duration_ms": 500.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 88200,
            "instrument_type": "kick",
            "bpm": 170.0,
            "key": "C",
        },
        # Snares
        {
            "id": "snare_1",
            "file_path": "/samples/snare1.wav",
            "file_hash": "hash_snare_1",
            "duration_ms": 300.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 52920,
            "instrument_type": "snare",
            "bpm": 128.0,
            "key": "D",
        },
        {
            "id": "snare_2",
            "file_path": "/samples/snare2.wav",
            "file_hash": "hash_snare_2",
            "duration_ms": 300.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 52920,
            "instrument_type": "snare",
            "bpm": 145.0,
            "key": "A",
        },
        # Hats
        {
            "id": "hat_1",
            "file_path": "/samples/hat1.wav",
            "file_hash": "hash_hat_1",
            "duration_ms": 200.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 35280,
            "instrument_type": "hat",
            "bpm": 130.0,
            "key": "C",
        },
        # Bass
        {
            "id": "bass_1",
            "file_path": "/samples/bass1.wav",
            "file_hash": "hash_bass_1",
            "duration_ms": 1000.0,
            "sample_rate": 44100,
            "channels": 2,
            "bit_depth": 16,
            "file_size_bytes": 176400,
            "instrument_type": "bass",
            "bpm": 110.0,
            "key": "E",
        },
    ]

    added_count = 0
    for sample in samples:
        try:
            store.add(sample)
            added_count += 1
        except Exception as e:
            print(f"Failed to add sample {sample['id']}: {e}")

    # Verify all samples were added
    actual_count = store.count()
    assert actual_count == len(samples), f"Expected {len(samples)} samples (added {added_count}), but count() returned {actual_count}"

    return db_path


def test_stats_command_shows_total_sample_count(populated_db, monkeypatch):
    """stats command displays total number of samples in database."""
    # monkeypatch is already set by fixture, but need to ensure it's available
    result = runner.invoke(app, ['stats'])

    assert result.exit_code == 0

    # Should show total of 7 samples
    assert "7" in result.stdout
    assert any(word in result.stdout.lower() for word in ['total', 'samples'])


def test_stats_command_shows_instrument_type_breakdown(populated_db):
    """stats command displays breakdown by instrument type."""
    result = runner.invoke(app, ['stats'])

    assert result.exit_code == 0

    # Should show instrument types with counts
    assert "kick" in result.stdout.lower()
    assert "snare" in result.stdout.lower()
    assert "hat" in result.stdout.lower()
    assert "bass" in result.stdout.lower()

    # Should show correct counts (3 kicks, 2 snares, 1 hat, 1 bass)
    assert "3" in result.stdout  # kicks
    assert "2" in result.stdout  # snares


def test_stats_command_shows_bpm_distribution(populated_db):
    """stats command displays BPM distribution in ranges."""
    result = runner.invoke(app, ['stats'])

    assert result.exit_code == 0

    # Should show BPM ranges
    assert "bpm" in result.stdout.lower()

    # Should have different BPM ranges represented
    # 90, 110 (< 120), 120, 128, 130 (120-140), 145, 170 (> 140)
    assert any(word in result.stdout for word in ['<100', '100-120', '120-140', '140-160', '160+'])


def test_stats_command_shows_key_distribution(populated_db):
    """stats command displays musical key distribution."""
    result = runner.invoke(app, ['stats'])

    assert result.exit_code == 0

    # Should show key information
    assert "key" in result.stdout.lower()

    # Should show keys present in data (C, A, D, E)
    # At minimum, should show the most common key (C appears 3 times)
    assert "C" in result.stdout or "c" in result.stdout


def test_stats_command_handles_empty_database(tmp_path, monkeypatch):
    """stats command handles empty database gracefully."""
    # Create empty database
    db_path = tmp_path / "empty.db"
    store = SampleStore(str(db_path))

    # Create config directory and file (XDG_CONFIG_HOME/audiomancer/config.yaml)
    config_dir = tmp_path / "audiomancer"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Write minimal config pointing to empty test database
    config_data = {
        "storage": {
            "db_path": str(db_path),
            "embeddings_path": str(tmp_path / "embeddings"),
            "models_path": str(tmp_path / "models"),
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Set XDG_CONFIG_HOME to use our test config (it will append /audiomancer)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = runner.invoke(app, ['stats'])

    # Should not crash
    assert result.exit_code == 0

    # Should indicate empty state
    assert "0" in result.stdout or "empty" in result.stdout.lower() or "no samples" in result.stdout.lower()


def test_stats_command_uses_rich_formatting(populated_db):
    """stats command uses Rich panels or tables for display."""
    result = runner.invoke(app, ['stats'])

    assert result.exit_code == 0

    # Rich uses box drawing characters for tables/panels
    # Check for common Rich formatting indicators
    # This is a heuristic test - Rich output includes formatting
    assert len(result.stdout) > 50  # Should have substantial output

    # Should have section headers or organized output
    assert any(word in result.stdout for word in ['─', '│', '┌', '┐', '└', '┘', 'Statistics', 'Distribution'])
