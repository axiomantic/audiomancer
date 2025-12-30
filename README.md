# audiomancer

MCP server for AI-assisted music production. Manages sample libraries, analyzes audio, generates patterns, and integrates with TidalCycles live coding.

## Table of Contents

- [What is audiomancer?](#what-is-audiomancer)
- [Workflows](#workflows)
  - [Sample Library Management](#workflow-sample-library-management)
  - [Pattern Generation](#workflow-pattern-generation)
  - [Sample Discovery](#workflow-sample-discovery)
- [Installation](#installation)
- [Quick Reference](#quick-reference)
- [MCP Tools](#mcp-tools)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Python API](#python-api)
- [Project Structure](#project-structure)
- [Testing](#testing)

## What is audiomancer?

Audiomancer gives AI assistants deep integration with music production workflows. Instead of just chatting about music, the AI can:

- **Browse and enable sample packs** from Google Drive without you leaving the conversation
- **Generate TidalCycles patterns** using your actual sample library (not generic "bd" and "sn")
- **Find similar samples** using audio embeddings and semantic search
- **Analyze audio files** for BPM, key, spectral features, and more

It's designed for TidalCycles live coding but the analysis and search features work for any DAW workflow.

### Architecture

```
Google Drive (sample packs)
        |
        | MCP: enable_pack, disable_pack
        v
+------------------+     +------------------+
|  samples/        | --> |  library/        |  (symlinks)
|  (local cache)   |     |  (SuperDirt)     |
+------------------+     +------------------+
        |
        | MCP: generate_pattern (with sample_lookup)
        v
+------------------+
|  TidalCycles     |  d1 $ sound "808dk_bd 808dk_bd ~ 808dk_sn"
+------------------+
```

## Workflows

### Workflow: Sample Library Management

**Goal**: Enable sample packs from Google Drive for use in TidalCycles.

```
You: "What sample packs do I have?"

AI: [calls list_packs]
    You have 47 packs available:
    - 808 Drum Kit (4 files, 2.1 MB) - remote
    - Vinyl House Drums (12 files, 8.4 MB) - remote
    - Tech Loops 125 (6 files, 15.2 MB) - enabled
    ...

You: "Enable the 808 Drum Kit"

AI: [calls enable_pack "808 Drum Kit"]
    Enabled 808 Drum Kit:
    - Copied 4 files to samples/
    - Created symlinks in library/
    - Sample IDs: 808dk_bd, 808dk_sn, 808dk_hh

    Restart SuperDirt to load: Ctrl+Enter on start_superdirt.scd

You: "What kicks do I have now?"

AI: [calls list_enabled_samples, filters by category]
    Enabled kicks (bd):
    - 808dk_bd (2 variations)
    - vihodr_bd (1 variation)
```

**Pack Status**:
- `remote` - On Google Drive, not cached locally
- `cached` - Copied to samples/, but not enabled (no symlinks)
- `enabled` - Active in library/, SuperDirt can load it

### Workflow: Pattern Generation

**Goal**: Generate TidalCycles patterns using your enabled samples.

```
You: "Generate a techno drum pattern at 130 BPM"

AI: [calls generate_pattern with sample_lookup]
    Generated 4-bar techno pattern:

    d1 $ sound "808dk_bd 808dk_bd ~ 808dk_bd" # speed 1.05
    d2 $ sound "808dk_sn" # n (irand 3) # gain 0.9
    d3 $ sound "808dk_hh*8" # gain 0.7 # pan (rand)

You: "Make the hats more sparse"

AI: [modifies pattern]
    d3 $ sound "808dk_hh(5,8)" # gain 0.7

You: "Add some variation to the kick"

AI: [adds pattern variation]
    d1 $ sound "808dk_bd(<3 4>,8)" # speed (range 0.95 1.1 $ slow 4 sine)
```

The AI uses your actual sample IDs (like `808dk_bd`) instead of generic names because it queries your enabled library.

### Workflow: Sample Discovery

**Goal**: Find samples by description or similarity.

```
You: "Find samples similar to this kick" [with sample ID or path]

AI: [calls find_similar]
    Similar to 808dk_bd:
    1. vihodr_bd (0.92 similarity) - warmer, more sub
    2. techse_bd (0.87 similarity) - harder attack
    3. dnbpk_bd (0.81 similarity) - longer decay

You: "Search for dark ambient pads"

AI: [calls search_samples]
    Found 3 matching samples:
    - ambpk_pad (key: Dm, 8.2s)
    - drkam_pad (key: Am, 12.1s)
    ...
```

## Installation

```bash
# Clone and install
git clone https://github.com/youruser/audiomancer
cd audiomancer
pip install -e ".[dev]"

# Initialize config and data directories
audiomancer init

# Check dependencies
audiomancer doctor
```

### Requirements

- Python 3.10+
- SuperCollider (for SynthDef parsing)

### Claude Code / Claude Desktop Setup

Add to your MCP config:

**Claude Code** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "audiomancer": {
      "command": "audiomancer",
      "args": ["serve"]
    }
  }
}
```

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "audiomancer": {
      "command": "audiomancer",
      "args": ["serve"]
    }
  }
}
```

## Quick Reference

### Things You Can Ask

| Request | What Happens |
|---------|--------------|
| "What sample packs do I have?" | Lists all packs with status |
| "Enable the 808 kit" | Copies files, creates symlinks |
| "Disable the 808 kit" | Removes symlinks, keeps cache |
| "Search for dark kicks" | Text + semantic search |
| "Find samples like this one" | Embedding similarity search |
| "Generate a house drum pattern" | Creates TidalCycles code |
| "Analyze this sample" | Returns BPM, key, features |
| "What synths are available?" | Lists parsed SynthDefs |

### Sample Categories

When enabling packs, samples are auto-categorized:

| Category | Detected From | Type |
|----------|---------------|------|
| `bd` | kick, bassdrum, bd | drum |
| `sn` | snare, sd | drum |
| `hh` | hihat, hh, hat | drum |
| `oh` | open hat, oh | drum |
| `cp` | clap, handclap | drum |
| `perc` | perc, shaker, conga | perc |
| `bass` | bass, sub | bass |
| `synth` | synth, lead, pad | melodic |
| `fx` | fx, riser, impact | fx |
| `vox` | vocal, vox | vocal |
| `lp` | loop, drumloop | loop |

## MCP Tools

### Library Management (7 tools)

| Tool | Description |
|------|-------------|
| `list_packs` | List all packs from source with status |
| `search_packs` | Search packs by name pattern |
| `get_pack_status` | Get detailed pack info |
| `enable_pack` | Enable pack (copy + symlink) |
| `disable_pack` | Disable pack (remove symlinks) |
| `purge_pack` | Remove from cache entirely |
| `list_enabled_samples` | List enabled sample IDs |

### Analysis & Search (4 tools)

| Tool | Description |
|------|-------------|
| `search_samples` | Search by text, instrument, BPM, key |
| `find_similar` | Find samples similar to given sample |
| `describe_sample` | Get full metadata for a sample |
| `analyze_file` | Analyze new audio file |

### Generation & Synths (3 tools)

| Tool | Description |
|------|-------------|
| `generate_pattern` | Generate drum/melody/bass pattern |
| `list_synths` | List available SynthDefs |
| `get_synth` | Get SynthDef details |

### Stats (1 tool)

| Tool | Description |
|------|-------------|
| `get_stats` | Library statistics |

## CLI Commands

```bash
audiomancer init              # Initialize config and data directories
audiomancer doctor            # Check all dependencies
audiomancer serve             # Start MCP server

audiomancer scan ~/Samples    # Scan and import sample folders
audiomancer search "dark kick" # Search from CLI
audiomancer stats             # Library statistics
audiomancer benchmark         # Run performance benchmarks
```

## Configuration

Config file: `~/.config/audiomancer/config.yaml`

```yaml
# Sample library paths
library:
  source_dir: ~/Library/CloudStorage/GoogleDrive/Samples  # Where packs live
  project_root: ~/Development/my-music                     # Project with samples/ and library/
  auto_analyze: true
  max_file_size_mb: 10
  copy_workers: 16

# Analysis settings
analysis:
  sample_rate: 44100

# Embedding model
models:
  embeddings: musicnn  # musicnn, vggish, openl3

# Sample sources (for scanning)
sources:
  samples:
    - ~/Music/Samples
  synths:
    - ~/synths
```

### Project Structure Expected

```
{project_root}/
├── samples/           # Local cache (copied from source)
├── library/           # Active samples (symlinks to samples/)
├── session.tidal      # TidalCycles session
└── start_superdirt.scd
```

## Python API

### Pattern Generation

```python
from audiomancer.generators import generate_drums, generate_melody, generate_bass

# Generate patterns (uses Euclidean rhythms, no ML)
drums = generate_drums(style="techno", bpm=130, bars=4)
melody = generate_melody(key="Am", scale="minor", bpm=130, bars=4)
bass = generate_bass(key="Am", bpm=130, bars=4)

# Access generated code
print(drums.tidal_code)   # d1 $ sound "bd bd ~ bd" ...
print(drums.midi_data)    # bytes
```

### Audio Analysis

```python
from audiomancer.analyzers import (
    get_basic_metadata,
    extract_spectral_features,
    extract_rhythm_features,
    extract_audio_embedding
)
import librosa

audio, sr = librosa.load("kick.wav", sr=None)

basic = get_basic_metadata(Path("kick.wav"))
# {'duration_ms', 'sample_rate', 'channels', 'file_hash', ...}

spectral = extract_spectral_features(audio, sr)
# {'spectral_centroid', 'spectral_bandwidth', 'rms_energy', ...}

rhythm = extract_rhythm_features(audio, sr)
# {'bpm', 'bpm_confidence', 'is_loop', ...}

embedding = extract_audio_embedding(audio, sr)
# 128-dim vector for similarity search
```

### Storage & Search

```python
from audiomancer.storage.unified import UnifiedSampleStorage

storage = UnifiedSampleStorage("samples.db", "embeddings/")

# Add sample with embedding
sample_id = storage.add_sample_with_embedding(metadata, embedding)

# Find similar
for sample, distance in storage.find_similar(sample_id, limit=10):
    print(f"{sample['file_path']}: {distance:.3f}")
```

## Project Structure

```
src/audiomancer/
├── analyzers/       # Audio analysis (Essentia, librosa)
├── converters/      # MIDI ↔ TidalCycles ↔ SuperCollider
├── generators/      # Pattern generation (algorithmic)
├── library/         # Sample pack management (NEW)
│   ├── manager.py   # LibraryManager class
│   ├── scanner.py   # Category detection, file scanning
│   ├── schema.py    # TypedDict definitions
│   └── interfaces.py # Protocol definitions
├── storage/         # SQLite + LanceDB
├── server.py        # MCP server (15 tools)
├── cli.py           # Typer CLI
├── config.py        # Pydantic config
└── errors.py        # Error hierarchy
```

## Testing

```bash
pytest                        # All tests (597 tests)
pytest tests/unit/            # Fast unit tests
pytest tests/unit/library/    # Library module tests (62 tests)
pytest --cov=audiomancer      # With coverage
```

## License

MIT
