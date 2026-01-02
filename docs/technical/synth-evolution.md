# SynthDef Evolution System

Darwin's evolutionary algorithm for breeding the perfect synth sounds through genetic operations on SuperCollider SynthDefs.

## Overview

The audiomancer synth evolution system provides:

1. **Generation**: Create new synths from templates or natural language descriptions
2. **Mutation**: Evolve existing synths through genetic mutations (UGen swapping, parameter tweaking, etc.)
3. **Crossover**: Breed two parent synths to create hybrid children
4. **Lineage Tracking**: Track evolutionary history, generations, and user ratings
5. **Fitness Scoring**: Rate synths to guide evolution toward better sounds

## Architecture

```
audiomancer/
├── src/audiomancer/generators/
│   ├── synths.py          # Generation, mutation, crossover logic
│   ├── lineage.py         # Lineage tracking and fitness scoring
│   └── templates/         # Template SynthDefs
│       ├── bass_template.scd
│       ├── lead_template.scd
│       ├── pad_template.scd
│       ├── drum_template.scd
│       └── fx_template.scd
├── tests/unit/
│   ├── test_synth_generator.py  # 46 tests for generation/mutation
│   └── test_lineage.py          # 26 tests for lineage tracking
└── examples/
    └── synth_evolution_demo.py  # Complete demonstration
```

## Quick Start

### Basic Generation

```python
from audiomancer.generators import generate_synth

# Generate from template
bass = generate_synth("acid bass with filter sweep", category="bass")
print(bass.name)          # acid_bass_001
print(bass.source_code)   # Full SuperCollider code
```

### Mutation

```python
from audiomancer.generators import mutate_synth
from audiomancer.analyzers.synthdef import parse_synthdef
from pathlib import Path

# Load existing synth
tb303 = parse_synthdef(Path("synths/tb303.scd"))

# Mutate with 50% strength
variant = mutate_synth(tb303, amount=0.5, seed=42)

print(variant.name)           # tb303_m42
print(variant.mutation_log)   # ['Saw → Pulse', 'cutoff: 1200 → 1440', ...]
```

### Crossover (Breeding)

```python
from audiomancer.generators import breed_synths

# Breed two synths
child = breed_synths(tb303, juno_pad, seed=100)

print(child.name)        # tb303_x_juno_pad
print(child.parent_ids)  # ['tb303', 'juno_pad']
```

### Lineage Tracking

```python
from audiomancer.generators import (
    record_synth,
    rate_synth,
    get_synth_lineage,
    get_top_rated,
)

# Record synth
record_synth(
    synth_id="synt_m1",
    name="tb303_m1",
    parent_ids=["tb303"],
    generation_method="mutation",
    mutation_log=["Saw → Pulse"],
)

# Rate synth
rate_synth("synt_m1", score=5, notes="Perfect acid sound!")

# Get lineage
lineage = get_synth_lineage("synt_m1")
print(lineage["ancestors"])   # ['tb303']
print(lineage["generation"])  # 1

# Get top rated
top = get_top_rated(limit=5, min_rating=4)
```

## Mutation Operations

The `mutate_synth` function applies probabilistic mutations:

| Mutation Type | Probability | Description |
|--------------|-------------|-------------|
| Swap Oscillator | amount × 0.4 | Replace UGen (Saw → Pulse) |
| Swap Filter | amount × 0.3 | Replace filter (LPF → MoogFF) |
| Add Modulation | amount × 0.3 | Add LFO to parameter |
| Add Distortion | amount × 0.2 | Apply saturation/distortion |
| Modify Parameters | amount × 0.5 | Adjust defaults ±20% |
| Modify Envelope | amount × 0.2 | Change envelope times |

### UGen Categories for Substitution

```python
UGEN_CATEGORIES = {
    "oscillators": ["SinOsc", "Saw", "Pulse", "Tri", "VarSaw", "LFSaw", "Blip"],
    "filters": ["LPF", "HPF", "BPF", "RLPF", "MoogFF", "BLowPass", "MoogLadder"],
    "distortion": ["tanh", "softclip", "Shaper", "CrossoverDistortion", "Decimator"],
    "envelopes": ["Perc", "ADSR", "ASR", "Linen"],
    "modulation": ["LFO", "SinOsc.kr", "LFNoise1", "LFTri.kr", "LFNoise0"],
}
```

## Generation from Natural Language

The `generate_synth` function interprets description keywords:

| Keyword | Effect |
|---------|--------|
| `acid` | Adds resonant filter with envelope modulation |
| `warm` | Uses saw wave with low-pass filter |
| `bright` | Uses pulse wave with high cutoff |
| `filtered` | Adds MoogFF or RLPF filter |
| `distorted` | Adds distortion/saturation |
| `sweep` | Adds LFO modulation to filter |

### Example

```python
synth = generate_synth(
    description="warm acid bass with filter sweep",
    category="bass"
)
# Result: Uses saw wave, adds MoogFF filter, adds LFO to cutoff
```

## Template Categories

Five base templates are provided:

### Bass Template
- Low-frequency synth with resonant filter
- Default freq: 55 Hz
- RLPF filter with envelope modulation
- Rich harmonics from saw wave

### Lead Template
- Bright melodic synth
- ADSR envelope
- Pulse wave oscillator
- High cutoff for brightness

### Pad Template
- Sustained atmospheric sound
- Long ASR envelope (slow attack/release)
- Detuned oscillators for thickness
- Soft filter

### Drum Template
- Percussive synth without gate
- Mix of sine (kick) and noise (snap)
- Short percussive envelope
- No sustain

### FX Template
- Noise and texture generator
- Dust (sparse impulses)
- Resonant filter for character
- Short decay

## Crossover Strategy

The `breed_synths` function combines parents:

1. **Extract Sections**:
   - Oscillator code from parent A or B (random)
   - Filter code from the other parent
   - Effects mixed randomly

2. **Combine Controls**:
   - Merge unique controls from both parents
   - Average numeric defaults for shared controls

3. **Build Child**:
   - Create new SynthDef with combined features
   - Preserve essential structure (Out, envelope)

## Lineage Database

Synth lineage is persisted in `~/.audiomancer/lineage.json`:

```json
{
  "synt_tb303": {
    "id": "synt_tb303",
    "name": "tb303",
    "parent_ids": [],
    "generation_method": "original",
    "mutation_log": ["Original TB-303"],
    "user_rating": 5,
    "user_notes": "Classic acid sound",
    "created_at": "2025-01-15T10:30:00"
  },
  "synt_m1": {
    "id": "synt_m1",
    "name": "tb303_m1",
    "parent_ids": ["synt_tb303"],
    "generation_method": "mutation",
    "mutation_log": ["Saw → Pulse", "cutoff: 1200 → 1440"],
    "user_rating": 4,
    "user_notes": "Good variation",
    "created_at": "2025-01-15T10:31:00"
  }
}
```

## Evolution Workflow

Recommended process for multi-generation evolution:

```
Generation 0 (Seed Population)
  ├─ tb303 [original]
  ├─ juno [original]
  └─ dx7  [original]
         ↓ Rate synths
         ↓ Select top 50%
         ↓
Generation 1 (Mutations)
  ├─ tb303_m1 [mutation, amount=0.3]
  ├─ tb303_m2 [mutation, amount=0.5]
  ├─ juno_m1  [mutation, amount=0.4]
  └─ juno_m2  [mutation, amount=0.6]
         ↓ Rate mutants
         ↓ Select top rated
         ↓
Generation 2 (Crossover)
  ├─ tb303_m2_x_juno_m1 [breed best mutants]
  └─ tb303_m1_x_juno_m2 [breed other top pair]
         ↓ Rate hybrids
         ↓ Iterate...
         ↓
Generation N
  └─ Perfect evolved synth!
```

### Darwin's Advice

1. **Start with diversity**: Use multiple templates or import different originals
2. **Vary mutation amounts**: 0.3 for subtle, 0.8 for drastic changes
3. **Rate consistently**: Fitness scoring guides evolution
4. **Breed the best**: Crossover only top-rated synths
5. **Iterate 5-10 generations**: Good sounds emerge over time
6. **Listen and select**: Your ears are the ultimate fitness function!

## API Reference

### Main Functions

#### `generate_synth(description, base_synth=None, category="bass")`
Generate new SynthDef from description or template.

**Args**:
- `description` (str): Natural language description
- `base_synth` (SynthDefInfo, optional): Existing synth to modify
- `category` (str): One of: bass, lead, pad, drum, fx

**Returns**: `GeneratedSynth` with source code and metadata

#### `mutate_synth(synth, amount=0.3, seed=None)`
Mutate existing SynthDef.

**Args**:
- `synth` (SynthDefInfo): Source synth to mutate
- `amount` (float): Mutation strength 0.0-1.0
- `seed` (int, optional): Random seed for deterministic testing

**Returns**: `GeneratedSynth` with mutations logged

#### `breed_synths(synth_a, synth_b, seed=None)`
Crossover two synths to create hybrid.

**Args**:
- `synth_a` (SynthDefInfo): First parent
- `synth_b` (SynthDefInfo): Second parent
- `seed` (int, optional): Random seed

**Returns**: `GeneratedSynth` combining both parents

### Lineage Functions

#### `record_synth(synth_id, name, parent_ids, generation_method, mutation_log)`
Record synth in lineage database.

#### `rate_synth(synth_id, score, notes=None)`
Rate synth (1-5 stars) with optional notes.

#### `get_synth_lineage(synth_id)`
Get full ancestry and descendants.

**Returns**: Dict with ancestors, descendants, generation, family_tree

#### `get_top_rated(limit=10, min_rating=None)`
Get highest-rated synths.

**Returns**: List of synth records sorted by rating

#### `get_generation_stats()`
Get statistics about evolutionary generations.

**Returns**: Dict with counts, depths, and ratings

## Implementation Details

### Code Structure Preservation

All mutations preserve essential SynthDef structure:

```supercollider
SynthDef(\name, {
    |params|           // Parameters preserved
    var variables;     // Variables may be added

    // Envelope (preserved)
    // Oscillator (may be swapped)
    // Filter (may be swapped/added)
    // Effects (may be added)

    Out.ar(out, sig);  // Output preserved
}).add;
```

### Mutation Safety

- Parameter declarations are preserved
- Essential variables (sig, env) are maintained
- Out.ar statements remain intact
- .add terminator is kept
- Syntax validated through regex checks

### Lineage Persistence

- JSON database at `~/.audiomancer/lineage.json`
- Automatic saving on modifications
- Datetime serialization for timestamps
- Singleton pattern for global tracker

## Testing

72 comprehensive tests cover:

- Template generation (all 5 categories)
- Mutation operations (all 6 types)
- Crossover breeding
- Lineage tracking and queries
- Database persistence
- Deterministic seeding
- Structure preservation

Run tests:
```bash
pytest tests/unit/test_synth_generator.py -v  # 46 tests
pytest tests/unit/test_lineage.py -v          # 26 tests
```

## Examples

See `examples/synth_evolution_demo.py` for complete workflow demonstration.

## Future Enhancements

Potential additions:

1. **Multi-parent crossover**: Blend 3+ synths
2. **Guided evolution**: Target specific sonic characteristics
3. **Automatic fitness**: Analyze spectral features for ratings
4. **Population algorithms**: Implement full genetic algorithm
5. **Neural evolution**: Use ML to predict good mutations
6. **Interactive GUI**: Visual synth designer with evolution
7. **SuperCollider validation**: Compile and test generated synths
8. **Sound similarity**: Find similar synths by timbre

## Credits

Inspired by:
- Genetic algorithms in music synthesis
- SuperCollider SynthDef architecture
- Evolutionary computation
- Darwin's natural selection

Created for the audiomancer project.
