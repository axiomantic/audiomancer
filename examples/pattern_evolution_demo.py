#!/usr/bin/env python3
"""Pattern evolution demo.

Demonstrates generating patterns, evolving them through mutation and crossover,
and converting between formats.
"""

from audiomancer.generators.patterns import generate_drums, generate_melody, humanize
from audiomancer.generators.evolution import EvolutionEngine
from audiomancer.converters.midi_tidal import tidal_to_midi, merge_tidal_patterns


def demo_basic_generation():
    """Demonstrate basic pattern generation."""
    print("=" * 60)
    print("BASIC PATTERN GENERATION")
    print("=" * 60)

    # Generate drum patterns with different styles
    house_drums = generate_drums(style="house", bpm=125, bars=4)
    print(f"\nHouse drums (ID: {house_drums.id}):")
    print(f"  {house_drums.tidal_code}")

    techno_drums = generate_drums(style="techno", bpm=130, bars=4)
    print(f"\nTechno drums (ID: {techno_drums.id}):")
    print(f"  {techno_drums.tidal_code}")

    # Generate melody
    melody = generate_melody(key="Am", scale="minor", bpm=120, bars=4)
    print(f"\nMelody in A minor (ID: {melody.id}):")
    print(f"  {melody.tidal_code}")

    return house_drums, techno_drums, melody


def demo_evolution(house_drums, techno_drums):
    """Demonstrate pattern evolution."""
    print("\n" + "=" * 60)
    print("PATTERN EVOLUTION")
    print("=" * 60)

    engine = EvolutionEngine()

    # Store original patterns
    engine.store_pattern(house_drums)
    engine.store_pattern(techno_drums)

    # Mutate house pattern
    print(f"\nMutating house pattern (amount=0.3, seed=42)...")
    mutated_house = engine.mutate_pattern(house_drums, amount=0.3, seed=42)
    engine.store_pattern(mutated_house)
    print(f"  Original: {house_drums.tidal_code}")
    print(f"  Mutated:  {mutated_house.tidal_code}")
    print(f"  Parent IDs: {mutated_house.parent_ids}")

    # Crossover house and techno
    print(f"\nCrossing over house and techno patterns...")
    hybrid = engine.crossover_patterns(house_drums, techno_drums, seed=42)
    engine.store_pattern(hybrid)
    print(f"  Parent A: {house_drums.tidal_code}")
    print(f"  Parent B: {techno_drums.tidal_code}")
    print(f"  Hybrid:   {hybrid.tidal_code}")
    print(f"  Parent IDs: {hybrid.parent_ids}")

    # Create multi-generation lineage
    print(f"\nCreating multi-generation lineage...")
    gen1 = engine.mutate_pattern(hybrid, amount=0.2, seed=100)
    engine.store_pattern(gen1)

    gen2 = engine.mutate_pattern(gen1, amount=0.2, seed=200)
    engine.store_pattern(gen2)

    gen3 = engine.mutate_pattern(gen2, amount=0.2, seed=300)
    engine.store_pattern(gen3)

    lineage = engine.get_lineage(gen3.id)
    print(f"  Lineage chain ({len(lineage)} generations):")
    for i, pattern_id in enumerate(lineage):
        print(f"    {i}: {pattern_id}")

    return engine, hybrid


def demo_population_evolution(engine):
    """Demonstrate population evolution."""
    print("\n" + "=" * 60)
    print("POPULATION EVOLUTION")
    print("=" * 60)

    # Create initial population
    print("\nCreating initial population of 4 drum patterns...")
    population = [
        generate_drums(style="house", bpm=120),
        generate_drums(style="techno", bpm=128),
        generate_drums(style="breakbeat", bpm=140),
        generate_drums(style="trap", bpm=150),
    ]

    for p in population:
        engine.store_pattern(p)
        print(f"  {p.id}: {p.tidal_code}")

    # Evolve population
    print("\nEvolving population (5 generations, mutation=0.3, crossover=0.2)...")
    final_population = engine.evolve_population(
        population=population,
        generations=5,
        mutation_rate=0.3,
        crossover_rate=0.2,
        seed=42,
    )

    print(f"\nEvolution complete:")
    print(f"  Initial: {len(population)} patterns")
    print(f"  Final:   {len(final_population)} patterns")

    # Show some evolved patterns
    print("\nSample evolved patterns:")
    for i, p in enumerate(final_population[-5:], 1):
        print(f"  {i}. {p.id} ({p.generation_method}, parents: {len(p.parent_ids)})")
        print(f"     {p.tidal_code}")


def demo_humanization(house_drums):
    """Demonstrate pattern humanization."""
    print("\n" + "=" * 60)
    print("HUMANIZATION")
    print("=" * 60)

    # Add human feel to pattern
    print("\nAdding human timing variations...")
    humanized = humanize(house_drums, amount=0.5)
    print(f"  Original:  {house_drums.tidal_code}")
    print(f"  Humanized: {humanized.tidal_code}")
    print(f"  Parent ID: {humanized.parent_ids}")
    print(f"  Amount:    {humanized.mutation_amount}")


def demo_midi_conversion(house_drums, techno_drums, melody):
    """Demonstrate MIDI conversion."""
    print("\n" + "=" * 60)
    print("MIDI CONVERSION")
    print("=" * 60)

    # Convert Tidal to MIDI
    print("\nConverting patterns to MIDI...")
    drums_midi = tidal_to_midi(house_drums.tidal_code, bpm=125)
    melody_midi = tidal_to_midi(melody.tidal_code, bpm=120)

    print(f"  House drums MIDI: {len(drums_midi)} bytes")
    print(f"  Melody MIDI:      {len(melody_midi)} bytes")

    # Merge patterns
    print("\nMerging patterns...")
    patterns_to_merge = [
        house_drums.tidal_code,
        techno_drums.tidal_code,
    ]
    merged = merge_tidal_patterns(patterns_to_merge)
    print(f"  Merged pattern:")
    print(f"    {merged}")


def demo_pattern_metadata(house_drums):
    """Demonstrate pattern metadata."""
    print("\n" + "=" * 60)
    print("PATTERN METADATA")
    print("=" * 60)

    print(f"\nPattern: {house_drums.id}")
    print(f"  Type:         {house_drums.type}")
    print(f"  BPM:          {house_drums.bpm}")
    print(f"  Bars:         {house_drums.bars}")
    print(f"  Generation:   {house_drums.generation_method}")
    print(f"  Parents:      {house_drums.parent_ids}")
    print(f"  Created:      {house_drums.created_at}")

    # Serialize to dict
    data = house_drums.to_dict()
    print(f"\nSerialized to dict ({len(data)} fields):")
    for key, value in data.items():
        if key != "midi_data":  # Don't print binary data
            print(f"  {key}: {value}")


def main():
    """Run all demos."""
    print("\n🎵 AUDIOMANCER PATTERN GENERATION DEMO 🎵\n")

    try:
        # Basic generation
        house, techno, melody = demo_basic_generation()

        # Evolution
        engine, hybrid = demo_evolution(house, techno)

        # Population evolution
        demo_population_evolution(engine)

        # Humanization
        demo_humanization(house)

        # MIDI conversion
        demo_midi_conversion(house, techno, melody)

        # Metadata
        demo_pattern_metadata(house)

        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print("\nAll pattern generation features demonstrated successfully!")
        print("\nNote: This demo uses placeholder implementations.")
        print("Install Magenta for full ML-based generation:")
        print("  pip install magenta tensorflow")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print(f"Error details: {getattr(e, 'details', {})}")
        raise


if __name__ == "__main__":
    main()
