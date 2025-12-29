"""MIDI conversion for audiomancer.

Provides interfaces for converting between MIDI, TidalCycles, and SuperCollider formats.
"""

from .interfaces import (
    DRUM_MIDI_MAP,
    MidiConverter,
    MidiData,
    MidiNote,
    MidiTrack,
    SCPattern,
    TidalPattern,
)
from .midi_sc import (
    midi_to_supercollider,
    supercollider_to_midi,
    midi_to_freq,
    freq_to_midi,
    quantize_time,
)

__all__ = [
    "DRUM_MIDI_MAP",
    "MidiConverter",
    "MidiData",
    "MidiNote",
    "MidiTrack",
    "SCPattern",
    "TidalPattern",
    "midi_to_supercollider",
    "supercollider_to_midi",
    "midi_to_freq",
    "freq_to_midi",
    "quantize_time",
]
