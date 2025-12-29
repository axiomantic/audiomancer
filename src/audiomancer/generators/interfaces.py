"""Pattern generation and evolution interfaces for audiomancer.

This module defines Protocol interfaces for generating musical patterns using
Magenta models and evolving them through mutation and crossover.
"""

from datetime import datetime
from typing import Literal, Optional, Protocol
from typing_extensions import TypedDict


class PatternMetadata(TypedDict, total=False):
    """Metadata for a generated pattern.

    Stores MIDI data and conversion outputs for patterns.

    Example:
        >>> pattern = PatternMetadata(
        ...     id="ptrn_abc12345",
        ...     type="drums",
        ...     midi_data='{"tracks": [...], "tempo": 120}',
        ...     tidal_code="d1 $ sound \"bd ~ sn ~\"",
        ...     sc_code="Pbind(\\instrument, \\default, ...)",
        ...     style="techno",
        ...     key="C",
        ...     scale="minor",
        ...     bpm=125.0,
        ...     bars=4,
        ...     parent_ids=["ptrn_xyz789"],
        ...     generation_method="mutated",
        ...     mutation_amount=0.3,
        ...     user_rating=4,
        ...     user_notes="Good groove, needs variation",
        ...     created_at=datetime.now(),
        ... )
    """
    # Identity (required)
    id: str  # Format: "ptrn_{uuid[:8]}"
    type: Literal["drums", "melody", "bass"]  # Pattern type

    # Content (required)
    midi_data: str  # JSON-serialized MidiData
    tidal_code: Optional[str]  # TidalCycles mininotation
    sc_code: Optional[str]  # SuperCollider Pbind

    # Generation parameters (optional)
    style: Optional[str]  # Style hint (e.g., "techno", "house", "dnb")
    key: Optional[str]  # Musical key (e.g., "C", "F#m")
    scale: Optional[str]  # Scale type (major, minor, pentatonic, chromatic)
    bpm: float  # Tempo in BPM
    bars: int  # Number of bars

    # Lineage tracking (required)
    parent_ids: list[str]  # Parent pattern IDs (empty if generated from scratch)
    generation_method: Literal["generated", "mutated", "crossover"]
    mutation_amount: Optional[float]  # Mutation strength (0.0-1.0)

    # User feedback (optional)
    user_rating: Optional[int]  # Rating 1-5
    user_notes: Optional[str]  # User comments

    # Timestamp
    created_at: datetime


class SynthLineage(TypedDict, total=False):
    """Lineage tracking for evolved SynthDefs.

    Records mutation history and parent relationships.

    Example:
        >>> lineage = SynthLineage(
        ...     id="synt_evolved1",
        ...     name="tb303_evolved_1",
        ...     source_code="SynthDef(\\tb303_evolved_1, { ... })",
        ...     parent_ids=["synt_tb303"],
        ...     generation_method="mutated",
        ...     mutation_log=[
        ...         "Increased cutoff default: 1200 → 1500",
        ...         "Added distortion: 0 → 0.3",
        ...     ],
        ...     user_rating=5,
        ...     user_notes="Perfect acid sound",
        ...     created_at=datetime.now(),
        ... )
    """
    # Identity (required)
    id: str  # Format: "synt_{hash[:8]}"
    name: str  # Unique SynthDef name
    source_code: str  # Full .scd code

    # Lineage (required)
    parent_ids: list[str]  # Parent synth IDs
    generation_method: Literal["original", "mutated", "crossover"]
    mutation_log: list[str]  # Human-readable mutation descriptions

    # User feedback (optional)
    user_rating: Optional[int]  # Rating 1-5
    user_notes: Optional[str]  # User comments

    # Timestamp
    created_at: datetime


class PatternGenerator(Protocol):
    """Interface for generating musical patterns using Magenta.

    Supports drum and melody generation with style and scale constraints.
    """

    def generate_drums(
        self,
        style: Literal["basic", "techno", "house", "dnb"] = "basic",
        bars: int = 4,
        bpm: float = 120.0,
        timeout: int = 30,
    ) -> PatternMetadata:
        """Generate drum pattern using Magenta DrumsRNN.

        Styles:
        - basic: 4-on-floor kick, snare on 2&4
        - techno: 16th hat variations, offbeat kicks
        - house: shuffle groove, open hats
        - dnb: fast breaks, syncopation

        Args:
            style: Generation style
            bars: Number of bars to generate
            bpm: Tempo in BPM
            timeout: Maximum generation time (seconds)

        Returns:
            Generated pattern with MIDI data

        Raises:
            InferenceTimeoutError: If generation exceeds timeout
            ModelLoadError: If Magenta not available

        Example:
            >>> generator = PatternGenerator()
            >>> pattern = generator.generate_drums(
            ...     style="techno",
            ...     bars=4,
            ...     bpm=125,
            ...     timeout=30,
            ... )
            >>> pattern['type']
            "drums"
            >>> pattern['bpm']
            125.0
            >>> pattern['parent_ids']
            []
        """
        ...

    def generate_melody(
        self,
        key: str = "C",
        scale: Literal["major", "minor", "pentatonic", "chromatic"] = "minor",
        bars: int = 4,
        bpm: float = 120.0,
        timeout: int = 30,
    ) -> PatternMetadata:
        """Generate melody using Magenta MelodyRNN.

        Scales:
        - major: C D E F G A B (Ionian)
        - minor: C D Eb F G Ab Bb (Natural minor/Aeolian)
        - pentatonic: C D F G A (Minor pentatonic)
        - chromatic: All 12 notes

        Args:
            key: Root note (e.g., "C", "F#", "Bb")
            scale: Scale type
            bars: Number of bars to generate
            bpm: Tempo in BPM
            timeout: Maximum generation time (seconds)

        Returns:
            Generated melody pattern

        Raises:
            InferenceTimeoutError: If generation exceeds timeout
            ModelLoadError: If Magenta not available

        Example:
            >>> generator = PatternGenerator()
            >>> melody = generator.generate_melody(
            ...     key="C",
            ...     scale="minor",
            ...     bars=4,
            ...     bpm=120,
            ... )
            >>> melody['key']
            "C"
            >>> melody['scale']
            "minor"
        """
        ...

    def generate_bass(
        self,
        key: str = "C",
        scale: Literal["major", "minor", "pentatonic", "chromatic"] = "minor",
        bars: int = 4,
        bpm: float = 120.0,
        timeout: int = 30,
    ) -> PatternMetadata:
        """Generate bass line pattern.

        Similar to melody but constrained to lower register.

        Args:
            key: Root note
            scale: Scale type
            bars: Number of bars
            bpm: Tempo in BPM
            timeout: Maximum generation time (seconds)

        Returns:
            Generated bass pattern

        Raises:
            InferenceTimeoutError: If generation exceeds timeout
            ModelLoadError: If Magenta not available

        Example:
            >>> bass = generator.generate_bass(
            ...     key="F#",
            ...     scale="minor",
            ...     bars=8,
            ...     bpm=140,
            ... )
            >>> bass['type']
            "bass"
        """
        ...

    def load_model(self, model_name: Literal["drums_rnn", "melody_rnn"]) -> None:
        """Load and cache Magenta model.

        Downloads model if not present. Caches in memory for reuse.

        Args:
            model_name: Model to load

        Raises:
            ModelLoadError: If download or loading fails
            ImportError: If Magenta/TensorFlow not installed

        Example:
            >>> generator = PatternGenerator()
            >>> generator.load_model("drums_rnn")
            >>> generator.load_model("melody_rnn")
        """
        ...

    def download_models(self) -> None:
        """Download all required Magenta models (~500MB total).

        Downloads to ~/.local/share/audiomancer/models/

        Raises:
            IOError: If download fails

        Example:
            >>> generator = PatternGenerator()
            >>> generator.download_models()
            # Downloads drums_rnn.mag, melody_rnn.mag
        """
        ...


class EvolutionEngine(Protocol):
    """Interface for evolving patterns and synths through mutation and crossover.

    Implements genetic algorithm-style evolution with lineage tracking.
    """

    def mutate_pattern(
        self,
        pattern_id: str,
        amount: float = 0.3,
        seed: Optional[int] = None,
    ) -> PatternMetadata:
        """Mutate pattern with deterministic randomness.

        Mutation types (probability based on amount):
        1. Shift timing: ±50ms per note (amount * 0.3 probability)
        2. Swap notes: exchange two notes (amount * 0.2)
        3. Change velocity: ±20% (amount * 0.3)
        4. Add note: insert on empty step (amount * 0.1)
        5. Remove note: delete random note (amount * 0.1)

        Args:
            pattern_id: Pattern to mutate
            amount: Mutation strength (0.0-1.0, higher = more drastic)
            seed: Random seed for deterministic testing

        Returns:
            New mutated pattern with lineage tracking

        Raises:
            PatternNotFoundError: If pattern_id does not exist

        Example:
            >>> engine = EvolutionEngine()
            >>> original = pattern_store.get("ptrn_abc123")
            >>> mutated = engine.mutate_pattern(
            ...     "ptrn_abc123",
            ...     amount=0.5,
            ...     seed=42,  # Deterministic for testing
            ... )
            >>> mutated['parent_ids']
            ["ptrn_abc123"]
            >>> mutated['mutation_amount']
            0.5
            >>> mutated['generation_method']
            "mutated"
        """
        ...

    def crossover_patterns(
        self,
        pattern_id_1: str,
        pattern_id_2: str,
        seed: Optional[int] = None,
    ) -> PatternMetadata:
        """Crossover two patterns to create hybrid.

        Algorithm:
        1. Split each pattern at random bar boundary
        2. Combine first half of pattern 1 with second half of pattern 2
        3. Quantize and adjust timing to maintain coherence

        Args:
            pattern_id_1: First parent pattern
            pattern_id_2: Second parent pattern
            seed: Random seed for deterministic testing

        Returns:
            New hybrid pattern with both parents in lineage

        Raises:
            PatternNotFoundError: If either pattern not found
            IncompatiblePatternsError: If patterns have different time signatures

        Example:
            >>> engine = EvolutionEngine()
            >>> hybrid = engine.crossover_patterns(
            ...     "ptrn_abc123",
            ...     "ptrn_def456",
            ...     seed=42,
            ... )
            >>> hybrid['parent_ids']
            ["ptrn_abc123", "ptrn_def456"]
            >>> hybrid['generation_method']
            "crossover"
        """
        ...

    def mutate_synth(
        self,
        synth_id: str,
        amount: float = 0.3,
        seed: Optional[int] = None,
    ) -> SynthLineage:
        """Mutate SynthDef parameters.

        Mutation types:
        1. Adjust control defaults: ±20% of range
        2. Swap oscillator types: Saw ↔ Pulse ↔ Sine
        3. Add/remove effects: reverb, distortion, delay
        4. Adjust envelope times: ±30%

        Args:
            synth_id: SynthDef to mutate
            amount: Mutation strength (0.0-1.0)
            seed: Random seed for deterministic testing

        Returns:
            New mutated SynthDef with lineage

        Raises:
            SynthNotFoundError: If synth_id does not exist
            InvalidSynthError: If mutated synth fails validation with sclang

        Example:
            >>> engine = EvolutionEngine()
            >>> mutated = engine.mutate_synth(
            ...     "synt_tb303",
            ...     amount=0.4,
            ...     seed=42,
            ... )
            >>> mutated['parent_ids']
            ["synt_tb303"]
            >>> mutated['mutation_log']
            [
                "Increased cutoff default: 1200 → 1440",
                "Changed oscillator: Saw → Pulse",
            ]
        """
        ...

    def validate_mutated_synth(self, source_code: str) -> bool:
        """Validate SynthDef by compiling with sclang.

        Ensures mutated SynthDef is syntactically valid.

        Args:
            source_code: SuperCollider code to validate

        Returns:
            True if valid, False if compilation fails

        Example:
            >>> code = "SynthDef(\\test, { Out.ar(0, SinOsc.ar(440)); })"
            >>> engine.validate_mutated_synth(code)
            True
            >>> bad_code = "SynthDef(\\test, { invalid syntax )"
            >>> engine.validate_mutated_synth(bad_code)
            False
        """
        ...

    def get_lineage(self, item_id: str) -> list[str]:
        """Get full ancestry chain for pattern or synth.

        Recursively traces parent_ids to root.

        Args:
            item_id: Pattern or synth ID

        Returns:
            List of ancestor IDs from oldest to newest

        Example:
            >>> # Pattern with 3 generations:
            >>> # ptrn_root → ptrn_gen1 → ptrn_gen2 → ptrn_gen3
            >>> lineage = engine.get_lineage("ptrn_gen3")
            >>> lineage
            ["ptrn_root", "ptrn_gen1", "ptrn_gen2", "ptrn_gen3"]
        """
        ...

    def rank_by_rating(
        self,
        pattern_type: Optional[Literal["drums", "melody", "bass"]] = None,
        limit: int = 10,
    ) -> list[PatternMetadata]:
        """Get highest-rated patterns.

        Useful for selecting best candidates for further evolution.

        Args:
            pattern_type: Filter by type (None = all types)
            limit: Maximum results

        Returns:
            Patterns sorted by user_rating descending

        Example:
            >>> top_drums = engine.rank_by_rating(
            ...     pattern_type="drums",
            ...     limit=5,
            ... )
            >>> top_drums[0]['user_rating']
            5
        """
        ...

    def evolve_population(
        self,
        population: list[str],
        generations: int = 5,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.2,
        seed: Optional[int] = None,
    ) -> list[PatternMetadata]:
        """Evolve a population of patterns over multiple generations.

        Genetic algorithm:
        1. Rank population by fitness (user ratings)
        2. Select top 50% as parents
        3. Mutate parents (mutation_rate probability)
        4. Crossover random parent pairs (crossover_rate probability)
        5. Repeat for N generations

        Args:
            population: List of pattern IDs to evolve
            generations: Number of evolution cycles
            mutation_rate: Probability of mutation (0.0-1.0)
            crossover_rate: Probability of crossover (0.0-1.0)
            seed: Random seed for deterministic testing

        Returns:
            Final population (patterns from all generations)

        Example:
            >>> initial = ["ptrn_1", "ptrn_2", "ptrn_3", "ptrn_4"]
            >>> final_pop = engine.evolve_population(
            ...     population=initial,
            ...     generations=5,
            ...     mutation_rate=0.3,
            ...     crossover_rate=0.2,
            ...     seed=42,
            ... )
            >>> len(final_pop) > len(initial)
            True
        """
        ...
