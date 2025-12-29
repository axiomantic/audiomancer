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

__all__ = [
    "DRUM_MIDI_MAP",
    "MidiConverter",
    "MidiData",
    "MidiNote",
    "MidiTrack",
    "SCPattern",
    "TidalPattern",
]
