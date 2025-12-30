# audiomancer - AI Assistant Guide

This document helps you (the AI) understand what audiomancer does and how to use it effectively.

## What is audiomancer?

An MCP server that gives you deep integration with music production workflows. You can:

1. **Manage sample libraries** - Browse, enable, disable packs from Google Drive
2. **Generate patterns** - Create TidalCycles code using real sample IDs
3. **Search samples** - Find by description, features, or audio similarity
4. **Analyze audio** - Extract BPM, key, spectral features, embeddings

## Quick Start: What Can You Do?

### Sample Library Management

```
User: "What sample packs do I have?"
You: [call list_packs] → Shows all packs with status (remote/cached/enabled)

User: "Enable the 808 Drum Kit"
You: [call enable_pack "808 Drum Kit"] → Copies files, creates symlinks

User: "What kicks do I have?"
You: [call list_enabled_samples] → Filter by category "bd"

User: "Disable all the packs I'm not using"
You: [call disable_pack for each] → Removes symlinks, keeps cache
```

### Pattern Generation

```
User: "Generate a techno drum pattern"
You: [call generate_pattern with style="techno"]
     The pattern uses real sample IDs from the enabled library!
     Result: d1 $ sound "808dk_bd 808dk_bd ~ 808dk_sn"

User: "Make it more sparse"
You: Modify the pattern directly in your response
```

### Sample Discovery

```
User: "Find samples similar to 808dk_bd"
You: [call find_similar "808dk_bd"] → Returns similar samples by audio embedding

User: "Search for dark ambient pads"
You: [call search_samples query="dark ambient pad"] → Text + semantic search
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server (server.py)                        │
│                      15 tools for AI access                      │
├─────────────────────────────────────────────────────────────────┤
│  Library Management           │  Analysis & Storage              │
│  ├── list_packs               │  ├── search_samples              │
│  ├── search_packs             │  ├── find_similar                │
│  ├── get_pack_status          │  ├── describe_sample             │
│  ├── enable_pack              │  ├── analyze_file                │
│  ├── disable_pack             │  └── get_stats                   │
│  ├── purge_pack               │                                  │
│  └── list_enabled_samples     │  Generation                      │
│                               │  ├── generate_pattern            │
│                               │  ├── list_synths                 │
│                               │  └── get_synth                   │
├─────────────────────────────────────────────────────────────────┤
│  library/                     │  analyzers/                      │
│  ├── manager.py (LibraryMgr)  │  ├── basic.py (metadata)         │
│  ├── scanner.py (categories)  │  ├── spectral.py (Essentia)      │
│  ├── schema.py (TypedDicts)   │  ├── rhythm.py (BPM)             │
│  └── interfaces.py            │  ├── embeddings.py (128-dim)     │
│                               │  └── synthdef.py (SC parser)     │
├─────────────────────────────────────────────────────────────────┤
│  generators/                  │  storage/                        │
│  ├── patterns.py (drums/mel)  │  ├── db.py (SQLite)              │
│  ├── synths.py (evolution)    │  ├── vectors.py (LanceDB)        │
│  └── lineage.py (tracking)    │  └── unified.py (atomic ops)     │
├─────────────────────────────────────────────────────────────────┤
│  CLI: cli.py (Typer)  │  Config: config.py (Pydantic)           │
└─────────────────────────────────────────────────────────────────┘
```

## MCP Tools Reference

### Library Management Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `list_packs` | none | List of PackInfo with name, file_count, size_mb, status |
| `search_packs` | `pattern: str` | Filtered list of PackInfo |
| `get_pack_status` | `pack_name: str` | PackStatus with detailed info |
| `enable_pack` | `pack_name: str` | EnableResult with sample_ids, copy_stats |
| `disable_pack` | `pack_name: str` | Number of symlinks removed |
| `purge_pack` | `pack_name: str` | Boolean success |
| `list_enabled_samples` | none | List of SampleInfo with id, category, pack_name |

### Analysis Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `search_samples` | `query, instrument_type, bpm_min, bpm_max, key, limit` | List of samples |
| `find_similar` | `sample_id, limit` | List of (sample, distance) |
| `describe_sample` | `sample_id` | Full sample metadata |
| `analyze_file` | `path` | Analysis results (BPM, key, features) |
| `get_stats` | none | Library statistics |

### Generation Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `generate_pattern` | `type, style, bpm, bars, key` | Pattern with tidal_code, midi_data |
| `list_synths` | `category` | List of SynthDef names |
| `get_synth` | `name` | SynthDef details (controls, UGens) |

## Sample Categories

When samples are enabled, they're auto-categorized by filename patterns:

| Category | Matches | Type |
|----------|---------|------|
| `bd` | kick, bassdrum, bd | drum |
| `sn` | snare, sd | drum |
| `hh` | hihat, hh, hat | drum |
| `oh` | open hat, oh | drum |
| `cp` | clap, handclap, cp | drum |
| `tom` | tom, floor tom | drum |
| `crash`, `ride`, `cym` | crash, ride, cymbal | drum |
| `perc` | perc, shaker, conga, bongo, tamb | perc |
| `bass`, `sub` | bass, sub, subbass | bass |
| `synth`, `lead`, `pad`, `arp` | synth, lead, pad, arp | melodic |
| `fx`, `impact`, `riser` | fx, impact, riser, downlifter | fx |
| `vox` | vocal, vox, voice | vocal |
| `dloop`, `tloop`, `ploop`, `loop` | drum loop, top loop, perc loop, loop | loop |

**Important**: Category patterns use word boundaries (`\b`), so `kick_01.wav` won't match (underscore is a word character). Use spaces or hyphens: `kick 01.wav` or `kick-01.wav`.

## Sample ID Format

Sample IDs are generated as: `{pack_abbr}[_lp]_{category}[_{bpm}]`

Examples:
- `808dk_bd` - 808 Drum Kit kicks
- `vihodr_sn` - Vinyl House Drums snares
- `techse_lp_hh_125` - Tech House loop, hi-hats, 125 BPM

## Pattern Generation with Library Samples

When you call `generate_pattern`, it can use the SampleLookup interface to query real sample IDs:

```python
# Without library (defaults)
drums = generate_drums(style="techno", bpm=130)
# Result: d1 $ sound "bd bd ~ bd"

# With library (real samples)
drums = generate_drums(style="techno", bpm=130, sample_lookup=library_manager)
# Result: d1 $ sound "808dk_bd 808dk_bd ~ 808dk_bd"
```

The MCP server automatically passes the library manager when available.

## Pack Status States

| Status | Meaning |
|--------|---------|
| `remote` | On Google Drive, not cached locally |
| `cached` | Copied to samples/, but symlinks removed |
| `enabled` | Active in library/, SuperDirt can load it |

## Error Handling

All errors inherit from `AudiomancerError` with a `details` dict:

```python
from audiomancer.errors import (
    AudiomancerError,       # Base
    LibraryError,           # Library operations
    PackNotFoundError,      # Pack doesn't exist
    SourceNotAvailableError,# Can't access source (Google Drive)
    SampleNotFoundError,    # Sample ID not found
    AnalysisError,          # Analysis failed
    GenerationError,        # Pattern generation failed
)
```

When errors occur, check `error.details` for actionable information.

## Key Principles

1. **Fail-fast**: No graceful degradation. Errors include actionable fixes.
2. **Type safety**: All code uses type hints and Protocol classes.
3. **Atomic operations**: Storage operations are all-or-nothing.
4. **128-dim embeddings**: All audio embeddings are exactly 128 dimensions, L2-normalized.

## Common Tasks

### Enabling a pack and generating a pattern

```
1. list_packs → See what's available
2. enable_pack "Pack Name" → Copy and symlink
3. list_enabled_samples → Verify samples are available
4. generate_pattern style="techno" → Uses real sample IDs
5. Tell user to restart SuperDirt if they haven't
```

### Finding similar samples

```
1. describe_sample "sample_id" → Get metadata
2. find_similar "sample_id" limit=10 → Get similar by embedding
3. Present results with distances and descriptions
```

### Searching by criteria

```
1. search_samples query="dark kick" instrument_type="kick" bpm_min=120 bpm_max=140
2. Filter/sort results as needed
3. Present with relevant metadata
```

## File Paths

The library uses a project-based structure:

```
{project_root}/
├── samples/           # Local cache (copied from Google Drive)
├── library/           # Active samples (symlinks to samples/)
├── session.tidal      # TidalCycles session
└── start_superdirt.scd
```

Source is typically Google Drive:
```
~/Library/CloudStorage/GoogleDrive-{email}/My Drive/.../Samples/
```

## Testing

```bash
pytest tests/unit/library/    # Library module (62 tests)
pytest tests/unit/            # All unit tests
pytest                        # Full suite (597 tests)
```

## Dependencies

- `essentia.standard` - Audio feature extraction
- `librosa` - Audio loading
- `lancedb` - Vector similarity search
- `sqlalchemy` - SQL ORM
- `mido` - MIDI handling
- `mcp` - Model Context Protocol SDK
- `typer` + `rich` - CLI
