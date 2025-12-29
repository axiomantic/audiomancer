"""Tests for MIDI to SuperCollider conversion."""

import io
import pytest

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False

from audiomancer.converters.midi_sc import (
    midi_to_supercollider,
    supercollider_to_midi,
    midi_to_freq,
    freq_to_midi,
    quantize_time,
)


pytestmark = pytest.mark.skipif(not MIDO_AVAILABLE, reason="mido not installed")


class TestMidiToSupercollider:
    """Tests for converting MIDI to SuperCollider."""

    def test_simple_midi_to_pbind(self):
        """Test converting simple MIDI to Pbind."""
        # Create minimal MIDI file
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        # Add tempo
        track.append(mido.MetaMessage('set_tempo', tempo=500000))  # 120 BPM

        # Add middle C
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))  # 1 beat

        # Add E
        track.append(mido.Message('note_on', note=64, velocity=80, time=0))
        track.append(mido.Message('note_off', note=64, velocity=0, time=480))

        # Convert to bytes
        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Convert to SuperCollider
        sc_code = midi_to_supercollider(midi_bytes, synth_name="default", output_format="pbind")

        # Verify structure
        assert 'Pbind(' in sc_code
        assert '\\instrument, \\default' in sc_code
        assert '\\freq, Pseq([' in sc_code
        assert '\\dur, Pseq([' in sc_code
        assert '\\amp, Pseq([' in sc_code
        assert '.play;' in sc_code

    def test_midi_to_routine(self):
        """Test converting MIDI to Routine."""
        # Create minimal MIDI
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Convert to Routine
        sc_code = midi_to_supercollider(midi_bytes, synth_name="tb303", output_format="routine")

        # Verify structure
        assert 'Routine({' in sc_code
        assert 'Synth(\\tb303' in sc_code
        assert '.wait;' in sc_code or '}).play;' in sc_code

    def test_midi_to_pdef(self):
        """Test converting MIDI to Pdef."""
        # Create minimal MIDI
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Convert to Pdef
        sc_code = midi_to_supercollider(midi_bytes, synth_name="default", output_format="pattern")

        # Verify structure
        assert 'Pdef(\\midi_pattern' in sc_code
        assert 'Pbind(' in sc_code
        assert '\\instrument, \\default' in sc_code

    def test_midi_with_custom_synth(self):
        """Test MIDI conversion with custom synth name."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Custom synth
        sc_code = midi_to_supercollider(midi_bytes, synth_name="tb303")

        assert '\\instrument, \\tb303' in sc_code

    def test_polyphonic_midi(self):
        """Test handling of polyphonic MIDI (simultaneous notes)."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))

        # Chord: C + E + G
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_on', note=64, velocity=100, time=0))
        track.append(mido.Message('note_on', note=67, velocity=100, time=0))

        # Release all
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))
        track.append(mido.Message('note_off', note=64, velocity=0, time=0))
        track.append(mido.Message('note_off', note=67, velocity=0, time=0))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        sc_code = midi_to_supercollider(midi_bytes)

        # Should contain multiple frequencies
        assert 'Pseq([' in sc_code
        # For polyphonic content, will generate sequential events

    def test_empty_midi(self):
        """Test handling of empty MIDI file."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage('end_of_track', time=0))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        sc_code = midi_to_supercollider(midi_bytes)

        # Should produce valid (if minimal) code
        assert 'Pbind(' in sc_code
        assert '.play;' in sc_code

    def test_midi_fallback_on_error(self):
        """Test fallback for invalid MIDI data."""
        invalid_midi = b"not_a_midi_file"

        sc_code = midi_to_supercollider(invalid_midi)

        # Should fallback gracefully
        assert 'Pbind(' in sc_code
        assert '\\instrument' in sc_code


class TestSupercolliderToMidi:
    """Tests for converting SuperCollider to MIDI."""

    def test_simple_pbind_to_midi(self):
        """Test converting simple Pbind to MIDI."""
        sc_code = '''Pbind(
            \\instrument, \\default,
            \\freq, Pseq([440, 880], 1),
            \\dur, Pseq([0.5, 0.5], 1),
            \\amp, Pseq([0.8, 0.6], 1)
        ).play;'''

        midi_bytes = supercollider_to_midi(sc_code, bpm=120.0)

        # Should be valid MIDI
        assert midi_bytes.startswith(b'MThd')

        # Parse and verify
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))
        assert len(midi.tracks) > 0

    def test_sc_to_midi_with_midinote(self):
        """Test conversion using midinote instead of freq."""
        sc_code = '''Pbind(
            \\instrument, \\default,
            \\midinote, Pseq([60, 64, 67], 1),
            \\dur, Pseq([0.25, 0.25, 0.5], 1)
        ).play;'''

        midi_bytes = supercollider_to_midi(sc_code, bpm=120.0)

        assert midi_bytes.startswith(b'MThd')

        # Parse and count notes
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))
        note_count = 0
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_count += 1

        assert note_count == 3

    def test_sc_to_midi_tempo(self):
        """Test that BPM is preserved in MIDI."""
        sc_code = 'Pbind(\\freq, Pseq([440], 1)).play;'

        midi_bytes = supercollider_to_midi(sc_code, bpm=140.0)

        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))

        # Find tempo message
        tempo_found = False
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    bpm = 60_000_000 / msg.tempo
                    assert abs(bpm - 140.0) < 1.0
                    tempo_found = True
                    break

        assert tempo_found

    def test_sc_to_midi_fallback(self):
        """Test fallback for invalid SC code."""
        invalid_sc = "not valid supercollider code"

        midi_bytes = supercollider_to_midi(invalid_sc, bpm=120.0)

        # Should produce minimal valid MIDI
        assert midi_bytes.startswith(b'MThd')


class TestRoundTrip:
    """Tests for round-trip MIDI ↔ SuperCollider conversion."""

    def test_midi_to_sc_to_midi(self):
        """Test converting MIDI → SC → MIDI preserves note count."""
        # Create original MIDI
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=480))
        track.append(mido.Message('note_on', note=64, velocity=80, time=0))
        track.append(mido.Message('note_off', note=64, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        original_midi_bytes = bytes_io.getvalue()

        # Convert to SC
        sc_code = midi_to_supercollider(original_midi_bytes, bpm=120.0)

        # Convert back to MIDI
        reconstructed_midi_bytes = supercollider_to_midi(sc_code, bpm=120.0)

        # Parse both
        original = mido.MidiFile(file=io.BytesIO(original_midi_bytes))
        reconstructed = mido.MidiFile(file=io.BytesIO(reconstructed_midi_bytes))

        # Count notes
        def count_notes(midi_file):
            count = 0
            for track in midi_file.tracks:
                for msg in track:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        count += 1
            return count

        assert count_notes(original) == count_notes(reconstructed)


class TestUtilities:
    """Tests for utility functions."""

    def test_midi_to_freq(self):
        """Test MIDI note to frequency conversion."""
        # A4 = 440 Hz
        assert abs(midi_to_freq(69) - 440.0) < 0.01

        # C4 = 261.63 Hz
        assert abs(midi_to_freq(60) - 261.63) < 0.01

        # A5 = 880 Hz
        assert abs(midi_to_freq(81) - 880.0) < 0.01

    def test_freq_to_midi(self):
        """Test frequency to MIDI note conversion."""
        # 440 Hz = A4
        assert freq_to_midi(440.0) == 69

        # 261.63 Hz = C4
        assert freq_to_midi(261.63) == 60

        # 880 Hz = A5
        assert freq_to_midi(880.0) == 81

    def test_roundtrip_freq_conversion(self):
        """Test round-trip frequency conversion."""
        for note in [36, 48, 60, 72, 84, 96]:
            freq = midi_to_freq(note)
            reconstructed_note = freq_to_midi(freq)
            assert reconstructed_note == note

    def test_quantize_time(self):
        """Test time quantization."""
        # Quantize to 16th notes (0.25)
        assert quantize_time(0.23, grid=0.25) == 0.25
        assert quantize_time(0.12, grid=0.25) == 0.0
        assert quantize_time(0.13, grid=0.25) == 0.25

        # Quantize to 8th notes (0.5)
        assert quantize_time(1.1, grid=0.5) == 1.0
        assert quantize_time(1.3, grid=0.5) == 1.5

    def test_quantize_zero(self):
        """Test quantizing zero stays zero."""
        assert quantize_time(0.0, grid=0.25) == 0.0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_high_notes(self):
        """Test handling of high MIDI notes."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=127, velocity=100, time=0))
        track.append(mido.Message('note_off', note=127, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        sc_code = midi_to_supercollider(midi_bytes)

        # Should handle gracefully
        assert 'Pbind(' in sc_code

    def test_very_low_notes(self):
        """Test handling of low MIDI notes."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=0, velocity=100, time=0))
        track.append(mido.Message('note_off', note=0, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        sc_code = midi_to_supercollider(midi_bytes)

        assert 'Pbind(' in sc_code

    def test_zero_velocity(self):
        """Test handling of zero velocity (note off as note on)."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        # Note off as velocity 0 note_on
        track.append(mido.Message('note_on', note=60, velocity=0, time=480))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        sc_code = midi_to_supercollider(midi_bytes)

        assert 'Pbind(' in sc_code

    def test_missing_note_off(self):
        """Test handling of missing note_off events."""
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        # No note_off - should use default duration

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        sc_code = midi_to_supercollider(midi_bytes)

        # Should handle gracefully with default duration
        assert 'Pbind(' in sc_code
        assert 'Pseq([' in sc_code
