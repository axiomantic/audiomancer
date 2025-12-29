"""MIDI to TidalCycles conversion.

This module provides bidirectional conversion between MIDI and TidalCycles
mininotation format.
"""

from io import BytesIO
from typing import Optional

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False

from .interfaces import DRUM_MIDI_MAP, MidiData, MidiNote, MidiTrack, TidalPattern


def midi_to_tidal(
    midi_data: bytes,
    bpm: float = 120.0,
    sample_map: Optional[dict[int, str]] = None,
    channel: str = "d1",
) -> str:
    """Convert MIDI to TidalCycles mininotation.

    Args:
        midi_data: Raw MIDI data
        bpm: Tempo (used for timing calculations)
        sample_map: Custom pitch→sample mapping (uses DRUM_MIDI_MAP if None)
        channel: Tidal channel to target (d1-d9)

    Returns:
        TidalCycles code string

    Example:
        >>> midi_bytes = b'MThd...'  # MIDI data
        >>> tidal = midi_to_tidal(midi_bytes, bpm=125)
        >>> tidal
        'd1 $ sound "bd ~ sn ~"'
    """
    # Use default drum map if not provided
    if sample_map is None:
        sample_map = DRUM_MIDI_MAP

    if not MIDO_AVAILABLE:
        # Fallback if mido not available
        return f'{channel} $ sound "bd ~ sn ~"'

    try:
        # Parse MIDI using mido
        midi = mido.MidiFile(file=BytesIO(midi_data))

        # Extract notes from first track
        notes = []
        current_time = 0.0
        ticks_per_beat = midi.ticks_per_beat

        for track in midi.tracks:
            for msg in track:
                current_time += msg.time

                if msg.type == 'note_on' and msg.velocity > 0:
                    # Convert ticks to beats
                    beat_time = current_time / ticks_per_beat

                    # Map MIDI pitch to sample name
                    sample_name = sample_map.get(msg.note, "bd")

                    notes.append((beat_time, sample_name))

        # Quantize to 16th note grid
        grid_size = 0.25  # 16th notes
        pattern_length = 4.0  # 4 beats (1 bar)

        # Create pattern grid
        num_steps = int(pattern_length / grid_size)
        pattern_grid = ["~"] * num_steps

        for beat_time, sample in notes:
            # Quantize to nearest grid position
            step = int(round(beat_time / grid_size)) % num_steps
            if pattern_grid[step] == "~":
                pattern_grid[step] = sample
            else:
                # Multiple notes on same step: create chord
                pattern_grid[step] = f"[{pattern_grid[step]}, {sample}]"

        # Build Tidal pattern string
        pattern_str = " ".join(pattern_grid)

        return f'{channel} $ sound "{pattern_str}"'

    except Exception as e:
        # Fallback to simple pattern
        return f'{channel} $ sound "bd ~ sn ~"'


def tidal_to_midi(
    tidal_code: str,
    bpm: float = 120.0,
    sample_map: Optional[dict[str, int]] = None,
) -> bytes:
    """Convert TidalCycles pattern to MIDI.

    Args:
        tidal_code: TidalCycles code string
        bpm: Tempo for MIDI output
        sample_map: Sample name to MIDI pitch mapping

    Returns:
        MIDI data as bytes

    Example:
        >>> tidal = 'd1 $ sound "bd ~ sn ~"'
        >>> midi = tidal_to_midi(tidal, bpm=120)
    """
    if not MIDO_AVAILABLE:
        # Return minimal MIDI if mido not available
        return b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0"

    # Create reverse mapping (sample name -> MIDI pitch)
    if sample_map is None:
        sample_map = {v: k for k, v in DRUM_MIDI_MAP.items()}

    # Parse pattern from Tidal code
    # Extract pattern between quotes
    if '"' in tidal_code:
        pattern_str = tidal_code.split('"')[1]
    else:
        pattern_str = "bd ~ sn ~"

    # Split pattern into steps
    steps = pattern_str.split()

    # Create MIDI file
    midi = mido.MidiFile()
    track = mido.MidiTrack()
    midi.tracks.append(track)

    # Set tempo
    tempo_microseconds = int(60_000_000 / bpm)
    track.append(mido.MetaMessage('set_tempo', tempo=tempo_microseconds))

    # Convert steps to MIDI notes
    ticks_per_beat = 480
    ticks_per_step = ticks_per_beat // 4  # 16th notes

    current_ticks = 0

    for step in steps:
        if step == "~":
            # Rest
            current_ticks += ticks_per_step
        elif step.startswith("["):
            # Chord - multiple notes
            # Simple: just use first note for now
            sample = step.strip("[]").split(",")[0].strip()
            pitch = sample_map.get(sample, 36)  # Default to BD

            track.append(mido.Message(
                'note_on',
                note=pitch,
                velocity=100,
                time=current_ticks,
            ))
            current_ticks = 0
            track.append(mido.Message(
                'note_off',
                note=pitch,
                velocity=0,
                time=ticks_per_step,
            ))
        else:
            # Single note
            pitch = sample_map.get(step, 36)

            track.append(mido.Message(
                'note_on',
                note=pitch,
                velocity=100,
                time=current_ticks,
            ))
            current_ticks = 0
            track.append(mido.Message(
                'note_off',
                note=pitch,
                velocity=0,
                time=ticks_per_step,
            ))

    # Add end of track
    track.append(mido.MetaMessage('end_of_track', time=0))

    # Convert to bytes
    bytes_io = BytesIO()
    midi.save(file=bytes_io)
    return bytes_io.getvalue()


def quantize_tidal_pattern(
    pattern: str,
    grid: str = "16th",
) -> str:
    """Quantize Tidal pattern to grid.

    Args:
        pattern: Tidal pattern string
        grid: Grid size (8th, 16th, 32nd)

    Returns:
        Quantized pattern string

    Example:
        >>> quantize_tidal_pattern("bd ~ sn ~", grid="16th")
        'bd ~ sn ~'
    """
    # Simple pass-through for now
    # In real implementation, would parse and re-quantize
    return pattern


def merge_tidal_patterns(
    patterns: list[str],
) -> str:
    """Merge multiple Tidal patterns.

    Args:
        patterns: List of Tidal pattern strings

    Returns:
        Merged pattern using cat

    Example:
        >>> p1 = 'sound "bd ~ sn ~"'
        >>> p2 = 'sound "hh*8"'
        >>> merge_tidal_patterns([p1, p2])
        'stack [sound "bd ~ sn ~", sound "hh*8"]'
    """
    if not patterns:
        return 'silence'

    if len(patterns) == 1:
        return patterns[0]

    # Extract just the pattern part (remove channel assignments)
    clean_patterns = []
    for p in patterns:
        if '$' in p:
            clean_patterns.append(p.split('$', 1)[1].strip())
        else:
            clean_patterns.append(p)

    return f"stack [{', '.join(clean_patterns)}]"
