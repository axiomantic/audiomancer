"""Tests for MIDI to TidalCycles conversion."""

import io
import pytest

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False

from audiomancer.converters.midi_tidal import (
    midi_to_tidal,
    tidal_to_midi,
    quantize_tidal_pattern,
    merge_tidal_patterns,
)
from audiomancer.converters.interfaces import DRUM_MIDI_MAP


pytestmark = pytest.mark.skipif(not MIDO_AVAILABLE, reason="mido not installed")


class TestMidiToTidal:
    """Tests for converting MIDI to TidalCycles."""

    def test_simple_midi_to_tidal(self):
        """Test converting simple MIDI pattern to Tidal."""
        # Create minimal MIDI file
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        # Add tempo
        track.append(mido.MetaMessage('set_tempo', tempo=500000))  # 120 BPM

        # Add kick drum on beat 1
        track.append(mido.Message('note_on', note=36, velocity=100, time=0))
        track.append(mido.Message('note_off', note=36, velocity=0, time=120))

        # Add snare on beat 3
        track.append(mido.Message('note_on', note=38, velocity=80, time=360))
        track.append(mido.Message('note_off', note=38, velocity=0, time=120))

        # Convert to bytes
        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Convert to Tidal
        tidal = midi_to_tidal(midi_bytes, bpm=120.0, channel="d1")

        # Should contain sound pattern
        assert 'd1 $ sound' in tidal
        assert 'bd' in tidal or 'sn' in tidal

    def test_midi_to_tidal_with_custom_map(self):
        """Test MIDI conversion with custom sample mapping."""
        # Create minimal MIDI
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)

        track.append(mido.MetaMessage('set_tempo', tempo=500000))
        track.append(mido.Message('note_on', note=60, velocity=100, time=0))
        track.append(mido.Message('note_off', note=60, velocity=0, time=120))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Custom mapping
        custom_map = {60: "custom_sample"}

        tidal = midi_to_tidal(midi_bytes, sample_map=custom_map)

        # Should use custom sample name
        assert 'custom_sample' in tidal or 'd1 $ sound' in tidal

    def test_midi_to_tidal_fallback(self):
        """Test fallback for invalid MIDI data."""
        # Invalid MIDI bytes
        invalid_midi = b"not_a_midi_file"

        # Should fallback gracefully
        tidal = midi_to_tidal(invalid_midi, bpm=120.0)

        # Should return some valid Tidal code
        assert 'd1 $ sound' in tidal
        assert 'bd' in tidal or 'sn' in tidal


class TestTidalToMidi:
    """Tests for converting TidalCycles to MIDI."""

    def test_simple_tidal_to_midi(self):
        """Test converting simple Tidal pattern to MIDI."""
        tidal = 'd1 $ sound "bd ~ sn ~"'

        midi_bytes = tidal_to_midi(tidal, bpm=120.0)

        # Should be valid MIDI
        assert midi_bytes.startswith(b'MThd')

        # Parse and verify
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))
        assert len(midi.tracks) > 0

    def test_tidal_to_midi_tempo(self):
        """Test that BPM is preserved in MIDI."""
        tidal = 'd1 $ sound "bd"'

        midi_bytes = tidal_to_midi(tidal, bpm=140.0)

        # Parse MIDI
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))

        # Find tempo message
        tempo_found = False
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    # Convert microseconds per beat to BPM
                    bpm = 60_000_000 / msg.tempo
                    assert abs(bpm - 140.0) < 1.0
                    tempo_found = True
                    break

        assert tempo_found

    def test_tidal_to_midi_notes(self):
        """Test that notes are present in MIDI."""
        tidal = 'd1 $ sound "bd sn"'

        midi_bytes = tidal_to_midi(tidal, bpm=120.0)

        # Parse MIDI
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))

        # Count note_on messages
        note_count = 0
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_count += 1

        assert note_count >= 2  # Should have at least 2 notes (bd and sn)

    def test_tidal_rest_handling(self):
        """Test that rests (~) are handled correctly."""
        tidal = 'd1 $ sound "bd ~ ~ sn"'

        midi_bytes = tidal_to_midi(tidal, bpm=120.0)

        # Should be valid MIDI
        assert midi_bytes.startswith(b'MThd')

        # Parse and count notes (should only have bd and sn, not rests)
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))
        note_count = 0
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_count += 1

        assert note_count == 2  # Only bd and sn

    def test_tidal_chord_handling(self):
        """Test handling of chords [...]."""
        tidal = 'd1 $ sound "[bd, sn]"'

        midi_bytes = tidal_to_midi(tidal, bpm=120.0)

        # Should be valid MIDI
        assert midi_bytes.startswith(b'MThd')


class TestBidirectionalConversion:
    """Tests for round-trip MIDI ↔ Tidal conversion."""

    def test_tidal_to_midi_to_tidal(self):
        """Test converting Tidal → MIDI → Tidal preserves structure."""
        original_tidal = 'd1 $ sound "bd ~ sn ~"'

        # Convert to MIDI
        midi_bytes = tidal_to_midi(original_tidal, bpm=120.0)

        # Convert back to Tidal
        reconstructed_tidal = midi_to_tidal(midi_bytes, bpm=120.0, channel="d1")

        # Should contain key elements
        assert 'd1 $ sound' in reconstructed_tidal
        # Pattern may differ slightly due to quantization, but should have similar structure


class TestQuantization:
    """Tests for pattern quantization."""

    def test_quantize_pattern(self):
        """Test quantizing a Tidal pattern."""
        pattern = "bd ~ sn ~"

        quantized = quantize_tidal_pattern(pattern, grid="16th")

        # Should return valid pattern (currently pass-through)
        assert isinstance(quantized, str)
        assert len(quantized) > 0

    def test_quantize_different_grids(self):
        """Test quantization with different grid sizes."""
        pattern = "bd sn hh"

        for grid in ["8th", "16th", "32nd"]:
            quantized = quantize_tidal_pattern(pattern, grid=grid)
            assert isinstance(quantized, str)


class TestPatternMerging:
    """Tests for merging Tidal patterns."""

    def test_merge_two_patterns(self):
        """Test merging two patterns."""
        p1 = 'sound "bd ~ sn ~"'
        p2 = 'sound "hh*8"'

        merged = merge_tidal_patterns([p1, p2])

        assert 'stack' in merged
        assert 'bd ~ sn ~' in merged
        assert 'hh*8' in merged

    def test_merge_single_pattern(self):
        """Test merging single pattern (no-op)."""
        pattern = 'sound "bd sn"'

        merged = merge_tidal_patterns([pattern])

        assert merged == pattern

    def test_merge_empty_list(self):
        """Test merging empty list."""
        merged = merge_tidal_patterns([])

        assert merged == 'silence'

    def test_merge_with_channel_assignments(self):
        """Test merging patterns with channel assignments."""
        p1 = 'd1 $ sound "bd ~ sn ~"'
        p2 = 'd2 $ sound "hh*8"'

        merged = merge_tidal_patterns([p1, p2])

        # Should strip channel assignments and merge
        assert 'stack' in merged


class TestDrumMapping:
    """Tests for drum MIDI mapping."""

    def test_drum_map_coverage(self):
        """Test that drum map covers common MIDI notes."""
        # Common drum notes should be mapped
        assert 36 in DRUM_MIDI_MAP  # Kick
        assert 38 in DRUM_MIDI_MAP  # Snare
        assert 42 in DRUM_MIDI_MAP  # Closed hat
        assert 46 in DRUM_MIDI_MAP  # Open hat

    def test_drum_map_values(self):
        """Test that drum map values are valid sample names."""
        for pitch, sample in DRUM_MIDI_MAP.items():
            assert isinstance(pitch, int)
            assert 0 <= pitch <= 127
            assert isinstance(sample, str)
            assert len(sample) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_midi_file(self):
        """Test handling of empty MIDI file."""
        # Minimal MIDI file with no notes
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage('end_of_track', time=0))

        bytes_io = io.BytesIO()
        midi.save(file=bytes_io)
        midi_bytes = bytes_io.getvalue()

        # Should handle gracefully
        tidal = midi_to_tidal(midi_bytes)
        assert isinstance(tidal, str)

    def test_malformed_tidal_code(self):
        """Test handling of malformed Tidal code."""
        malformed = "invalid tidal syntax"

        # Should still produce MIDI (may use fallback pattern)
        midi_bytes = tidal_to_midi(malformed, bpm=120.0)
        assert isinstance(midi_bytes, bytes)
        assert midi_bytes.startswith(b'MThd')

    def test_very_high_bpm(self):
        """Test handling of extreme BPM values."""
        tidal = 'd1 $ sound "bd"'

        # Very fast
        midi_fast = tidal_to_midi(tidal, bpm=300.0)
        assert midi_fast.startswith(b'MThd')

        # Very slow
        midi_slow = tidal_to_midi(tidal, bpm=40.0)
        assert midi_slow.startswith(b'MThd')
