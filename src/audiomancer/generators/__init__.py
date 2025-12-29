"""Pattern generation and evolution for audiomancer.

Provides interfaces for generating patterns with Magenta and evolving them
through mutation and crossover.

Synth Evolution:
- generate_synth: Generate new SynthDefs from templates or descriptions
- mutate_synth: Mutate existing synths with genetic operations
- breed_synths: Crossover two synths to create hybrids
- Lineage tracking: Track evolutionary history and ratings

Example:
    Pattern generation:
    >>> from audiomancer.generators import PatternGenerator, EvolutionEngine
    >>> generator = PatternGenerator()
    >>> pattern = generator.generate_drums(style="techno", bars=4, bpm=125)
    >>> engine = EvolutionEngine()
    >>> mutated = engine.mutate_pattern(pattern.id, amount=0.3)

    Synth evolution:
    >>> from audiomancer.generators import generate_synth, mutate_synth
    >>> synth = generate_synth("acid bass with filter sweep", category="bass")
    >>> variant = mutate_synth(synth, amount=0.5, seed=42)
    >>> print(variant.mutation_log)
    ['Saw → Pulse', 'Added LFO modulation to cutoff']
"""

from .interfaces import (
    EvolutionEngine,
    PatternGenerator,
    PatternMetadata,
    SynthLineage,
)

from .synths import (
    generate_synth,
    mutate_synth,
    breed_synths,
    GeneratedSynth,
)

from .lineage import (
    LineageTracker,
    SynthRecord,
    record_synth,
    rate_synth,
    get_synth_lineage,
    get_top_rated,
    get_generation_stats,
)

__all__ = [
    # Interfaces
    "EvolutionEngine",
    "PatternGenerator",
    "PatternMetadata",
    "SynthLineage",
    # Synth Generation
    "generate_synth",
    "mutate_synth",
    "breed_synths",
    "GeneratedSynth",
    # Lineage Tracking
    "LineageTracker",
    "SynthRecord",
    "record_synth",
    "rate_synth",
    "get_synth_lineage",
    "get_top_rated",
    "get_generation_stats",
]
