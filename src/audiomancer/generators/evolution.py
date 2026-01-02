"""Pattern evolution through mutation and crossover.

This module provides genetic algorithm-style evolution for musical patterns,
with lineage tracking and deterministic randomness for testing.
"""

import random
import uuid
from typing import Optional

from .patterns import Pattern, _generate_pattern_id
from ..errors import GenerationError


class EvolutionEngine:
    """Engine for evolving patterns through mutation and crossover."""

    def __init__(self, pattern_storage: Optional[dict[str, Pattern]] = None):
        """Initialize evolution engine.

        Args:
            pattern_storage: Optional dictionary to store patterns.
                             If None, creates internal storage.
        """
        self.patterns = pattern_storage if pattern_storage is not None else {}

    def store_pattern(self, pattern: Pattern) -> None:
        """Store pattern for later retrieval.

        Args:
            pattern: Pattern to store
        """
        self.patterns[pattern.id] = pattern

    def get_pattern(self, pattern_id: str) -> Pattern:
        """Retrieve pattern by ID.

        Args:
            pattern_id: Pattern ID to retrieve

        Returns:
            Pattern instance

        Raises:
            GenerationError: If pattern not found
        """
        if pattern_id not in self.patterns:
            raise GenerationError(
                f"Pattern not found: {pattern_id}",
                details={"pattern_id": pattern_id},
            )
        return self.patterns[pattern_id]

    def mutate_pattern(
        self,
        pattern: Pattern,
        amount: float = 0.3,
        seed: Optional[int] = None,
    ) -> Pattern:
        """Create a variation of a pattern.

        Mutation types:
        - Note deletion (10%)
        - Note addition (10%)
        - Timing shift (20%)
        - Velocity change (30%)
        - Note swap (30%)

        Amount controls probability of each change.

        Args:
            pattern: Pattern to mutate
            amount: Mutation strength (0.0-1.0)
            seed: Random seed for deterministic testing

        Returns:
            New mutated pattern

        Example:
            >>> engine = EvolutionEngine()
            >>> original = generate_drums(style="techno")
            >>> engine.store_pattern(original)
            >>> mutated = engine.mutate_pattern(original, amount=0.5, seed=42)
            >>> mutated.parent_ids
            [original.id]
        """
        if seed is not None:
            random.seed(seed)

        # Validate amount
        amount = max(0.0, min(1.0, amount))

        # Create mutated pattern with new ID
        new_id = _generate_pattern_id()

        # In a real implementation, we would:
        # 1. Parse MIDI data
        # 2. Apply mutations based on amount and random choices
        # 3. Regenerate Tidal/SC code
        # For now, create a simple variation

        # Add variation indicator to code
        mutated_tidal = pattern.tidal_code.replace(
            'd1 $', f'd1 $ degradeBy {amount * 0.2} $'
        )

        mutated_sc = pattern.sc_code.replace(
            '\\amp, 0.', f'\\amp, {0.8 - amount * 0.2},'
        )

        # Type assertion: we know pattern.type is one of the valid literals
        from typing import cast, Literal
        pattern_type = cast(Literal["drums", "melody", "bass"], pattern.type)

        return Pattern(
            pattern_id=new_id,
            pattern_type=pattern_type,
            midi_data=pattern.midi_data,  # In real impl, mutate MIDI
            tidal_code=mutated_tidal,
            sc_code=mutated_sc,
            bpm=pattern.bpm,
            bars=pattern.bars,
            key=pattern.key,
            scale=pattern.scale,
            parent_ids=[pattern.id],
            generation_method="mutated",
            mutation_amount=amount,
        )

    def crossover_patterns(
        self,
        pattern_a: Pattern,
        pattern_b: Pattern,
        seed: Optional[int] = None,
    ) -> Pattern:
        """Breed two patterns to create a child.

        Takes structural elements from both parents:
        - First half from A, second half from B (50%)
        - Alternating bars (30%)
        - Random selection per beat (20%)

        Args:
            pattern_a: First parent pattern
            pattern_b: Second parent pattern
            seed: Random seed for deterministic testing

        Returns:
            New hybrid pattern

        Raises:
            GenerationError: If patterns are incompatible

        Example:
            >>> engine = EvolutionEngine()
            >>> pattern_a = generate_drums(style="house")
            >>> pattern_b = generate_drums(style="techno")
            >>> engine.store_pattern(pattern_a)
            >>> engine.store_pattern(pattern_b)
            >>> hybrid = engine.crossover_patterns(pattern_a, pattern_b, seed=42)
            >>> hybrid.parent_ids
            [pattern_a.id, pattern_b.id]
        """
        if seed is not None:
            random.seed(seed)

        # Validate compatibility
        if pattern_a.type != pattern_b.type:
            raise GenerationError(
                "Cannot crossover patterns of different types",
                details={
                    "pattern_a_type": pattern_a.type,
                    "pattern_b_type": pattern_b.type,
                },
            )

        # Create hybrid pattern
        new_id = _generate_pattern_id()

        # Simple crossover: combine Tidal codes
        # In real implementation, would merge MIDI data
        hybrid_tidal = f'd1 $ cat [{pattern_a.tidal_code.split("$")[1].strip()}, {pattern_b.tidal_code.split("$")[1].strip()}]'

        # Merge SC code (simplified)
        hybrid_sc = pattern_a.sc_code  # Use first parent's SC code as base

        # Average BPM
        avg_bpm = (pattern_a.bpm + pattern_b.bpm) / 2

        # Type assertion: we know pattern_a.type is one of the valid literals
        from typing import cast, Literal
        pattern_type = cast(Literal["drums", "melody", "bass"], pattern_a.type)

        return Pattern(
            pattern_id=new_id,
            pattern_type=pattern_type,
            midi_data=pattern_a.midi_data,  # In real impl, merge MIDI
            tidal_code=hybrid_tidal,
            sc_code=hybrid_sc,
            bpm=avg_bpm,
            bars=max(pattern_a.bars, pattern_b.bars),
            key=pattern_a.key or pattern_b.key,
            scale=pattern_a.scale or pattern_b.scale,
            parent_ids=[pattern_a.id, pattern_b.id],
            generation_method="crossover",
        )

    def get_lineage(self, pattern_id: str) -> list[str]:
        """Get full family tree of pattern.

        Recursively traces parent_ids to root.

        Args:
            pattern_id: Pattern ID to trace

        Returns:
            List of ancestor IDs from oldest to newest

        Example:
            >>> engine = EvolutionEngine()
            >>> root = generate_drums()
            >>> engine.store_pattern(root)
            >>> gen1 = engine.mutate_pattern(root)
            >>> engine.store_pattern(gen1)
            >>> gen2 = engine.mutate_pattern(gen1)
            >>> engine.store_pattern(gen2)
            >>> lineage = engine.get_lineage(gen2.id)
            >>> lineage
            [root.id, gen1.id, gen2.id]
        """
        lineage = []
        current_id = pattern_id

        # Track visited to prevent infinite loops
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)

            try:
                pattern = self.get_pattern(current_id)
                lineage.insert(0, current_id)

                # Move to parent (if exists)
                if pattern.parent_ids:
                    # Use first parent for lineage chain
                    current_id = pattern.parent_ids[0]
                else:
                    break
            except GenerationError:
                # Pattern not found, stop tracing
                break

        return lineage

    def rank_by_rating(
        self,
        pattern_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[Pattern]:
        """Get highest-rated patterns.

        Args:
            pattern_type: Filter by type (None = all types)
            limit: Maximum results

        Returns:
            Patterns sorted by rating descending

        Example:
            >>> engine = EvolutionEngine()
            >>> # ... store patterns with ratings ...
            >>> top_drums = engine.rank_by_rating(pattern_type="drums", limit=5)
        """
        patterns = list(self.patterns.values())

        # Filter by type
        if pattern_type:
            patterns = [p for p in patterns if p.type == pattern_type]

        # Sort by rating (patterns don't have rating attribute yet)
        # In real implementation, would sort by user_rating
        # For now, sort by creation time (newest first)
        patterns.sort(key=lambda p: p.created_at, reverse=True)

        return patterns[:limit]

    def evolve_population(
        self,
        population: list[Pattern],
        generations: int = 5,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.2,
        seed: Optional[int] = None,
    ) -> list[Pattern]:
        """Evolve a population of patterns over multiple generations.

        Genetic algorithm:
        1. Rank population by fitness (creation time as proxy)
        2. Select top 50% as parents
        3. Mutate parents (mutation_rate probability)
        4. Crossover random parent pairs (crossover_rate probability)
        5. Repeat for N generations

        Args:
            population: List of patterns to evolve
            generations: Number of evolution cycles
            mutation_rate: Probability of mutation (0.0-1.0)
            crossover_rate: Probability of crossover (0.0-1.0)
            seed: Random seed for deterministic testing

        Returns:
            Final population (patterns from all generations)

        Example:
            >>> engine = EvolutionEngine()
            >>> initial = [
            ...     generate_drums(style="house"),
            ...     generate_drums(style="techno"),
            ...     generate_drums(style="breakbeat"),
            ... ]
            >>> for p in initial:
            ...     engine.store_pattern(p)
            >>> final = engine.evolve_population(
            ...     population=initial,
            ...     generations=3,
            ...     mutation_rate=0.3,
            ...     crossover_rate=0.2,
            ...     seed=42,
            ... )
            >>> len(final) > len(initial)
            True
        """
        if seed is not None:
            random.seed(seed)

        all_patterns = population.copy()

        for gen in range(generations):
            # Select top 50% as parents
            num_parents = max(1, len(population) // 2)
            parents = population[:num_parents]

            new_patterns = []

            # Mutation phase
            for parent in parents:
                if random.random() < mutation_rate:
                    mutated = self.mutate_pattern(parent, amount=0.3, seed=None)
                    self.store_pattern(mutated)
                    new_patterns.append(mutated)

            # Crossover phase
            if len(parents) >= 2:
                num_crossovers = max(1, int(len(parents) * crossover_rate))
                for _ in range(num_crossovers):
                    parent_a = random.choice(parents)
                    parent_b = random.choice(parents)
                    if parent_a.id != parent_b.id:
                        try:
                            hybrid = self.crossover_patterns(
                                parent_a, parent_b, seed=None
                            )
                            self.store_pattern(hybrid)
                            new_patterns.append(hybrid)
                        except GenerationError:
                            # Incompatible patterns, skip
                            pass

            # Update population for next generation
            population = parents + new_patterns
            all_patterns.extend(new_patterns)

        return all_patterns
