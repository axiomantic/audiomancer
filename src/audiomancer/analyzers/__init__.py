"""SynthDef analysis for audiomancer.

Provides interfaces for parsing and storing SuperCollider SynthDef files.
"""

from .interfaces import (
    ControlSpec,
    SynthControl,
    SynthDefMetadata,
    SynthDefParser,
    SynthDefStore,
)

__all__ = [
    "ControlSpec",
    "SynthControl",
    "SynthDefMetadata",
    "SynthDefParser",
    "SynthDefStore",
]
