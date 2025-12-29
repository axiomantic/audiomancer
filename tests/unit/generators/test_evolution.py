"""Tests for pattern evolution engine."""

import pytest

from audiomancer.generators.evolution import EvolutionEngine
from audiomancer.generators.patterns import Pattern, generate_drums, MAGENTA_AVAILABLE
from audiomancer.errors import GenerationError


class TestEvolutionEngineStorage:
    """Tests for pattern storage and retrieval."""

    def test_store_and_retrieve_pattern(self):
        """Test storing and retrieving patterns."""
        engine = EvolutionEngine()

        pattern = Pattern(
            pattern_id="ptrn_test",
            pattern_type="drums",
            midi_data=b"test",
            tidal_code="d1 $ sound 'bd'",
            sc_code="Pbind(...)",
            bpm=120.0,
            bars=4,
        )

        engine.store_pattern(pattern)
        retrieved = engine.get_pattern("ptrn_test")

        assert retrieved.id == pattern.id
        assert retrieved.type == pattern.type

    def test_get_nonexistent_pattern(self):
        """Test error when pattern doesn't exist."""
        engine = EvolutionEngine()

        with pytest.raises(GenerationError) as exc_info:
            engine.get_pattern("ptrn_nonexistent")

        assert "Pattern not found" in str(exc_info.value)
        assert "ptrn_nonexistent" in exc_info.value.details["pattern_id"]

    def test_shared_storage(self):
        """Test using shared storage dictionary."""
        storage = {}
        engine = EvolutionEngine(pattern_storage=storage)

        pattern = Pattern(
            pattern_id="ptrn_shared",
            pattern_type="drums",
            midi_data=b"test",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        engine.store_pattern(pattern)

        # Pattern should be in shared storage
        assert "ptrn_shared" in storage
        assert storage["ptrn_shared"] == pattern


class TestMutation:
    """Tests for pattern mutation."""

    def test_mutate_pattern(self):
        """Test mutating a pattern."""
        engine = EvolutionEngine()

        original = Pattern(
            pattern_id="ptrn_original",
            pattern_type="drums",
            midi_data=b"test",
            tidal_code='d1 $ sound "bd ~ sn ~"',
            sc_code="Pbind(\\amp, 0.8)",
            bpm=125.0,
            bars=4,
        )

        engine.store_pattern(original)
        mutated = engine.mutate_pattern(original, amount=0.5, seed=42)

        # Should have new ID
        assert mutated.id != original.id
        assert mutated.id.startswith("ptrn_")

        # Should track parent
        assert mutated.parent_ids == [original.id]
        assert mutated.generation_method == "mutated"
        assert mutated.mutation_amount == 0.5

        # Should preserve type and bars
        assert mutated.type == original.type
        assert mutated.bpm == original.bpm
        assert mutated.bars == original.bars

    def test_mutate_with_seed(self):
        """Test deterministic mutation with seed."""
        engine = EvolutionEngine()

        original = Pattern(
            pattern_id="ptrn_seed_test",
            pattern_type="drums",
            midi_data=b"test",
            tidal_code='d1 $ sound "bd sn"',
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        engine.store_pattern(original)

        # Same seed should produce same result
        mut1 = engine.mutate_pattern(original, amount=0.3, seed=42)
        mut2 = engine.mutate_pattern(original, amount=0.3, seed=42)

        # IDs will differ but mutations should be similar
        assert mut1.parent_ids == mut2.parent_ids
        assert mut1.mutation_amount == mut2.mutation_amount

    def test_mutate_amount_bounds(self):
        """Test mutation amount is clamped to valid range."""
        engine = EvolutionEngine()

        original = Pattern(
            pattern_id="ptrn_bounds",
            pattern_type="drums",
            midi_data=b"test",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        # Amount < 0 should be clamped
        mut_low = engine.mutate_pattern(original, amount=-0.5)
        assert mut_low.mutation_amount >= 0.0

        # Amount > 1 should be clamped
        mut_high = engine.mutate_pattern(original, amount=1.5)
        assert mut_high.mutation_amount <= 1.0


class TestCrossover:
    """Tests for pattern crossover."""

    def test_crossover_patterns(self):
        """Test crossing over two patterns."""
        engine = EvolutionEngine()

        pattern_a = Pattern(
            pattern_id="ptrn_a",
            pattern_type="drums",
            midi_data=b"a",
            tidal_code='d1 $ sound "bd ~ sn ~"',
            sc_code="Pbind()",
            bpm=120.0,
            bars=4,
        )

        pattern_b = Pattern(
            pattern_id="ptrn_b",
            pattern_type="drums",
            midi_data=b"b",
            tidal_code='d1 $ sound "bd bd sn sn"',
            sc_code="Pbind()",
            bpm=130.0,
            bars=4,
        )

        engine.store_pattern(pattern_a)
        engine.store_pattern(pattern_b)

        hybrid = engine.crossover_patterns(pattern_a, pattern_b, seed=42)

        # Should have new ID
        assert hybrid.id != pattern_a.id
        assert hybrid.id != pattern_b.id

        # Should track both parents
        assert hybrid.parent_ids == [pattern_a.id, pattern_b.id]
        assert hybrid.generation_method == "crossover"

        # Should preserve type
        assert hybrid.type == "drums"

        # BPM should be averaged
        assert hybrid.bpm == 125.0  # (120 + 130) / 2

    def test_crossover_incompatible_types(self):
        """Test error when crossing over different types."""
        engine = EvolutionEngine()

        drums = Pattern(
            pattern_id="ptrn_drums",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        melody = Pattern(
            pattern_id="ptrn_melody",
            pattern_type="melody",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        with pytest.raises(GenerationError) as exc_info:
            engine.crossover_patterns(drums, melody)

        assert "different types" in str(exc_info.value)
        assert exc_info.value.details["pattern_a_type"] == "drums"
        assert exc_info.value.details["pattern_b_type"] == "melody"


class TestLineage:
    """Tests for lineage tracking."""

    def test_simple_lineage(self):
        """Test lineage for single generation."""
        engine = EvolutionEngine()

        root = Pattern(
            pattern_id="ptrn_root",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        engine.store_pattern(root)
        child = engine.mutate_pattern(root)
        engine.store_pattern(child)

        lineage = engine.get_lineage(child.id)

        assert lineage == [root.id, child.id]

    def test_multi_generation_lineage(self):
        """Test lineage across multiple generations."""
        engine = EvolutionEngine()

        gen0 = Pattern(
            pattern_id="ptrn_gen0",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        engine.store_pattern(gen0)

        gen1 = engine.mutate_pattern(gen0)
        engine.store_pattern(gen1)

        gen2 = engine.mutate_pattern(gen1)
        engine.store_pattern(gen2)

        gen3 = engine.mutate_pattern(gen2)
        engine.store_pattern(gen3)

        lineage = engine.get_lineage(gen3.id)

        assert len(lineage) == 4
        assert lineage == [gen0.id, gen1.id, gen2.id, gen3.id]

    def test_lineage_with_missing_ancestors(self):
        """Test lineage when some ancestors are missing."""
        engine = EvolutionEngine()

        # Child references parent that doesn't exist
        child = Pattern(
            pattern_id="ptrn_child",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
            parent_ids=["ptrn_missing_parent"],
        )

        engine.store_pattern(child)
        lineage = engine.get_lineage(child.id)

        # Should stop at child since parent is missing
        assert lineage == [child.id]


class TestRanking:
    """Tests for pattern ranking."""

    def test_rank_by_type(self):
        """Test filtering by pattern type."""
        engine = EvolutionEngine()

        drums1 = Pattern(
            pattern_id="ptrn_drums1",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        drums2 = Pattern(
            pattern_id="ptrn_drums2",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=125.0,
            bars=4,
        )

        melody = Pattern(
            pattern_id="ptrn_melody",
            pattern_type="melody",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=130.0,
            bars=4,
        )

        engine.store_pattern(drums1)
        engine.store_pattern(drums2)
        engine.store_pattern(melody)

        # Get only drums
        drums_patterns = engine.rank_by_rating(pattern_type="drums")
        assert len(drums_patterns) == 2
        assert all(p.type == "drums" for p in drums_patterns)

        # Get only melodies
        melody_patterns = engine.rank_by_rating(pattern_type="melody")
        assert len(melody_patterns) == 1
        assert melody_patterns[0].type == "melody"

    def test_rank_limit(self):
        """Test limiting number of results."""
        engine = EvolutionEngine()

        # Create 10 patterns
        for i in range(10):
            pattern = Pattern(
                pattern_id=f"ptrn_{i}",
                pattern_type="drums",
                midi_data=b"",
                tidal_code="",
                sc_code="",
                bpm=120.0,
                bars=4,
            )
            engine.store_pattern(pattern)

        # Get top 5
        top_5 = engine.rank_by_rating(limit=5)
        assert len(top_5) == 5


class TestPopulationEvolution:
    """Tests for evolving pattern populations."""

    def test_evolve_population(self):
        """Test evolving a population over multiple generations."""
        engine = EvolutionEngine()

        # Create initial population
        initial = [
            generate_drums(style="house", bpm=120),
            generate_drums(style="techno", bpm=125),
            generate_drums(style="breakbeat", bpm=130),
        ]

        for p in initial:
            engine.store_pattern(p)

        # Evolve population
        final = engine.evolve_population(
            population=initial,
            generations=3,
            mutation_rate=0.5,
            crossover_rate=0.3,
            seed=42,
        )

        # Should have more patterns after evolution
        assert len(final) > len(initial)

        # All patterns should be stored
        for p in final:
            assert p.id in engine.patterns

    def test_evolve_with_deterministic_seed(self):
        """Test that evolution is deterministic with seed."""
        engine1 = EvolutionEngine()
        engine2 = EvolutionEngine()

        initial = [
            generate_drums(style="house", bpm=120),
            generate_drums(style="techno", bpm=125),
        ]

        for p in initial:
            engine1.store_pattern(p)
            engine2.store_pattern(p)

        final1 = engine1.evolve_population(
            population=initial,
            generations=2,
            mutation_rate=0.3,
            crossover_rate=0.2,
            seed=42,
        )

        final2 = engine2.evolve_population(
            population=initial,
            generations=2,
            mutation_rate=0.3,
            crossover_rate=0.2,
            seed=42,
        )

        # Should produce same number of patterns
        assert len(final1) == len(final2)

    def test_evolve_tracks_lineage(self):
        """Test that evolved patterns have proper lineage."""
        engine = EvolutionEngine()

        initial = [
            generate_drums(style="house", bpm=120),
            generate_drums(style="techno", bpm=125),
        ]

        for p in initial:
            engine.store_pattern(p)

        final = engine.evolve_population(
            population=initial,
            generations=2,
            mutation_rate=1.0,  # Always mutate
            crossover_rate=0.0,  # Never crossover
            seed=42,
        )

        # Find mutated patterns
        mutated = [p for p in final if p.generation_method == "mutated"]

        # All mutated patterns should have parents
        for p in mutated:
            assert len(p.parent_ids) > 0
            # Parent should be in initial population
            assert any(parent in [orig.id for orig in initial] for parent in p.parent_ids)
