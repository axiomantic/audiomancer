#!/usr/bin/env python3
"""Example demonstrating MIDI to SuperCollider conversion.

This example shows how to:
1. Create a simple MIDI pattern
2. Convert it to SuperCollider Pbind
3. Convert SuperCollider code back to MIDI
4. Use different output formats (Pbind, Routine, Pdef)
"""

import mido
import io
from audiomancer.converters.midi_sc import (
    midi_to_supercollider,
    supercollider_to_midi,
    midi_to_freq,
    freq_to_midi,
)


def create_simple_melody():
    """Create a simple MIDI melody: C D E F G."""
    midi = mido.MidiFile()
    track = mido.MidiTrack()
    midi.tracks.append(track)

    # Set tempo to 120 BPM
    track.append(mido.MetaMessage('set_tempo', tempo=500000))

    # Notes: C4, D4, E4, F4, G4
    notes = [60, 62, 64, 65, 67]

    for note in notes:
        track.append(mido.Message('note_on', note=note, velocity=100, time=0))
        track.append(mido.Message('note_off', note=note, velocity=0, time=480))  # Quarter note

    # Convert to bytes
    bytes_io = io.BytesIO()
    midi.save(file=bytes_io)
    return bytes_io.getvalue()


def create_acid_bassline():
    """Create a simple TB-303 style bassline."""
    midi = mido.MidiFile()
    track = mido.MidiTrack()
    midi.tracks.append(track)

    track.append(mido.MetaMessage('set_tempo', tempo=428571))  # ~140 BPM

    # Acid pattern: root, octave, fifth, octave, third, root, fifth, root
    notes = [36, 48, 43, 48, 40, 36, 43, 36]
    velocities = [127, 80, 100, 80, 90, 127, 100, 127]

    for note, vel in zip(notes, velocities):
        track.append(mido.Message('note_on', note=note, velocity=vel, time=0))
        track.append(mido.Message('note_off', note=note, velocity=0, time=120))  # 16th note

    bytes_io = io.BytesIO()
    midi.save(file=bytes_io)
    return bytes_io.getvalue()


def main():
    print("MIDI to SuperCollider Conversion Examples")
    print("=" * 50)
    print()

    # Example 1: Simple melody as Pbind
    print("1. Simple Melody → Pbind")
    print("-" * 50)
    melody_midi = create_simple_melody()
    pbind_code = midi_to_supercollider(
        melody_midi,
        synth_name="default",
        output_format="pbind"
    )
    print(pbind_code)
    print()

    # Example 2: Acid bassline for TB-303
    print("2. Acid Bassline → TB-303 Pbind")
    print("-" * 50)
    bass_midi = create_acid_bassline()
    tb303_code = midi_to_supercollider(
        bass_midi,
        synth_name="tb303",
        output_format="pbind"
    )
    print(tb303_code)
    print()

    # Example 3: Same bassline as Routine
    print("3. Acid Bassline → Routine")
    print("-" * 50)
    routine_code = midi_to_supercollider(
        bass_midi,
        synth_name="tb303",
        output_format="routine"
    )
    print(routine_code)
    print()

    # Example 4: Same bassline as Pdef
    print("4. Acid Bassline → Pdef Pattern")
    print("-" * 50)
    pdef_code = midi_to_supercollider(
        bass_midi,
        synth_name="tb303",
        output_format="pattern"
    )
    print(pdef_code)
    print()

    # Example 5: SuperCollider → MIDI round-trip
    print("5. SuperCollider → MIDI Round-Trip")
    print("-" * 50)
    sc_code = '''Pbind(
    \\instrument, \\default,
    \\freq, Pseq([261.63, 293.66, 329.63, 349.23], 1),
    \\dur, Pseq([0.25, 0.25, 0.25, 0.25], 1),
    \\amp, Pseq([0.8, 0.8, 0.8, 0.8], 1)
).play;'''

    print("Original SuperCollider code:")
    print(sc_code)
    print()

    # Convert to MIDI
    midi_bytes = supercollider_to_midi(sc_code, bpm=120.0)
    print(f"Converted to MIDI: {len(midi_bytes)} bytes")

    # Parse and show notes
    midi_file = mido.MidiFile(file=io.BytesIO(midi_bytes))
    print("MIDI notes:")
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                freq = midi_to_freq(msg.note)
                print(f"  Note {msg.note} ({freq:.2f} Hz) velocity {msg.velocity}")
    print()

    # Example 6: Utility functions
    print("6. Utility Functions")
    print("-" * 50)
    print(f"MIDI 60 (C4) = {midi_to_freq(60):.2f} Hz")
    print(f"MIDI 69 (A4) = {midi_to_freq(69):.2f} Hz")
    print(f"440 Hz = MIDI {freq_to_midi(440.0)}")
    print(f"261.63 Hz = MIDI {freq_to_midi(261.63)}")
    print()


if __name__ == "__main__":
    main()
