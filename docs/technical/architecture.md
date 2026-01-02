# Architecture Overview

This section contains detailed technical documentation about audiomancer's implementation.

## Module Organization

- [Analyzers Implementation](analyzers.md) - Audio analysis engine
- [Storage Implementation](storage.md) - Database and vector storage
- [Pattern Generation](pattern-generation.md) - Algorithmic pattern creation
- [MCP Server](mcp-server.md) - Model Context Protocol server
- [MIDI Converter](midi-converter.md) - MIDI/SuperCollider conversion
- [SynthDef Implementation](synthdef.md) - SuperCollider synthesis definitions
- [Synth Evolution](synth-evolution.md) - Generative synthesis
- [Rhythm and Tonal Analysis](rhythm-tonal.md) - Advanced audio analysis

## Project Structure

```
src/audiomancer/
├── analyzers/       # Audio analysis (Essentia, librosa)
├── converters/      # MIDI ↔ TidalCycles ↔ SuperCollider
├── generators/      # Pattern generation (algorithmic)
├── library/         # Sample pack management
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

## Component Overview

### Analyzers

The analyzers module provides comprehensive audio analysis:

- **Basic metadata**: Duration, sample rate, file hash
- **Spectral features**: Centroid, bandwidth, RMS energy
- **Rhythm features**: BPM detection, onset detection
- **Audio embeddings**: 128-dimensional vectors for similarity search

See [Analyzers Implementation](analyzers.md) for details.

### Library Management

The library module manages sample packs:

- **Scanner**: Auto-categorizes samples by filename
- **Manager**: Copies files, creates symlinks, tracks status
- **Pack management**: Enable, disable, purge operations

### Storage

The storage module provides persistence:

- **SQLite**: Sample metadata and configuration
- **LanceDB**: Vector embeddings for similarity search
- **Unified interface**: Single API for all storage operations

See [Storage Implementation](storage.md) for details.

### Generators

The generators module creates patterns:

- **Pattern generation**: Algorithmic drum, melody, bass patterns
- **Synth evolution**: Genetic algorithms for SynthDef generation
- **TidalCycles output**: Native Haskell pattern code

See [Pattern Generation](pattern-generation.md) for details.

### MCP Server

The MCP server exposes 15 tools to AI assistants:

- Library management (7 tools)
- Analysis & search (4 tools)
- Generation & synths (3 tools)
- Statistics (1 tool)

See [MCP Server](mcp-server.md) for details.

## Data Flow

```
Sample Pack (local source directory)
        |
        v
LibraryManager.enable_pack()
        |
        ├──> Copy files to samples/
        ├──> Create symlinks in library/
        └──> Analyze audio → SQLite + LanceDB
                |
                v
        Embeddings for similarity search
                |
                v
        PatternGenerator uses samples
                |
                v
        TidalCycles pattern code
```

## Next Steps

Browse the detailed technical documentation:

- [MCP Server Implementation](mcp-server.md)
- [Audio Analysis](analyzers.md)
- [Pattern Generation](pattern-generation.md)
- [Storage Architecture](storage.md)
