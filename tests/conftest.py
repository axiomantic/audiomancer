"""Pytest configuration and fixtures for audiomancer tests."""
import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_fixtures(fixtures_dir: Path) -> Path:
    """Path to sample fixtures."""
    return fixtures_dir / "samples"


@pytest.fixture
def synth_fixtures(fixtures_dir: Path) -> Path:
    """Path to synth fixtures."""
    return fixtures_dir / "synths"


@pytest.fixture
def midi_fixtures(fixtures_dir: Path) -> Path:
    """Path to MIDI fixtures."""
    return fixtures_dir / "midi"


@pytest.fixture
def golden_dir() -> Path:
    """Path to golden files directory."""
    return Path(__file__).parent / "golden"


@pytest.fixture
def mock_config(temp_dir: Path):
    """Create a mock configuration for testing."""
    from audiomancer.config import AudiomancerConfig, StorageConfig
    return AudiomancerConfig(
        storage=StorageConfig(
            db_path=temp_dir / "test.db",
            embeddings_path=temp_dir / "embeddings",
            models_path=temp_dir / "models",
        )
    )


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def sample_audio_data():
    """Generate simple audio data for testing.

    Returns a dict with different test audio scenarios:
    - silence: All zeros
    - sine_440: 1 second sine wave at 440 Hz
    - impulse: Single impulse (for testing onset detection)
    """
    import numpy as np

    sample_rate = 44100
    duration = 1.0
    samples = int(sample_rate * duration)

    # Generate test signals
    t = np.linspace(0, duration, samples, endpoint=False)

    return {
        "silence": np.zeros(samples, dtype=np.float32),
        "sine_440": np.sin(2 * np.pi * 440 * t).astype(np.float32),
        "impulse": np.concatenate([
            np.array([1.0], dtype=np.float32),
            np.zeros(samples - 1, dtype=np.float32)
        ]),
        "sample_rate": sample_rate,
    }


@pytest.fixture
def mock_sample_metadata():
    """Create mock sample metadata for testing."""
    return {
        "id": "test_sample_001",
        "file_path": "/path/to/test.wav",
        "semantic_id": "kick_808",
        "category": "bd",
        "source_pack": "808 Drum Kit",
        "duration_ms": 250.0,
        "sample_rate": 44100,
        "channels": 1,
        "bit_depth": 16,
        "file_size_bytes": 44100,
        "bpm": None,
        "is_loop": False,
        "analysis": {
            "tempo": None,
            "key": None,
            "spectral_centroid_mean": 1500.0,
            "rms_energy": 0.5,
        },
        "tags": ["drum", "kick", "808"],
        "created_at": "2025-12-28T00:00:00Z",
        "updated_at": "2025-12-28T00:00:00Z",
    }


@pytest.fixture
def mock_pattern_data():
    """Create mock TidalCycles pattern data for testing."""
    return {
        "simple_beat": 'd1 $ sound "bd sn bd sn"',
        "complex_pattern": 'd1 $ stack [sound "bd*4", sound "hh*8", sound "~ sn ~ sn"]',
        "with_effects": 'd1 $ sound "bd sn" # cutoff 1200 # resonance 0.7',
        "polyrhythm": 'd1 $ sound "{bd hh sn hh, arpy*3}"',
    }


@pytest.fixture
def mock_synthdef_data():
    """Create mock SuperCollider SynthDef data for testing."""
    return {
        "simple_sine": """
SynthDef(\\simple_sine, {
    |out=0, freq=440, amp=0.5, gate=1|
    var sig, env;
    env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate, doneAction: 2);
    sig = SinOsc.ar(freq) * amp * env;
    Out.ar(out, sig ! 2);
}).add;
""",
        "tb303": """
SynthDef(\\tb303, {
    |out=0, freq=440, cutoff=1200, resonance=0.7, envmod=0.6,
     decay=0.2, accent=0, slide=0, wave=0, gate=1, amp=0.5|
    var sig, env, fenv, osc1, osc2;

    env = EnvGen.kr(Env.asr(0.001, 1, 0.05), gate, doneAction: 2);
    fenv = EnvGen.kr(Env.perc(0.001, decay)) * envmod * 4000;

    freq = Lag.kr(freq, slide * 0.1);

    osc1 = Saw.ar(freq);
    osc2 = Pulse.ar(freq, 0.5);
    sig = Select.ar(wave, [osc1, osc2]);

    sig = MoogFF.ar(sig, (cutoff + fenv).clip(20, 20000), resonance);
    sig = sig * env * amp * (1 + (accent * 0.5));

    Out.ar(out, sig ! 2);
}).add;
""",
    }
