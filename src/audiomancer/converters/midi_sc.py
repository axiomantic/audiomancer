"""MIDI to SuperCollider conversion.

This module provides bidirectional conversion between MIDI and SuperCollider
Pbind patterns.
"""

import io
import math
import re
from typing import Literal, Optional

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False


def midi_to_freq(note: int) -> float:
    """Convert MIDI note number to frequency in Hz.

    Args:
        note: MIDI note number (0-127)

    Returns:
        Frequency in Hz

    Example:
        >>> midi_to_freq(69)  # A4
        440.0
        >>> midi_to_freq(60)  # C4
        261.63
    """
    return 440.0 * (2 ** ((note - 69) / 12))


def freq_to_midi(freq: float) -> int:
    """Convert frequency to nearest MIDI note.

    Args:
        freq: Frequency in Hz

    Returns:
        MIDI note number (0-127)

    Example:
        >>> freq_to_midi(440.0)
        69
        >>> freq_to_midi(261.63)
        60
    """
    return int(round(69 + 12 * math.log2(freq / 440.0)))


def quantize_time(time: float, grid: float = 0.25) -> float:
    """Quantize time to grid (in beats).

    Args:
        time: Time in beats
        grid: Grid size in beats (0.25 = 16th note)

    Returns:
        Quantized time

    Example:
        >>> quantize_time(0.23, grid=0.25)
        0.25
        >>> quantize_time(1.1, grid=0.5)
        1.0
    """
    return round(time / grid) * grid


def midi_to_supercollider(
    midi_data: bytes,
    synth_name: str = "default",
    bpm: float = 120.0,
    output_format: Literal["pbind", "routine", "pattern"] = "pbind",
) -> str:
    """Convert MIDI to SuperCollider code.

    Formats:
    - pbind: Pbind pattern (most common)
    - routine: Routine with explicit timing
    - pattern: Pdef pattern definition

    Args:
        midi_data: Raw MIDI bytes
        synth_name: SuperCollider synth name
        bpm: Tempo (used for timing calculations)
        output_format: Output format type

    Returns:
        SuperCollider code string

    Example:
        >>> sc_code = midi_to_supercollider(midi_bytes, synth_name="tb303")
        >>> print(sc_code)
        Pbind(
            \\instrument, \\tb303,
            \\dur, Pseq([0.25, 0.25, 0.5, 0.25], 1),
            \\freq, Pseq([261.63, 293.66, 329.63, 349.23], 1),
            \\amp, Pseq([0.8, 0.6, 0.9, 0.7], 1)
        ).play;
    """
    if not MIDO_AVAILABLE:
        # Fallback if mido not available
        return f'Pbind(\\instrument, \\{synth_name}).play;'

    try:
        mid = mido.MidiFile(file=io.BytesIO(midi_data))

        # Extract notes with timing
        notes = []
        current_time = 0.0
        ticks_per_beat = mid.ticks_per_beat
        active_notes = {}  # Track note_on events waiting for note_off

        for track in mid.tracks:
            current_time = 0.0
            for msg in track:
                current_time += msg.time / ticks_per_beat

                if msg.type == 'note_on' and msg.velocity > 0:
                    # Store note_on event
                    note_key = msg.note
                    active_notes[note_key] = {
                        'time': current_time,
                        'note': msg.note,
                        'velocity': msg.velocity / 127.0,
                    }
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    # Find matching note_on
                    note_key = msg.note
                    if note_key in active_notes:
                        note_data = active_notes[note_key]
                        duration = current_time - note_data['time']
                        notes.append({
                            'time': note_data['time'],
                            'note': note_data['note'],
                            'velocity': note_data['velocity'],
                            'duration': max(duration, 0.01),  # Minimum 10ms
                        })
                        del active_notes[note_key]

        # Close any remaining notes (no note_off received)
        for note_data in active_notes.values():
            notes.append({
                'time': note_data['time'],
                'note': note_data['note'],
                'velocity': note_data['velocity'],
                'duration': 0.25,  # Default quarter note
            })

        # Sort notes by time
        notes.sort(key=lambda n: n['time'])

        # Convert to SuperCollider based on output format
        if output_format == "pbind":
            return _to_pbind(notes, synth_name, bpm)
        elif output_format == "routine":
            return _to_routine(notes, synth_name, bpm)
        else:
            return _to_pdef(notes, synth_name, bpm)

    except Exception:
        # Fallback to simple pattern
        return f'Pbind(\\instrument, \\{synth_name}).play;'


def _to_pbind(notes: list, synth_name: str, bpm: float) -> str:
    """Generate Pbind code.

    Args:
        notes: List of note dictionaries
        synth_name: Synth name
        bpm: Tempo

    Returns:
        Pbind code string
    """
    if not notes:
        return f'Pbind(\\instrument, \\{synth_name}).play;'

    # Calculate durations between consecutive notes
    durations = []
    freqs = []
    amps = []
    legatos = []

    for i, note in enumerate(notes):
        # Duration until next note (or use note duration for last note)
        if i < len(notes) - 1:
            dur = notes[i + 1]['time'] - note['time']
        else:
            dur = note['duration']

        # Ensure minimum duration
        dur = max(dur, 0.01)

        durations.append(dur)
        freqs.append(midi_to_freq(note['note']))
        amps.append(note['velocity'])

        # Legato: how much of the duration the note actually sounds
        legato = min(note['duration'] / dur, 1.0)
        legatos.append(legato)

    # Format as SuperCollider arrays
    dur_str = ", ".join(f"{d:.4f}" for d in durations)
    freq_str = ", ".join(f"{f:.2f}" for f in freqs)
    amp_str = ", ".join(f"{a:.3f}" for a in amps)
    legato_str = ", ".join(f"{l:.3f}" for l in legatos)

    return f'''Pbind(
    \\instrument, \\{synth_name},
    \\dur, Pseq([{dur_str}], 1),
    \\freq, Pseq([{freq_str}], 1),
    \\amp, Pseq([{amp_str}], 1),
    \\legato, Pseq([{legato_str}], 1)
).play;'''


def _to_routine(notes: list, synth_name: str, bpm: float) -> str:
    """Generate Routine code with explicit timing.

    Args:
        notes: List of note dictionaries
        synth_name: Synth name
        bpm: Tempo

    Returns:
        Routine code string
    """
    if not notes:
        return f'Routine({{ }}).play;'

    lines = ['Routine({']

    for i, note in enumerate(notes):
        freq = midi_to_freq(note['note'])
        amp = note['velocity']
        dur = note['duration']

        # Play synth
        lines.append(f'    Synth(\\{synth_name}, [\\freq, {freq:.2f}, \\amp, {amp:.3f}, \\sustain, {dur:.4f}]);')

        # Wait until next note
        if i < len(notes) - 1:
            wait_time = notes[i + 1]['time'] - note['time']
            lines.append(f'    {wait_time:.4f}.wait;')

    lines.append('}).play;')
    return '\n'.join(lines)


def _to_pdef(notes: list, synth_name: str, bpm: float) -> str:
    """Generate Pdef pattern definition.

    Args:
        notes: List of note dictionaries
        synth_name: Synth name
        bpm: Tempo

    Returns:
        Pdef code string
    """
    if not notes:
        return f'Pdef(\\midi_pattern, Pbind(\\instrument, \\{synth_name}));'

    # Calculate durations between consecutive notes
    durations = []
    freqs = []
    amps = []

    for i, note in enumerate(notes):
        if i < len(notes) - 1:
            dur = notes[i + 1]['time'] - note['time']
        else:
            dur = note['duration']

        dur = max(dur, 0.01)
        durations.append(dur)
        freqs.append(midi_to_freq(note['note']))
        amps.append(note['velocity'])

    # Format arrays
    dur_str = ", ".join(f"{d:.4f}" for d in durations)
    freq_str = ", ".join(f"{f:.2f}" for f in freqs)
    amp_str = ", ".join(f"{a:.3f}" for a in amps)

    return f'''Pdef(\\midi_pattern,
    Pbind(
        \\instrument, \\{synth_name},
        \\dur, Pseq([{dur_str}], inf),
        \\freq, Pseq([{freq_str}], inf),
        \\amp, Pseq([{amp_str}], inf)
    )
);'''


def supercollider_to_midi(
    sc_code: str,
    bpm: float = 120.0,
) -> bytes:
    """Convert SuperCollider Pbind to MIDI.

    Parses Pseq arrays to extract note data.

    Args:
        sc_code: SuperCollider Pbind code
        bpm: Tempo for MIDI output

    Returns:
        MIDI data as bytes

    Example:
        >>> sc_code = 'Pbind(\\\\freq, Pseq([440, 880], 1)).play;'
        >>> midi = supercollider_to_midi(sc_code, bpm=120)
    """
    if not MIDO_AVAILABLE:
        # Return minimal MIDI if mido not available
        return b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0"

    try:
        # Parse freq/dur/amp Pseq arrays
        freq_match = re.search(r'\\freq,\s*Pseq\(\[([^\]]+)\]', sc_code)
        dur_match = re.search(r'\\dur,\s*Pseq\(\[([^\]]+)\]', sc_code)
        amp_match = re.search(r'\\amp,\s*Pseq\(\[([^\]]+)\]', sc_code)
        midinote_match = re.search(r'\\midinote,\s*Pseq\(\[([^\]]+)\]', sc_code)

        # Extract values
        if freq_match:
            freqs = [float(x.strip()) for x in freq_match.group(1).split(',')]
            notes = [freq_to_midi(f) for f in freqs]
        elif midinote_match:
            notes = [int(float(x.strip())) for x in midinote_match.group(1).split(',')]
        else:
            # Fallback: single middle C
            notes = [60]

        if dur_match:
            durs = [float(x.strip()) for x in dur_match.group(1).split(',')]
        else:
            # Default quarter notes
            durs = [0.25] * len(notes)

        if amp_match:
            amps = [float(x.strip()) for x in amp_match.group(1).split(',')]
        else:
            # Default velocity
            amps = [0.8] * len(notes)

        # Ensure all arrays same length
        max_len = max(len(notes), len(durs), len(amps))
        while len(notes) < max_len:
            notes.append(notes[-1] if notes else 60)
        while len(durs) < max_len:
            durs.append(durs[-1] if durs else 0.25)
        while len(amps) < max_len:
            amps.append(amps[-1] if amps else 0.8)

        # Create MIDI file
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        # Set tempo
        tempo_microseconds = int(60_000_000 / bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo_microseconds))

        # Convert to MIDI notes
        ticks_per_beat = 480
        current_ticks = 0

        for note, dur, amp in zip(notes, durs, amps):
            # Clamp MIDI note to valid range
            note = max(0, min(127, note))
            velocity = int(amp * 127)
            velocity = max(1, min(127, velocity))

            # Note on
            track.append(mido.Message(
                'note_on',
                note=note,
                velocity=velocity,
                time=current_ticks,
            ))

            # Note duration in ticks
            dur_ticks = int(dur * ticks_per_beat)

            # Note off
            track.append(mido.Message(
                'note_off',
                note=note,
                velocity=0,
                time=dur_ticks,
            ))

            current_ticks = 0  # Time is relative to previous message

        # Add end of track
        track.append(mido.MetaMessage('end_of_track', time=0))

        # Convert to bytes
        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        return bytes_io.getvalue()

    except Exception:
        # Fallback: minimal MIDI
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
        track.append(mido.MetaMessage('end_of_track', time=0))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        return bytes_io.getvalue()
