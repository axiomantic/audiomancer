#!/usr/bin/env python3
"""Demonstration of SynthDef evolution with genetic algorithms.

This example shows how to:
1. Generate synths from templates
2. Mutate existing synths
3. Breed synths to create hybrids
4. Track lineage and rate synths
5. Evolve a population over multiple generations

Run this to see Darwin's evolutionary synth breeding in action!
"""

from pathlib import Path
from audiomancer.analyzers.synthdef import parse_synthdef
from audiomancer.generators import (
    generate_synth,
    mutate_synth,
    breed_synths,
    record_synth,
    rate_synth,
    get_synth_lineage,
    get_top_rated,
    get_generation_stats,
)


def main():
    print("=" * 80)
    print("DARWIN: Evolutionary SynthDef Breeding")
    print("=" * 80)
    print()

    # ========================================================================
    # 1. Generate synths from templates
    # ========================================================================
    print("1. GENERATING SYNTHS FROM TEMPLATES")
    print("-" * 80)

    acid_bass = generate_synth(
        description="acid bass with filter sweep",
        category="bass"
    )
    print(f"✓ Generated: {acid_bass.name}")
    print(f"  Category: {acid_bass.category}")
    print(f"  Mutations: {acid_bass.mutation_log}")
    print()

    warm_lead = generate_synth(
        description="warm bright lead",
        category="lead"
    )
    print(f"✓ Generated: {warm_lead.name}")
    print(f"  Category: {warm_lead.category}")
    print()

    # ========================================================================
    # 2. Parse existing SynthDef and mutate it
    # ========================================================================
    print("2. MUTATING EXISTING SYNTHDEF")
    print("-" * 80)

    # Find test fixtures
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "synths"
    tb303_path = fixtures_dir / "tb303.scd"

    if tb303_path.exists():
        tb303 = parse_synthdef(tb303_path)
        print(f"✓ Loaded: {tb303.name}")
        print(f"  UGens: {', '.join(tb303.ugens_used[:5])}...")
        print()

        # Create 3 mutations with different amounts
        mutant1 = mutate_synth(tb303, amount=0.3, seed=42)
        print(f"✓ Mutant 1 ({mutant1.name})")
        print(f"  Mutations: {mutant1.mutation_log}")
        print()

        mutant2 = mutate_synth(tb303, amount=0.6, seed=43)
        print(f"✓ Mutant 2 ({mutant2.name})")
        print(f"  Mutations: {mutant2.mutation_log}")
        print()

        mutant3 = mutate_synth(tb303, amount=0.9, seed=44)
        print(f"✓ Mutant 3 ({mutant3.name})")
        print(f"  Mutations: {mutant3.mutation_log}")
        print()

        # ====================================================================
        # 3. Breed two synths to create a hybrid
        # ====================================================================
        print("3. BREEDING SYNTHS (CROSSOVER)")
        print("-" * 80)

        simple_path = fixtures_dir / "simple_sine.scd"
        if simple_path.exists():
            simple = parse_synthdef(simple_path)

            hybrid = breed_synths(tb303, simple, seed=100)
            print(f"✓ Hybrid: {hybrid.name}")
            print(f"  Parents: {', '.join(hybrid.parent_ids)}")
            print(f"  Crossover: {hybrid.mutation_log}")
            print()

            # Show partial code
            print("  Generated code snippet:")
            lines = hybrid.source_code.split('\n')[:10]
            for line in lines:
                print(f"    {line}")
            print("    ...")
            print()

        # ====================================================================
        # 4. Track lineage and rate synths
        # ====================================================================
        print("4. LINEAGE TRACKING & FITNESS SCORING")
        print("-" * 80)

        # Record synths in lineage database
        record_synth(
            synth_id="synt_tb303",
            name=tb303.name,
            parent_ids=[],
            generation_method="original",
            mutation_log=["Original TB-303"],
        )

        record_synth(
            synth_id="synt_m1",
            name=mutant1.name,
            parent_ids=["synt_tb303"],
            generation_method="mutation",
            mutation_log=mutant1.mutation_log,
        )

        record_synth(
            synth_id="synt_m2",
            name=mutant2.name,
            parent_ids=["synt_tb303"],
            generation_method="mutation",
            mutation_log=mutant2.mutation_log,
        )

        # Rate the synths (simulating user feedback)
        rate_synth("synt_tb303", score=5, notes="Classic acid sound")
        rate_synth("synt_m1", score=4, notes="Good variation")
        rate_synth("synt_m2", score=5, notes="Perfect mutation!")

        print("✓ Recorded synths in lineage database")
        print()

        # Get lineage for mutant2
        lineage = get_synth_lineage("synt_m2")
        print(f"Lineage for {mutant2.name}:")
        print(f"  Ancestors: {lineage['ancestors']}")
        print(f"  Generation: {lineage['generation']}")
        print(f"  Rating: {lineage['record']['user_rating']}/5")
        print()

        # Get top rated synths
        top_rated = get_top_rated(limit=3)
        print("Top rated synths:")
        for i, synth in enumerate(top_rated, 1):
            print(f"  {i}. {synth['name']} - {synth['user_rating']}/5 stars")
            if synth['user_notes']:
                print(f"     \"{synth['user_notes']}\"")
        print()

        # Get generation statistics
        stats = get_generation_stats()
        print("Generation statistics:")
        print(f"  Total synths: {stats['total_synths']}")
        print(f"  Original: {stats['original_synths']}")
        print(f"  Mutated: {stats['mutated_synths']}")
        print(f"  Crossover: {stats['crossover_synths']}")
        print(f"  Max generation: {stats['max_generation']}")
        print(f"  Average rating: {stats['avg_rating']}/5")
        print()

    # ========================================================================
    # 5. Evolution workflow demonstration
    # ========================================================================
    print("5. EVOLUTIONARY WORKFLOW")
    print("-" * 80)
    print("Example multi-generation evolution:")
    print()
    print("Generation 0 (Original):")
    print("  tb303 [rating: 5/5]")
    print()
    print("Generation 1 (Mutations):")
    print("  ├─ tb303_m42  [Saw → Pulse, cutoff: 1200 → 1440]")
    print("  ├─ tb303_m43  [Added LFO modulation to cutoff]")
    print("  └─ tb303_m44  [Saw → Pulse, Added distortion]")
    print()
    print("Generation 2 (Breed best mutants):")
    print("  └─ tb303_m42_x_tb303_m43 [Hybrid of top 2]")
    print()
    print("Darwin's advice:")
    print("  1. Generate diverse initial population")
    print("  2. Mutate with varying amounts (0.3-0.8)")
    print("  3. Rate synths to guide evolution")
    print("  4. Breed highest-rated synths")
    print("  5. Iterate for 5-10 generations")
    print("  6. Best sounds emerge through selection!")
    print()

    # ========================================================================
    # 6. Template showcase
    # ========================================================================
    print("6. TEMPLATE SHOWCASE")
    print("-" * 80)

    templates = [
        ("bass", "Deep sub bass"),
        ("lead", "Bright melodic synth"),
        ("pad", "Atmospheric sustained sound"),
        ("drum", "Percussive hit"),
        ("fx", "Noise texture"),
    ]

    for category, description in templates:
        synth = generate_synth(f"test {category}", category=category)
        print(f"✓ {category.upper():6} template - {description}")
        print(f"  Name: {synth.name}")
        print(f"  Controls: {', '.join([c.name for c in synth.controls[:5]])}...")
        print()

    print("=" * 80)
    print("Evolution complete! Your synths await in the primordial soup.")
    print("=" * 80)


if __name__ == "__main__":
    main()
