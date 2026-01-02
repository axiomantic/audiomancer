"""Pattern generation for music production.

This module provides algorithmic pattern generation using euclidean rhythms,
scale-based melodies, and style templates. All generation works without
external dependencies beyond mido for MIDI file creation.
"""

import random
import time
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

import mido
from mido import Message, MidiFile, MidiTrack

from ..errors import GenerationError, InferenceTimeoutError, ModelLoadError

if TYPE_CHECKING:
    from ..library.interfaces import SampleLookup

# Magenta is not used - all generation is algorithmic
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


def euclidean_rhythm(pulses: int, steps: int) -> list[bool]:
    """Generate euclidean rhythm pattern using Bjorklund's algorithm.

    Distributes pulses as evenly as possible across steps.
    Classic algorithm used in many world music traditions.

    Args:
        pulses: Number of beats/hits
        steps: Total number of steps

    Returns:
        List of booleans indicating hit positions

    Example:
        >>> euclidean_rhythm(3, 8)  # Tresillo
        [True, False, False, True, False, False, True, False]
        >>> euclidean_rhythm(5, 8)  # Cinquillo
        [True, False, True, True, False, True, True, False]
    """
    if pulses >= steps:
        return [True] * steps
    if pulses == 0:
        return [False] * steps

    # Bjorklund's algorithm
    pattern: list[list[bool]] = [[True]] * pulses + [[False]] * (steps - pulses)

    def bjorklund(pattern: list[list[bool]]) -> list[list[bool]]:
        if len(set(map(len, pattern))) <= 1:
            return pattern

        first = []
        second = []
        for i, p in enumerate(pattern):
            if i < len(pattern) // 2:
                first.append(p)
            else:
                second.append(p)

        result = []
        for f, s in zip(first, second):
            result.append(f + s)
        result.extend(second[len(first):])

        return bjorklund(result)

    result_pattern = bjorklund(pattern)
    return [item for sublist in result_pattern for item in sublist]


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

    def to_dict(self) -> dict[str, Any]:
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
        >>> _parse_key("Dmajor")
        2
    """
    # Remove quality suffixes (minor/major) - order matters!
    key_clean = key_str.replace("minor", "").replace("major", "")
    # Remove standalone "m" only if not part of note name (e.g., "Am" -> "A", but not "Dbm" -> "Db")
    if key_clean.endswith("m"):
        key_clean = key_clean[:-1]
    key_clean = key_clean.strip()

    if key_clean not in NOTE_NAMES:
        raise GenerationError(
            f"Invalid key: {key_str}",
            details={"key": key_str, "valid_keys": list(NOTE_NAMES.keys())},
        )

    return NOTE_NAMES[key_clean]


def _drum_pattern_to_tidal(
    template: dict[str, list[bool]],
    style: str,
    custom_samples: Optional[dict[str, str]] = None,
) -> str:
    """Convert drum pattern template to TidalCycles code.

    Args:
        template: Drum pattern with boolean lists for each instrument
        style: Style name for sample selection
        custom_samples: Optional custom sample map from library lookup

    Returns:
        TidalCycles pattern code
    """
    def pattern_to_string(pattern: list[bool], sound: str) -> str:
        """Convert boolean pattern to Tidal sound string."""
        result = []
        for hit in pattern:
            result.append(sound if hit else "~")
        return " ".join(result)

    # Default style-based sample choices
    default_sample_map = {
        "house": {"kick": "bd", "snare": "sd", "hh": "hh", "oh": "oh"},
        "techno": {"kick": "bd:3", "snare": "cp", "hh": "hc", "oh": "ho"},
        "breakbeat": {"kick": "bd:1", "snare": "sn:2", "hh": "hh:1", "oh": "oh:1"},
        "trap": {"kick": "808bd", "snare": "808sd", "hh": "808hh", "oh": "808oh"},
        "jazz": {"kick": "jazz:0", "snare": "jazz:1", "hh": "jazz:4", "oh": "jazz:5"},
        "minimal": {"kick": "bd:0", "snare": "sd:1", "hh": "hh:0", "oh": "oh:0"},
    }

    # Use custom samples if provided, otherwise fall back to style defaults
    if custom_samples:
        samples = custom_samples
    else:
        samples = default_sample_map.get(style, default_sample_map["house"])

    # Build multi-channel Tidal code
    lines = []
    lines.append(f'd1 $ sound "{pattern_to_string(template["kick"], samples["kick"])}"')
    lines.append(f'd2 $ sound "{pattern_to_string(template["snare"], samples["snare"])}"')
    lines.append(f'd3 $ sound "{pattern_to_string(template["hh"], samples["hh"])}"')
    if any(template["oh"]):
        lines.append(f'd4 $ sound "{pattern_to_string(template["oh"], samples["oh"])}"')

    return "\n".join(lines)


def _drum_pattern_to_supercollider(template: dict[str, list[bool]], style: str, bpm: float) -> str:
    """Convert drum pattern template to SuperCollider code.

    Args:
        template: Drum pattern with boolean lists for each instrument
        style: Style name
        bpm: Tempo in BPM

    Returns:
        SuperCollider Pdef code
    """
    def pattern_to_pseq(pattern: list[bool]) -> str:
        """Convert boolean pattern to Pseq values."""
        return ", ".join(["1" if hit else "Rest()" for hit in pattern])

    return f"""(
// {style.capitalize()} drum pattern at {bpm} BPM
Pdef(\\drums,
    Ppar([
        // Kick
        Pbind(
            \\instrument, \\default,
            \\midinote, 36,
            \\dur, Pseq([{pattern_to_pseq(template["kick"])}], inf) * 0.25,
            \\amp, 0.8,
        ),
        // Snare
        Pbind(
            \\instrument, \\default,
            \\midinote, 38,
            \\dur, Pseq([{pattern_to_pseq(template["snare"])}], inf) * 0.25,
            \\amp, 0.7,
        ),
        // Hi-hat
        Pbind(
            \\instrument, \\default,
            \\midinote, 42,
            \\dur, Pseq([{pattern_to_pseq(template["hh"])}], inf) * 0.25,
            \\amp, 0.5,
        ),
    ])
).play;
)"""


def generate_drums(
    style: str = "house",
    bpm: float = 120.0,
    bars: int = 4,
    temperature: float = 1.0,
    timeout: float = 30.0,
    seed: Optional[int] = None,
    sample_lookup: Optional["SampleLookup"] = None,
) -> Pattern:
    """Generate a drum pattern using algorithmic methods.

    Uses euclidean rhythms (Bjorklund's algorithm) and style-based templates
    for pattern generation. Patterns are deterministic when using the same seed.

    Styles: house, techno, breakbeat, trap, jazz, minimal

    Args:
        style: Drum style template to use
        bpm: Tempo in BPM
        bars: Number of bars to generate
        temperature: Randomness (0.0 = deterministic, 1.0 = default, >1.0 = more variation)
        timeout: Maximum generation time in seconds
        seed: Random seed for reproducibility
        sample_lookup: Optional SampleLookup interface for querying real sample IDs
            from the library. If provided, uses library samples instead of defaults.

    Returns:
        Generated drum pattern with MIDI, TidalCycles, and SuperCollider code

    Raises:
        GenerationError: If generation fails
        InferenceTimeoutError: If generation takes too long

    Example:
        >>> pattern = generate_drums(style="techno", bpm=130, bars=4, seed=42)
        >>> pattern.type
        'drums'
        >>> 'sound' in pattern.tidal_code
        True
    """
    if seed is not None:
        random.seed(seed)

    start_time = time.time()

    try:
        pattern_id = _generate_pattern_id()

        # Drum MIDI note mapping (General MIDI standard)
        KICK = 36
        SNARE = 38
        CLOSED_HH = 42
        OPEN_HH = 46
        CLAP = 39
        RIM = 37
        TOM_LOW = 41
        TOM_MID = 47
        TOM_HIGH = 50

        # Style templates using euclidean rhythms
        style_templates = {
            "house": {
                "kick": [i % 4 == 0 for i in range(16)],  # Four on floor
                "snare": [i in [4, 12] for i in range(16)],  # 2 and 4
                "hh": euclidean_rhythm(8, 16),  # 8th notes
                "oh": [i in [7, 15] for i in range(16)],  # Open hats
            },
            "techno": {
                "kick": [i % 4 == 0 for i in range(16)],  # Four on floor
                "snare": [i in [4, 12] for i in range(16)],  # 2 and 4
                "hh": [True] * 16,  # 16th notes
                "oh": [i % 8 == 7 for i in range(16)],
            },
            "breakbeat": {
                "kick": euclidean_rhythm(5, 16),  # Syncopated
                "snare": euclidean_rhythm(4, 16),
                "hh": euclidean_rhythm(11, 16),
                "oh": euclidean_rhythm(3, 16),
            },
            "trap": {
                "kick": [i in [0, 3, 6, 11] for i in range(16)],
                "snare": [i in [4, 12] for i in range(16)],
                "hh": [i % 2 == 1 for i in range(16)],  # Offbeat 16ths
                "oh": [False] * 16,
            },
            "jazz": {
                "kick": euclidean_rhythm(3, 16),
                "snare": euclidean_rhythm(5, 16),
                "hh": [i % 3 == 0 for i in range(16)],  # Triplet feel approximation
                "oh": [i in [7, 15] for i in range(16)],
            },
            "minimal": {
                "kick": euclidean_rhythm(4, 16),
                "snare": euclidean_rhythm(3, 16),
                "hh": euclidean_rhythm(7, 16),
                "oh": euclidean_rhythm(2, 16),
            },
        }

        template = style_templates.get(style, style_templates["house"])

        # Create MIDI file
        midi = MidiFile(ticks_per_beat=480)
        track = MidiTrack()
        midi.tracks.append(track)

        # Add tempo
        tempo = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

        # Add time signature (4/4)
        track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))

        step_ticks = 480 // 4  # 16th notes
        note_duration = step_ticks // 2  # Note duration (half a 16th)

        # Apply temperature-based randomization
        def should_play(pattern_val: bool) -> bool:
            if pattern_val:
                # Reduce probability of playing when temp < 1
                return random.random() < (1.0 - (1.0 - temperature) * 0.3)
            else:
                # Small chance to add note when temp > 1
                return random.random() < max(0, (temperature - 1.0) * 0.1)

        # Build complete list of MIDI events with absolute times
        events = []

        # Generate pattern for each bar
        for bar in range(bars):
            for step in range(16):
                step_start_time = (bar * 16 + step) * step_ticks

                # Kick
                if template["kick"][step] and should_play(template["kick"][step]):
                    velocity = random.randint(100, 127) if temperature > 0.5 else 110
                    events.append((step_start_time, 'note_on', KICK, velocity))
                    events.append((step_start_time + note_duration, 'note_off', KICK, 0))

                # Snare
                if template["snare"][step] and should_play(template["snare"][step]):
                    velocity = random.randint(90, 120) if temperature > 0.5 else 100
                    events.append((step_start_time, 'note_on', SNARE, velocity))
                    events.append((step_start_time + note_duration, 'note_off', SNARE, 0))

                # Closed hi-hat
                if template["hh"][step] and should_play(template["hh"][step]):
                    velocity = random.randint(60, 90) if temperature > 0.5 else 70
                    events.append((step_start_time, 'note_on', CLOSED_HH, velocity))
                    events.append((step_start_time + note_duration, 'note_off', CLOSED_HH, 0))

                # Open hi-hat
                if template["oh"][step] and should_play(template["oh"][step]):
                    velocity = random.randint(70, 100) if temperature > 0.5 else 80
                    events.append((step_start_time, 'note_on', OPEN_HH, velocity))
                    events.append((step_start_time + note_duration, 'note_off', OPEN_HH, 0))

        # Sort events by time
        events.sort(key=lambda e: e[0])

        # Convert absolute times to delta times and add to track
        last_time = 0
        for abs_time, msg_type, note, velocity in events:
            delta = abs_time - last_time
            track.append(Message(msg_type, note=note, velocity=velocity, time=delta))
            last_time = abs_time

        # Add end of track
        track.append(mido.MetaMessage('end_of_track', time=0))

        # Convert to bytes
        midi_buffer = BytesIO()
        midi.save(file=midi_buffer)
        midi_data = midi_buffer.getvalue()

        # Query library samples if sample_lookup provided
        custom_samples: Optional[dict[str, str]] = None
        if sample_lookup:
            # Query for drum samples by type
            kicks = sample_lookup.get_samples_by_type("bd", bpm=bpm, limit=1)
            snares = sample_lookup.get_samples_by_type("sn", bpm=bpm, limit=1)
            hats = sample_lookup.get_samples_by_type("hh", bpm=bpm, limit=1)
            open_hats = sample_lookup.get_samples_by_type("oh", bpm=bpm, limit=1)

            # Build sample map with library samples, falling back to defaults
            custom_samples = {
                "kick": kicks[0] if kicks else "bd",
                "snare": snares[0] if snares else "sd",
                "hh": hats[0] if hats else "hh",
                "oh": open_hats[0] if open_hats else "oh",
            }

        # Generate TidalCycles code
        tidal_code = _drum_pattern_to_tidal(template, style, custom_samples)

        # Generate SuperCollider code
        sc_code = _drum_pattern_to_supercollider(template, style, bpm)

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise InferenceTimeoutError(
                "Drum generation timed out",
                details={
                    "model": "algorithmic",
                    "timeout_seconds": timeout,
                    "elapsed": elapsed,
                },
            )

        return Pattern(
            pattern_id=pattern_id,
            pattern_type="drums",
            midi_data=midi_data,
            tidal_code=tidal_code,
            sc_code=sc_code,
            bpm=bpm,
            bars=bars,
            generation_method="algorithmic",
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
    seed: Optional[int] = None,
    sample_lookup: Optional["SampleLookup"] = None,
) -> Pattern:
    """Generate a melody using algorithmic composition.

    Uses random walk through scale degrees with temperature-based variation.
    Lower temperature produces smoother stepwise motion, higher temperature
    creates more intervallic jumps and rests.

    Keys: C, C#, D, D#, E, F, F#, G, G#, A, A#, B
    Scales: major, minor, dorian, mixolydian, pentatonic

    Args:
        key: Root note (e.g., "C", "F#", "Bbm")
        scale: Scale type (major, minor, dorian, mixolydian, pentatonic)
        bpm: Tempo in BPM
        bars: Number of bars to generate
        temperature: Randomness (0.0 = stepwise, 1.0 = balanced, >1.0 = jumpy with rests)
        timeout: Maximum generation time in seconds
        seed: Random seed for reproducibility
        sample_lookup: Optional SampleLookup interface for querying real sample IDs
            from the library. If provided, uses library synth/melodic samples.

    Returns:
        Generated melody pattern with MIDI, TidalCycles, and SuperCollider code

    Raises:
        GenerationError: If generation fails or invalid key/scale
        InferenceTimeoutError: If generation takes too long

    Example:
        >>> pattern = generate_melody(key="Am", scale="minor", bars=4, seed=42)
        >>> pattern.key
        'A'
        >>> pattern.scale
        'minor'
    """
    if seed is not None:
        random.seed(seed)

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

        # Get scale intervals
        scale_intervals = SCALES[scale]
        octave = 4  # Middle octave
        base_note = root_pitch + octave * 12

        # Generate melodic pattern based on temperature
        num_notes = 16 * bars  # 16th notes per bar

        # Create melodic contour
        melody_notes = []
        current_degree = 0  # Start on root

        for i in range(num_notes):
            # Determine note duration (more variation at higher temperature)
            if temperature > 1.0 and random.random() < 0.3:
                # Skip note (rest)
                melody_notes.append(None)
                continue

            # Random walk through scale degrees
            if temperature < 0.5:
                # Stay close to current degree
                step = random.choice([-1, 0, 0, 1])
            elif temperature < 1.0:
                # More stepwise motion
                step = random.choice([-2, -1, 0, 1, 2])
            else:
                # More jumps
                step = random.choice([-3, -2, -1, 0, 1, 2, 3])

            current_degree = (current_degree + step) % len(scale_intervals)

            # Convert scale degree to MIDI note
            interval = scale_intervals[current_degree]
            octave_offset = 0
            if current_degree + step < 0:
                octave_offset = -12
            elif current_degree + step >= len(scale_intervals):
                octave_offset = 12

            midi_note = base_note + interval + octave_offset
            melody_notes.append(midi_note)

        # Create MIDI file
        midi = MidiFile(ticks_per_beat=480)
        track = MidiTrack()
        midi.tracks.append(track)

        # Add tempo
        tempo = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

        # Add notes
        step_ticks = 480 // 4  # 16th notes
        time_since_last = 0

        for note in melody_notes:
            if note is None:
                # Rest
                time_since_last += step_ticks
            else:
                # Note on
                velocity = random.randint(80, 110) if temperature > 0.5 else 90
                track.append(Message('note_on', note=note, velocity=velocity, time=time_since_last))
                # Note off after 1/16 note
                track.append(Message('note_off', note=note, velocity=0, time=step_ticks // 2))
                time_since_last = step_ticks // 2

        # Add end of track
        track.append(mido.MetaMessage('end_of_track', time=0))

        # Convert to bytes
        midi_buffer = BytesIO()
        midi.save(file=midi_buffer)
        midi_data = midi_buffer.getvalue()

        # Query library samples for synth/melodic sounds if available
        synth_sample = "superpiano"  # Default
        if sample_lookup:
            # Try to find synth or melodic samples
            synth_samples = sample_lookup.get_samples_by_type("synth", bpm=bpm, limit=1)
            if not synth_samples:
                synth_samples = sample_lookup.get_samples_by_type("keys", bpm=bpm, limit=1)
            if not synth_samples:
                synth_samples = sample_lookup.get_samples_by_type("lead", bpm=bpm, limit=1)
            if synth_samples:
                synth_sample = synth_samples[0]

        # Create TidalCycles code
        key_clean = key.replace("minor", "").replace("m", "").strip()
        note_pattern = " ".join([str(n - base_note) if n is not None else "~" for n in melody_notes[:16]])
        tidal_code = f'd1 $ n "{note_pattern}" # s "{synth_sample}" # scale "{scale}"'

        # Create SuperCollider code
        midi_notes_str = ", ".join([str(n) if n is not None else "Rest()" for n in melody_notes[:16]])
        sc_code = f"""(
Pdef(\\melody,
    Pbind(
        \\instrument, \\default,
        \\midinote, Pseq([{midi_notes_str}], inf),
        \\dur, 0.25,
        \\amp, 0.6,
    )
).play;
)"""

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise InferenceTimeoutError(
                "Melody generation timed out",
                details={
                    "model": "algorithmic",
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
            generation_method="algorithmic",
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
    seed: Optional[int] = None,
    sample_lookup: Optional["SampleLookup"] = None,
) -> Pattern:
    """Generate a bassline using algorithmic composition.

    Uses style-based interval patterns (root, fifth, octave, etc.) to create
    musically appropriate bass lines. Each style has its own characteristic pattern.

    Styles:
        - synth: Simple root/fifth pattern (electronic music)
        - acoustic: Walking motion through chord tones
        - walking: Jazz-style stepwise motion
        - slap: Funky root emphasis with octave jumps

    Args:
        key: Root note (e.g., "C", "F#", "Bbm")
        bpm: Tempo in BPM
        bars: Number of bars to generate
        style: Bass style template (synth, acoustic, walking, slap)
        timeout: Maximum generation time in seconds
        seed: Random seed for reproducibility
        sample_lookup: Optional SampleLookup interface for querying real sample IDs
            from the library. If provided, uses library bass samples.

    Returns:
        Generated bass pattern with MIDI, TidalCycles, and SuperCollider code

    Raises:
        GenerationError: If generation fails
        InferenceTimeoutError: If generation takes too long

    Example:
        >>> pattern = generate_bass(key="F#", style="synth", bars=4, seed=42)
        >>> pattern.type
        'bass'
        >>> pattern.key
        'F#'
    """
    if seed is not None:
        random.seed(seed)

    start_time = time.time()

    try:
        # Parse key
        root_pitch = _parse_key(key)

        pattern_id = _generate_pattern_id()

        # Bass octave
        octave = 2
        base_note = root_pitch + octave * 12

        # Common bass intervals
        root = 0
        minor_third = 3
        fourth = 5
        fifth = 7
        octave_up = 12

        # Style-based patterns (intervals from root)
        style_patterns = {
            "synth": [root, root, fifth, fifth, root, root, fifth, fifth] * bars,
            "acoustic": [root, fifth, octave_up, fifth, root, fourth, fifth, root] * bars,
            "walking": [root, minor_third, fourth, fifth, fifth, fourth, minor_third, root] * bars,
            "slap": [root, root, root, fifth, root, root, octave_up, fifth] * bars,
        }

        pattern = style_patterns.get(style, style_patterns["synth"])
        bass_notes = [base_note + interval for interval in pattern]

        # Create MIDI file
        midi = MidiFile(ticks_per_beat=480)
        track = MidiTrack()
        midi.tracks.append(track)

        # Add tempo
        tempo = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

        # Add notes (8th notes)
        step_ticks = 480 // 2  # 8th notes
        time_since_last = 0

        for note in bass_notes:
            velocity = random.randint(90, 110)
            track.append(Message('note_on', note=note, velocity=velocity, time=time_since_last))
            track.append(Message('note_off', note=note, velocity=0, time=step_ticks // 2))
            time_since_last = step_ticks // 2

        # Add end of track
        track.append(mido.MetaMessage('end_of_track', time=0))

        # Convert to bytes
        midi_buffer = BytesIO()
        midi.save(file=midi_buffer)
        midi_data = midi_buffer.getvalue()

        # Query library samples for bass sounds if available
        bass_sample = "bass1"  # Default
        if sample_lookup:
            bass_samples = sample_lookup.get_samples_by_type("bass", bpm=bpm, limit=1)
            if not bass_samples:
                bass_samples = sample_lookup.get_samples_by_type("sub", bpm=bpm, limit=1)
            if bass_samples:
                bass_sample = bass_samples[0]

        # Create TidalCycles code
        key_clean = key.replace("minor", "").replace("m", "").strip()
        note_pattern = " ".join([str(n - base_note) for n in bass_notes[:8]])
        tidal_code = f'd1 $ n "{note_pattern}" # s "{bass_sample}" # octave 2'

        # Create SuperCollider code
        midi_notes_str = ", ".join([str(n) for n in bass_notes[:8]])
        sc_code = f"""(
Pdef(\\bass,
    Pbind(
        \\instrument, \\default,
        \\midinote, Pseq([{midi_notes_str}], inf),
        \\dur, 0.5,
        \\amp, 0.7,
    )
).play;
)"""

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise InferenceTimeoutError(
                "Bass generation timed out",
                details={
                    "model": "algorithmic",
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
            generation_method="algorithmic",
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
    """Add human-like timing and velocity variations to a pattern.

    Applies subtle randomization to note timing (±amount*5% of beat) and velocity
    (±amount*20 MIDI units) to create more natural, less mechanical sounding patterns.

    Args:
        pattern: Pattern to humanize
        amount: Humanization strength (0.0 = no change, 1.0 = maximum variation)

    Returns:
        New pattern with timing and velocity variations applied

    Example:
        >>> original = generate_drums(style="techno", seed=42)
        >>> humanized = humanize(original, amount=0.3)
        >>> humanized.parent_ids
        [original.id]
        >>> humanized.generation_method
        'humanized'
    """
    new_id = _generate_pattern_id()

    # Load MIDI file from bytes
    midi_buffer = BytesIO(pattern.midi_data)
    midi = MidiFile(file=midi_buffer)

    # Create new MIDI file with humanized timing
    new_midi = MidiFile(ticks_per_beat=midi.ticks_per_beat)

    for track in midi.tracks:
        new_track = MidiTrack()
        new_midi.tracks.append(new_track)

        for msg in track:
            if msg.type in ('note_on', 'note_off'):
                # Randomize timing by ±amount * 5% of a beat
                max_timing_shift = int(midi.ticks_per_beat * 0.05 * amount)
                timing_shift = random.randint(-max_timing_shift, max_timing_shift)
                new_time = max(0, msg.time + timing_shift)

                # Randomize velocity for note_on messages
                if msg.type == 'note_on' and msg.velocity > 0:
                    max_velocity_shift = int(20 * amount)
                    velocity_shift = random.randint(-max_velocity_shift, max_velocity_shift)
                    new_velocity = max(1, min(127, msg.velocity + velocity_shift))
                    new_msg = msg.copy(time=new_time, velocity=new_velocity)
                else:
                    new_msg = msg.copy(time=new_time)

                new_track.append(new_msg)
            else:
                # Keep non-note messages unchanged
                new_track.append(msg.copy())

    # Convert back to bytes
    output_buffer = BytesIO()
    new_midi.save(file=output_buffer)
    new_midi_data = output_buffer.getvalue()

    # Type assertion: we know pattern.type is one of the valid literals
    from typing import cast
    pattern_type = cast(Literal["drums", "melody", "bass"], pattern.type)

    return Pattern(
        pattern_id=new_id,
        pattern_type=pattern_type,
        midi_data=new_midi_data,
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
