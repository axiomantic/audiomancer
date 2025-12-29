# audiomancer - AI Agent Onboarding Guide

This document helps AI agents understand and work with the audiomancer codebase.

## What is audiomancer?

An MCP server that analyzes music production assets (samples, SynthDefs) and serves metadata to LLMs. It enables intelligent sound selection, pattern generation, and synth evolution.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Server (server.py)                    │
│                      7 tools for LLM access                      │
├─────────────────────────────────────────────────────────────────┤
│  Analyzers                      │  Storage                       │
│  ├── basic.py (metadata)        │  ├── db.py (SQLite)            │
│  ├── spectral.py (Essentia)     │  ├── vectors.py (LanceDB)      │
│  ├── rhythm.py (BPM)            │  └── unified.py (atomic ops)   │
│  ├── tonal.py (key)             │                                │
│  ├── classifier.py (ML)         │  Generators                    │
│  ├── embeddings.py (128-dim)    │  ├── patterns.py (algorithmic) │
│  └── synthdef.py (SC parser)    │  ├── synths.py (evolution)     │
│                                 │  └── lineage.py (tracking)     │
├─────────────────────────────────────────────────────────────────┤
│  Converters: midi_tidal.py, midi_sc.py                          │
├─────────────────────────────────────────────────────────────────┤
│  CLI: cli.py (Typer)  │  Config: config.py (Pydantic)           │
└─────────────────────────────────────────────────────────────────┘
```

## Key Principles

1. **Fail-fast**: No graceful degradation. Fail loudly with actionable fixes.
2. **Type safety**: All code uses type hints. Protocol classes define interfaces.
3. **Atomic operations**: Storage operations are all-or-nothing.
4. **128-dim embeddings**: All audio embeddings are exactly 128 dimensions, L2-normalized.

## Error Handling

All errors inherit from `AudiomancerError` and include a `details` dict:

```python
from audiomancer.errors import (
    AudiomancerError,      # Base class
    ConfigError,           # Config issues
    StorageError,          # Database errors
    SampleNotFoundError,   # Missing sample
    DuplicateSampleError,  # Hash collision
    AnalysisError,         # Analysis failed
    UnsupportedFormatError,# Bad audio format
    GenerationError,       # Generation failed
    ModelLoadError,        # ML model missing
    SynthDefError,         # Invalid SynthDef
    SubprocessTimeoutError # sclang timeout
)

# Errors have structured details
try:
    store.add(sample)
except DuplicateSampleError as e:
    print(e.existing_id)  # ID of existing sample
    print(e.details)      # {"existing_id": "...", "path": "..."}
```

## Storage Layer

### SampleStore (SQLite)

```python
from audiomancer.storage.db import SampleStore

store = SampleStore("samples.db")

# CRUD operations
sample_id = store.add(sample_metadata)  # Raises DuplicateSampleError on hash collision
store.add_batch(samples)                # Atomic - all or nothing
sample = store.get(sample_id)           # Returns None if not found
store.update(sample_id, {"bpm": 128})   # Returns True/False
store.delete(sample_id)                 # Returns True/False

# Search with filters
results = store.search(
    instrument_type="kick",
    bpm_min=120, bpm_max=130,
    key="C",
    mood=["dark"],
    limit=20, offset=0
)
```

### VectorStore (LanceDB)

```python
from audiomancer.storage.vectors import LanceDBVectorStore

vectors = LanceDBVectorStore(Path("embeddings/"))

# Store/retrieve 128-dim embeddings
vectors.add_embedding(sample_id, embedding)  # Raises ValueError if dim != 128
vectors.add_embeddings_batch([(id, emb), ...])

# Similarity search
similar = vectors.search_similar(
    query_embedding,
    limit=10,
    exclude_ids=["smpl_abc123"],
    distance_metric="cosine"  # or "l2"
)
# Returns: [(sample_id, distance), ...]
```

### UnifiedSampleStorage

```python
from audiomancer.storage.unified import UnifiedSampleStorage

storage = UnifiedSampleStorage(db_path, embeddings_path)

# Atomic operations (both succeed or both fail)
sample_id = storage.add_sample_with_embedding(sample, embedding)
storage.delete_sample(sample_id)  # Removes from both stores

# Similarity with metadata
similar = storage.find_similar(sample_id, limit=10)
# Returns: [(SampleMetadata, distance), ...]
```

## Analyzers

All analyzers follow the same pattern:

```python
import librosa
from audiomancer.analyzers import (
    get_basic_metadata,
    extract_spectral_features,
    extract_rhythm_features,
    extract_tonal_features,
    classify_instrument,
    extract_audio_embedding
)

# Load audio once
audio, sr = librosa.load("sample.wav", sr=None)

# Extract features
basic = get_basic_metadata(Path("sample.wav"))
# {'duration_ms', 'sample_rate', 'channels', 'bit_depth', 'file_size_bytes', 'file_hash'}

spectral = extract_spectral_features(audio, sr)
# {'spectral_centroid', 'spectral_bandwidth', 'spectral_rolloff', 'zero_crossing_rate', 'rms_energy', 'dynamic_range'}

rhythm = extract_rhythm_features(audio, sr)
# {'bpm', 'bpm_confidence', 'beat_positions', 'is_loop'}

tonal = extract_tonal_features(audio, sr)
# {'key', 'key_confidence', 'tuning_frequency', 'pitch_salience'}

classification = classify_instrument(audio, sr)
# {'instrument_type', 'instrument_confidence'}

embedding = extract_audio_embedding(audio, sr, model="musicnn")
# list[float] with exactly 128 dimensions, L2-normalized
```

## Generators

### Pattern Generation

```python
from audiomancer.generators.patterns import generate_drums, generate_melody
from audiomancer.generators.evolution import mutate_pattern, crossover_patterns

# Generate patterns
drums = generate_drums(style="techno", bpm=130, bars=4)
melody = generate_melody(key="Am", scale="minor", bpm=130, bars=4)

# Evolve patterns
mutant = mutate_pattern(drums, amount=0.5)
child = crossover_patterns(pattern_a, pattern_b)

# Access data
drums.midi_data     # bytes
drums.tidal_code    # str
drums.parent_ids    # list[str] for lineage
```

### SynthDef Evolution

```python
from audiomancer.analyzers.synthdef import parse_synthdef
from audiomancer.generators.synths import generate_synth, mutate_synth, breed_synths

# Parse existing
tb303 = parse_synthdef(Path("tb303.scd"))

# Generate from description
new_synth = generate_synth("acid bass with filter sweep", category="bass")

# Evolve
variant = mutate_synth(tb303, amount=0.5)
# Mutations logged: ['Saw → Pulse', 'Added tanh distortion']

child = breed_synths(synth_a, synth_b)
```

## Converters

```python
from audiomancer.converters.midi_tidal import midi_to_tidal, tidal_to_midi
from audiomancer.converters.midi_sc import midi_to_supercollider, supercollider_to_midi

# MIDI ↔ TidalCycles
tidal = midi_to_tidal(midi_bytes, bpm=130)
midi = tidal_to_midi('d1 $ sound "bd sd bd sd"', bpm=130)

# MIDI ↔ SuperCollider
sc = midi_to_supercollider(midi_bytes, synth_name="tb303", output_format="pbind")
midi = supercollider_to_midi(sc_code, bpm=130)
```

## MCP Server

The server exposes 7 tools. See `src/audiomancer/server.py`:

```python
# Tool implementations
async def search_samples(query, instrument_type, bpm_min, bpm_max, key, limit)
async def find_similar(sample_id, limit)
async def describe_sample(sample_id)
async def analyze_file(path)
async def list_synths(category)
async def get_synth(name)
async def get_stats()
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_db.py

# Run with verbose output
pytest -v tests/unit/test_db.py::test_add_duplicate_raises_error
```

Test fixtures are in `tests/fixtures/`:
- `samples/` - Generated test audio files
- `synths/` - Test SynthDefs (simple_sine.scd, tb303.scd)
- `midi/` - Test MIDI files

Golden files in `tests/golden/` define expected outputs for regression testing.

## Common Tasks

### Adding a new analyzer

1. Create `src/audiomancer/analyzers/new_analyzer.py`
2. Follow the pattern: `def extract_X_features(audio: np.ndarray, sr: int) -> dict`
3. Raise `AnalysisFailedError` on errors with `details` dict
4. Add to `src/audiomancer/analyzers/__init__.py`
5. Write tests in `tests/unit/test_new_analyzer.py`
6. Add golden file if needed

### Adding a new MCP tool

1. Add tool definition to `list_tools()` in `server.py`
2. Add handler in `call_tool()`
3. Implement async handler function
4. Return `TextContent` with JSON-formatted result
5. Add tests in `tests/integration/test_mcp_server.py`

### Running benchmarks

```bash
# Full benchmark suite
python benchmarks/run_benchmarks.py

# Check for performance regressions
python benchmarks/check_regression.py benchmarks/baseline.json

# Quick sanity check
python benchmarks/quick_test.py
```

## File Conventions

- **Imports**: Top-level, no function-level imports unless circular import issue
- **Type hints**: Required on all functions
- **Docstrings**: Required with examples for public functions
- **Error messages**: Include actionable fix suggestions
- **Tests**: Mirror source structure in `tests/unit/`

## Dependencies to Know

- `essentia.standard` - Audio feature extraction
- `librosa` - Audio loading (with native sample rate)
- `lancedb` - Vector similarity search
- `sqlalchemy` - SQL ORM
- `mido` - MIDI file handling and pattern generation
- `mcp` - Model Context Protocol SDK
- `typer` + `rich` - CLI framework

## Pattern Generation

Pattern generation uses algorithmic methods (no ML dependencies):

- **Euclidean rhythms**: Bjorklund's algorithm for drum patterns
- **Scale-based melody**: Random walks within musical scales
- **Style templates**: Pre-defined patterns for house, techno, breakbeat, etc.

All patterns output:
- MIDI data (bytes, via mido)
- TidalCycles code (string)
- SuperCollider Pbind code (string)
