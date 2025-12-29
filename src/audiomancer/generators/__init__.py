"""Pattern generation and evolution for audiomancer.

Provides interfaces for generating patterns with Magenta and evolving them
through mutation and crossover.
"""

from .interfaces import (
    EvolutionEngine,
    PatternGenerator,
    PatternMetadata,
    SynthLineage,
)

__all__ = [
    "EvolutionEngine",
    "PatternGenerator",
    "PatternMetadata",
    "SynthLineage",
]
