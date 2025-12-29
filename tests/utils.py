"""Test utilities and helpers for audiomancer tests."""
from pathlib import Path
from typing import Dict, Any, Optional
import json
import numpy as np


def create_test_audio(
    duration: float = 1.0,
    sample_rate: int = 44100,
    frequency: float = 440.0,
    waveform: str = "sine",
) -> np.ndarray:
    """Create test audio data.

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency in Hz
        waveform: Type of waveform ('sine', 'square', 'saw', 'noise', 'silence')

    Returns:
        Audio data as numpy array
    """
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    if waveform == "sine":
        audio = np.sin(2 * np.pi * frequency * t)
    elif waveform == "square":
        audio = np.sign(np.sin(2 * np.pi * frequency * t))
    elif waveform == "saw":
        audio = 2 * (t * frequency % 1) - 1
    elif waveform == "noise":
        audio = np.random.uniform(-1, 1, samples)
    elif waveform == "silence":
        audio = np.zeros(samples)
    else:
        raise ValueError(f"Unknown waveform: {waveform}")

    return audio.astype(np.float32)


def create_test_impulse_train(
    duration: float = 1.0,
    sample_rate: int = 44100,
    bpm: float = 120.0,
    beats_per_bar: int = 4,
) -> np.ndarray:
    """Create an impulse train at specified BPM.

    Useful for testing onset detection and rhythm analysis.

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        bpm: Tempo in beats per minute
        beats_per_bar: Number of beats per bar

    Returns:
        Audio data with impulses at beat positions
    """
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.float32)

    beat_interval = 60.0 / bpm  # seconds per beat
    beat_samples = int(beat_interval * sample_rate)

    for i in range(0, samples, beat_samples):
        if i < samples:
            audio[i] = 1.0

    return audio


def assert_dict_subset(subset: Dict[str, Any], full: Dict[str, Any]) -> None:
    """Assert that subset is contained in full dict.

    Useful for testing that expected fields exist without
    requiring exact match of all fields.

    Args:
        subset: Expected subset of fields
        full: Full dict to check against

    Raises:
        AssertionError: If subset is not contained in full
    """
    for key, expected_value in subset.items():
        assert key in full, f"Key '{key}' not found in {list(full.keys())}"

        actual_value = full[key]

        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            assert_dict_subset(expected_value, actual_value)
        else:
            assert actual_value == expected_value, (
                f"Value mismatch for '{key}': "
                f"expected {expected_value}, got {actual_value}"
            )


def load_golden_file(path: Path, format: str = "json") -> Any:
    """Load a golden file for comparison testing.

    Args:
        path: Path to golden file
        format: Format of file ('json', 'text', 'binary')

    Returns:
        Loaded data
    """
    if format == "json":
        with open(path) as f:
            return json.load(f)
    elif format == "text":
        return path.read_text()
    elif format == "binary":
        return path.read_bytes()
    else:
        raise ValueError(f"Unknown format: {format}")


def save_golden_file(path: Path, data: Any, format: str = "json") -> None:
    """Save data as a golden file.

    Args:
        path: Path to save to
        data: Data to save
        format: Format to use ('json', 'text', 'binary')
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    elif format == "text":
        path.write_text(data)
    elif format == "binary":
        path.write_bytes(data)
    else:
        raise ValueError(f"Unknown format: {format}")


def assert_audio_similar(
    audio1: np.ndarray,
    audio2: np.ndarray,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> None:
    """Assert that two audio arrays are similar.

    Args:
        audio1: First audio array
        audio2: Second audio array
        rtol: Relative tolerance
        atol: Absolute tolerance

    Raises:
        AssertionError: If arrays are not similar
    """
    assert audio1.shape == audio2.shape, (
        f"Shape mismatch: {audio1.shape} vs {audio2.shape}"
    )
    assert np.allclose(audio1, audio2, rtol=rtol, atol=atol), (
        "Audio arrays differ beyond tolerance"
    )


def assert_valid_sample_metadata(metadata: Dict[str, Any]) -> None:
    """Assert that sample metadata has all required fields.

    Args:
        metadata: Sample metadata dict

    Raises:
        AssertionError: If required fields are missing or invalid
    """
    required_fields = [
        "id",
        "file_path",
        "semantic_id",
        "category",
        "duration_ms",
        "sample_rate",
        "channels",
    ]

    for field in required_fields:
        assert field in metadata, f"Missing required field: {field}"

    # Type checks
    assert isinstance(metadata["id"], str)
    assert isinstance(metadata["file_path"], (str, Path))
    assert isinstance(metadata["semantic_id"], str)
    assert isinstance(metadata["category"], str)
    assert isinstance(metadata["duration_ms"], (int, float))
    assert isinstance(metadata["sample_rate"], int)
    assert isinstance(metadata["channels"], int)

    # Value checks
    assert metadata["duration_ms"] >= 0
    assert metadata["sample_rate"] > 0
    assert metadata["channels"] > 0


def create_mock_sample(
    sample_id: str = "test_001",
    file_path: str = "/path/to/test.wav",
    semantic_id: str = "test_sample",
    category: str = "bd",
    **kwargs,
) -> Dict[str, Any]:
    """Create mock sample metadata for testing.

    Args:
        sample_id: Sample ID
        file_path: File path
        semantic_id: Semantic ID
        category: Category
        **kwargs: Additional fields to override

    Returns:
        Sample metadata dict
    """
    base = {
        "id": sample_id,
        "file_path": file_path,
        "semantic_id": semantic_id,
        "category": category,
        "source_pack": "Test Pack",
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
        "tags": [],
        "created_at": "2025-12-28T00:00:00Z",
        "updated_at": "2025-12-28T00:00:00Z",
    }

    base.update(kwargs)
    return base


def assert_valid_tidal_pattern(pattern: str) -> None:
    """Assert that a string is a valid TidalCycles pattern.

    Basic syntax validation - does not execute the pattern.

    Args:
        pattern: TidalCycles pattern string

    Raises:
        AssertionError: If pattern appears invalid
    """
    assert isinstance(pattern, str)
    assert len(pattern) > 0

    # Should start with channel identifier (d1, d2, etc.)
    assert pattern.strip().startswith("d"), (
        "Pattern should start with channel identifier (d1, d2, etc.)"
    )

    # Should contain $ operator
    assert "$" in pattern, "Pattern should contain $ operator"

    # Basic bracket matching
    open_brackets = pattern.count("[")
    close_brackets = pattern.count("]")
    assert open_brackets == close_brackets, "Mismatched brackets"

    open_braces = pattern.count("{")
    close_braces = pattern.count("}")
    assert open_braces == close_braces, "Mismatched braces"

    open_parens = pattern.count("(")
    close_parens = pattern.count(")")
    assert open_parens == close_parens, "Mismatched parentheses"


def assert_valid_supercollider_code(code: str) -> None:
    """Assert that a string is valid SuperCollider code.

    Basic syntax validation - does not execute the code.

    Args:
        code: SuperCollider code string

    Raises:
        AssertionError: If code appears invalid
    """
    assert isinstance(code, str)
    assert len(code) > 0

    # Basic bracket matching
    open_brackets = code.count("[")
    close_brackets = code.count("]")
    assert open_brackets == close_brackets, "Mismatched brackets"

    open_braces = code.count("{")
    close_braces = code.count("}")
    assert open_braces == close_braces, "Mismatched braces"

    open_parens = code.count("(")
    close_parens = code.count(")")
    assert open_parens == close_parens, "Mismatched parentheses"

    # Should end with semicolon or closing brace/bracket
    stripped = code.strip()
    assert stripped[-1] in [";", "}", "]", ")"], (
        "SuperCollider code should end with semicolon or closing bracket"
    )
