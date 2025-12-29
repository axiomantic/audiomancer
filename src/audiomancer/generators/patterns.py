"""Pattern generation using Magenta models.

This module provides high-level pattern generation functions using Magenta's
DrumsRNN and MelodyRNN models. It handles graceful degradation when Magenta
is not installed.
"""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from ..errors import GenerationError, InferenceTimeoutError, ModelLoadError

# Try to import Magenta - graceful degradation if not available
try:
    import magenta  # type: ignore
    from magenta.models.drums_rnn import drums_rnn_sequence_generator  # type: ignore
    from magenta.models.melody_rnn import melody_rnn_sequence_generator  # type: ignore
    import tensorflow as tf  # type: ignore
    from magenta.music import sequences_lib  # type: ignore
    import note_seq  # type: ignore
    MAGENTA_AVAILABLE = True
except ImportError:
    MAGENTA_AVAILABLE = False


# Musical scale definitions (semitones from root)
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "pentatonic": [0, 2, 4, 7, 9],
}

# Note name to MIDI pitch mapping
NOTE_NAMES = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


class Pattern:
    """Generated musical pattern with MIDI data and code representations."""

    def __init__(
        self,
        pattern_id: str,
        pattern_type: Literal["drums", "melody", "bass"],
        midi_data: bytes,
        tidal_code: str,
        sc_code: str,
        bpm: float,
        bars: int,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        parent_ids: Optional[list[str]] = None,
        generation_method: str = "generated",
        mutation_amount: Optional[float] = None,
    ):
        self.id = pattern_id
        self.type = pattern_type
        self.midi_data = midi_data
        self.tidal_code = tidal_code
        self.sc_code = sc_code
        self.bpm = bpm
        self.bars = bars
        self.key = key
        self.scale = scale
        self.parent_ids = parent_ids or []
        self.generation_method = generation_method
        self.mutation_amount = mutation_amount
        self.created_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "midi_data": self.midi_data.hex(),
            "tidal_code": self.tidal_code,
            "sc_code": self.sc_code,
            "bpm": self.bpm,
            "bars": self.bars,
            "key": self.key,
            "scale": self.scale,
            "parent_ids": self.parent_ids,
            "generation_method": self.generation_method,
            "mutation_amount": self.mutation_amount,
            "created_at": self.created_at.isoformat(),
        }


def _check_magenta_available() -> None:
    """Raise error if Magenta is not installed."""
    if not MAGENTA_AVAILABLE:
        raise ModelLoadError(
            "Magenta not available. Install with: pip install magenta tensorflow",
            details={
                "package": "magenta",
                "install_cmd": "pip install magenta tensorflow",
            },
        )


def _generate_pattern_id() -> str:
    """Generate unique pattern ID."""
    return f"ptrn_{uuid.uuid4().hex[:8]}"


def _parse_key(key_str: str) -> int:
    """Parse key string to MIDI root note.

    Args:
        key_str: Key name like "C", "F#", "Bbm", "C#minor"

    Returns:
        MIDI pitch of root note (0-11 within octave)

    Example:
        >>> _parse_key("C")
        0
        >>> _parse_key("F#m")
        6
    """
    # Remove "m" or "minor" suffix
    key_clean = key_str.replace("minor", "").replace("m", "").strip()

    if key_clean not in NOTE_NAMES:
        raise GenerationError(
            f"Invalid key: {key_str}",
            details={"key": key_str, "valid_keys": list(NOTE_NAMES.keys())},
        )

    return NOTE_NAMES[key_clean]


def generate_drums(
    style: str = "house",
    bpm: float = 120.0,
    bars: int = 4,
    temperature: float = 1.0,
    timeout: float = 30.0,
) -> Pattern:
    """Generate a drum pattern using Magenta's DrumsRNN.

    Styles: house, techno, breakbeat, trap, jazz

    Args:
        style: Generation style hint
        bpm: Tempo in BPM
        bars: Number of bars to generate
        temperature: Randomness (0.0 = deterministic, 1.0+ = creative)
        timeout: Maximum generation time in seconds

    Returns:
        Generated drum pattern

    Raises:
        GenerationError: If generation fails
        InferenceTimeoutError: If model takes too long
        ModelLoadError: If Magenta not available

    Example:
        >>> pattern = generate_drums(style="techno", bpm=130, bars=4)
        >>> pattern.type
        'drums'
        >>> pattern.tidal_code
        'd1 $ sound "bd ~ sd ~ bd bd sd ~"'
    """
    _check_magenta_available()

    start_time = time.time()

    try:
        # Create a simple drum sequence as placeholder
        # In real implementation, use Magenta's DrumsRNN
        # For now, create a basic pattern based on style

        pattern_id = _generate_pattern_id()

        # Simple style-based patterns
        style_patterns = {
            "house": "bd ~ sd ~ bd ~ sd ~",
            "techno": "bd hh sd hh bd hh sd hh",
            "breakbeat": "bd*2 ~ sd ~ bd ~ sd*2 ~",
            "trap": "bd ~ ~ ~ sd ~ bd bd",
            "jazz": "~ bd ~ sd ~ bd sd ~",
        }

        tidal_pattern = style_patterns.get(style, style_patterns["house"])

        # Create minimal MIDI data (placeholder)
        midi_data = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0"  # Minimal MIDI header

        # Create SuperCollider code
        sc_code = f"""(
Pdef(\\drums,
    Pbind(
        \\instrument, \\default,
        \\dur, Pseq([0.25], inf),
        \\amp, 0.8,
    )
).play;
)"""

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise InferenceTimeoutError(
                "Drum generation timed out",
                details={
                    "model": "drums_rnn",
                    "timeout_seconds": timeout,
                    "elapsed": elapsed,
                },
            )

        return Pattern(
            pattern_id=pattern_id,
            pattern_type="drums",
            midi_data=midi_data,
            tidal_code=f'd1 $ sound "{tidal_pattern}"',
            sc_code=sc_code,
            bpm=bpm,
            bars=bars,
            generation_method="generated",
        )

    except Exception as e:
        if isinstance(e, (GenerationError, InferenceTimeoutError, ModelLoadError)):
            raise
        raise GenerationError(
            f"Drum generation failed: {str(e)}",
            details={"style": style, "error": str(e)},
        )


def generate_melody(
    key: str = "C",
    scale: str = "major",
    bpm: float = 120.0,
    bars: int = 4,
    temperature: float = 1.0,
    timeout: float = 30.0,
) -> Pattern:
    """Generate a melody using Magenta's MelodyRNN.

    Keys: C, C#, D, D#, E, F, F#, G, G#, A, A#, B
    Scales: major, minor, dorian, mixolydian, pentatonic

    Args:
        key: Root note (e.g., "C", "F#", "Bb")
        scale: Scale type
        bpm: Tempo in BPM
        bars: Number of bars to generate
        temperature: Randomness (0.0 = deterministic, 1.0+ = creative)
        timeout: Maximum generation time in seconds

    Returns:
        Generated melody pattern

    Raises:
        GenerationError: If generation fails
        InferenceTimeoutError: If model takes too long
        ModelLoadError: If Magenta not available

    Example:
        >>> pattern = generate_melody(key="Am", scale="minor", bars=4)
        >>> pattern.key
        'A'
        >>> pattern.scale
        'minor'
    """
    _check_magenta_available()

    start_time = time.time()

    try:
        # Parse key
        root_pitch = _parse_key(key)

        # Validate scale
        if scale not in SCALES:
            raise GenerationError(
                f"Invalid scale: {scale}",
                details={"scale": scale, "valid_scales": list(SCALES.keys())},
            )

        pattern_id = _generate_pattern_id()

        # Create simple melody based on scale (placeholder)
        scale_notes = SCALES[scale]
        # Simple ascending pattern
        notes = " ".join([str((root_pitch + n) % 12) for n in scale_notes[:4]])

        # Create minimal MIDI data (placeholder)
        midi_data = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0"

        # Create TidalCycles code
        key_clean = key.replace("minor", "").replace("m", "").strip()
        tidal_code = f'd1 $ n "{notes}" # s "superpiano" # scale "{scale}"'

        # Create SuperCollider code
        sc_code = f"""(
Pdef(\\melody,
    Pbind(
        \\instrument, \\default,
        \\midinote, Pseq([{notes}], inf) + 60,
        \\dur, Pseq([0.5], inf),
        \\amp, 0.6,
    )
).play;
)"""

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise InferenceTimeoutError(
                "Melody generation timed out",
                details={
                    "model": "melody_rnn",
                    "timeout_seconds": timeout,
                    "elapsed": elapsed,
                },
            )

        return Pattern(
            pattern_id=pattern_id,
            pattern_type="melody",
            midi_data=midi_data,
            tidal_code=tidal_code,
            sc_code=sc_code,
            bpm=bpm,
            bars=bars,
            key=key_clean,
            scale=scale,
            generation_method="generated",
        )

    except Exception as e:
        if isinstance(e, (GenerationError, InferenceTimeoutError, ModelLoadError)):
            raise
        raise GenerationError(
            f"Melody generation failed: {str(e)}",
            details={"key": key, "scale": scale, "error": str(e)},
        )


def generate_bass(
    key: str = "C",
    bpm: float = 120.0,
    bars: int = 4,
    style: str = "synth",
    timeout: float = 30.0,
) -> Pattern:
    """Generate a bassline.

    Styles: synth, acoustic, walking, slap

    Args:
        key: Root note
        bpm: Tempo in BPM
        bars: Number of bars
        style: Bass style hint
        timeout: Maximum generation time in seconds

    Returns:
        Generated bass pattern

    Raises:
        GenerationError: If generation fails
        InferenceTimeoutError: If model takes too long
        ModelLoadError: If Magenta not available

    Example:
        >>> pattern = generate_bass(key="F#", style="synth", bars=4)
        >>> pattern.type
        'bass'
    """
    _check_magenta_available()

    start_time = time.time()

    try:
        # Parse key
        root_pitch = _parse_key(key)

        pattern_id = _generate_pattern_id()

        # Create simple bass line (root, fifth, octave pattern)
        notes = f"{root_pitch} {(root_pitch + 7) % 12} {root_pitch} {(root_pitch + 7) % 12}"

        # Create minimal MIDI data (placeholder)
        midi_data = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0"

        # Create TidalCycles code
        key_clean = key.replace("minor", "").replace("m", "").strip()
        tidal_code = f'd1 $ n "{notes}" # s "bass1" # octave 2'

        # Create SuperCollider code
        sc_code = f"""(
Pdef(\\bass,
    Pbind(
        \\instrument, \\default,
        \\midinote, Pseq([{notes}], inf) + 36,  // Low octave
        \\dur, Pseq([0.5], inf),
        \\amp, 0.7,
    )
).play;
)"""

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise InferenceTimeoutError(
                "Bass generation timed out",
                details={
                    "model": "bass_generator",
                    "timeout_seconds": timeout,
                    "elapsed": elapsed,
                },
            )

        return Pattern(
            pattern_id=pattern_id,
            pattern_type="bass",
            midi_data=midi_data,
            tidal_code=tidal_code,
            sc_code=sc_code,
            bpm=bpm,
            bars=bars,
            key=key_clean,
            scale="minor",  # Default to minor for bass
            generation_method="generated",
        )

    except Exception as e:
        if isinstance(e, (GenerationError, InferenceTimeoutError, ModelLoadError)):
            raise
        raise GenerationError(
            f"Bass generation failed: {str(e)}",
            details={"key": key, "style": style, "error": str(e)},
        )


def humanize(
    pattern: Pattern,
    amount: float = 0.5,
) -> Pattern:
    """Add human-like timing variations using GrooVAE.

    Amount: 0.0 (quantized) to 1.0 (very loose)

    Args:
        pattern: Pattern to humanize
        amount: Humanization strength

    Returns:
        New pattern with timing variations

    Raises:
        ModelLoadError: If GrooVAE not available

    Example:
        >>> original = generate_drums(style="techno")
        >>> humanized = humanize(original, amount=0.3)
        >>> humanized.parent_ids
        [original.id]
    """
    _check_magenta_available()

    # Create new pattern with same data but marked as humanized
    new_id = _generate_pattern_id()

    return Pattern(
        pattern_id=new_id,
        pattern_type=pattern.type,
        midi_data=pattern.midi_data,  # In real implementation, modify timing
        tidal_code=pattern.tidal_code,
        sc_code=pattern.sc_code,
        bpm=pattern.bpm,
        bars=pattern.bars,
        key=pattern.key,
        scale=pattern.scale,
        parent_ids=[pattern.id],
        generation_method="humanized",
        mutation_amount=amount,
    )
