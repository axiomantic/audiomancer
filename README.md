# audiomancer

MCP server for AI-assisted music production. Manages sample libraries, analyzes audio, generates patterns, and integrates with TidalCycles live coding.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
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
- [Development](#development)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

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

## Prerequisites

Before installing audiomancer, you need a working TidalCycles setup:

- **TidalCycles**: Live coding language and runtime
  - Installation guide: https://tidalcycles.org/docs/getting-started/installation/
- **SuperCollider**: Audio synthesis platform (required for TidalCycles)
  - Download: https://supercollider.github.io/downloads
- **VS Code TidalCycles Extension**: Editor integration
  - Extension: https://marketplace.visualstudio.com/items?itemName=tidalcycles.vscode-tidalcycles
- **ghcup**: Haskell toolchain manager (for TidalCycles)
  - Installation: https://www.haskell.org/ghcup/

Run `audiomancer doctor` after installation to verify all prerequisites are installed.

## Installation

```bash
# Clone and install
git clone https://github.com/youruser/audiomancer
cd audiomancer
pip install -e ".[dev]"

# Check dependencies (including TidalCycles setup)
audiomancer doctor
```

### Creating a New Project

```bash
# Create a new TidalCycles project with interactive setup
audiomancer init

# Or specify a directory
audiomancer init --path ~/my-music-project
```

The `init` command will:
1. Prompt for project name (defaults to directory name)
2. Prompt for sample source directory (e.g., Google Drive samples folder)
3. Create project structure with samples/ and library/ directories
4. Generate project-specific .audiomancer.yaml config file
5. Create TidalCycles session files (session.tidal, start_superdirt.scd)
6. Add Claude Code integration files (.mcp.json, CLAUDE.md)
7. Initialize git repository with .gitignore

### Requirements

- Python 3.10+
- SuperCollider (for SynthDef parsing)

### Claude Code Setup

```bash
# Use the full path to the venv's audiomancer binary
claude mcp add audiomancer --scope user -- /path/to/audiomancer/.venv/bin/audiomancer serve

# Example with actual path:
# claude mcp add audiomancer --scope user -- ~/Development/audiomancer/.venv/bin/audiomancer serve
```

### Claude Desktop Setup

Add to `~/.config/claude/claude_desktop_config.json`:

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
audiomancer init              # Create new TidalCycles project (interactive)
audiomancer init --path PATH  # Create project at specific path
audiomancer doctor            # Check all dependencies
audiomancer serve             # Start MCP server

audiomancer scan ~/Samples    # Scan and import sample folders
audiomancer search "dark kick" # Search from CLI
audiomancer stats             # Library statistics
audiomancer benchmark         # Run performance benchmarks
```

## Configuration

Audiomancer uses a three-tier configuration system with inheritance:

```
1. Builtin defaults (hardcoded in config.py)
   ↓
2. Global config (~/.config/audiomancer/config.yaml)
   ↓ (overrides)
3. Project config (.audiomancer.yaml in project directory)
   ↓ (overrides)
Final merged configuration
```

### Configuration Files

**Global config** (`~/.config/audiomancer/config.yaml`):
- Shared settings across all projects
- Personal defaults (sample sources, analysis settings)
- Optional - if missing, uses builtin defaults

**Project config** (`.audiomancer.yaml` in project root):
- Project-specific overrides
- Auto-generated by `audiomancer init`
- Auto-detected when starting MCP server in a project directory
- Optional - if missing, uses global config or builtin defaults

### Example Global Config

`~/.config/audiomancer/config.yaml`:
```yaml
# Sample library paths
library:
  source_dir: ~/Library/CloudStorage/GoogleDrive/Samples  # Where packs live
  auto_analyze: true
  max_file_size_mb: 10
  copy_workers: 16

# Analysis settings
analysis:
  max_file_size_mb: 50
  embedding_dim: 128

# Sample sources (for scanning)
sources:
  samples:
    paths:
      - ~/Music/Samples
  synths:
    paths:
      - ~/synths

# Storage paths
storage:
  db_path: ~/.local/share/audiomancer/audiomancer.db
  embeddings_path: ~/.local/share/audiomancer/embeddings
  models_path: ~/.local/share/audiomancer/models
```

### Example Project Config

`.audiomancer.yaml` (auto-generated by `audiomancer init`):
```yaml
# Project-specific settings
library:
  project_root: ~/Development/my-music  # This project's root
  source_dir: ~/path/to/samples         # Override global sample source

# Project can override any global setting
analysis:
  max_file_size_mb: 20  # Different limit for this project
```

### Config Auto-Detection

When running `audiomancer serve` or using MCP tools, the server automatically:
1. Searches upward from current directory for `.audiomancer.yaml`
2. If found, uses that project as the context
3. Merges project config with global config and builtin defaults
4. All file paths in tools are relative to detected project root

This means Claude Code can automatically detect which project you're working in when you start the MCP server.

### Project Structure

```
{project_root}/
├── .audiomancer.yaml   # Project-specific config
├── .mcp.json          # MCP server detection
├── samples/           # Local cache (copied from source)
├── library/           # Active samples (symlinks to samples/)
├── session.tidal      # TidalCycles session
├── start_superdirt.scd # SuperDirt startup
└── CLAUDE.md          # Claude Code project instructions
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

### Similarity Search with FAISS

```python
from audiomancer.analyzers.embeddings import SimilarityIndex, extract_audio_embedding
import librosa

# Build an index from multiple samples
index = SimilarityIndex(dimension=128)

embeddings = []
for sample_path in sample_paths:
    audio, sr = librosa.load(sample_path, sr=None)
    emb = extract_audio_embedding(audio, sr)
    embeddings.append(emb)

index.add(embeddings)
print(f"Indexed {index.ntotal} samples")

# Search for similar samples
query_audio, sr = librosa.load("query.wav", sr=None)
query_emb = extract_audio_embedding(query_audio, sr)

similarities, indices = index.search(query_emb, k=5)
for sim, idx in zip(similarities, indices):
    print(f"Sample {idx}: similarity {sim:.3f}")

# Save/load index for persistence
index.save("samples.index")
loaded_index = SimilarityIndex.load("samples.index")
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

## Development

### Setup

After cloning the repo:

```bash
pip install -e ".[dev]"
pre-commit install
```

Run hooks manually: `pre-commit run --all-files`

## License

MIT
