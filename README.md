# audiomancer

MCP server for AI-assisted music production with TidalCycles. Manage sample libraries, analyze audio, generate patterns, and enable AI-driven live coding workflows.

## Features

- **AI-powered sample library management** - Browse and enable sample packs from Google Drive via conversation
- **Smart pattern generation** - Generate TidalCycles patterns using your actual enabled samples, not generic names
- **Semantic sample search** - Find similar samples using audio embeddings and ML-based similarity
- **Comprehensive audio analysis** - Extract BPM, key, spectral features, and tonal information from any audio file
- **SuperCollider integration** - Parse SynthDefs and generate patterns with custom synths
- **Project-aware configuration** - Auto-detect projects with hierarchical config inheritance

## Quick Start

```bash
# Clone and install
git clone https://github.com/axiomantic/audiomancer
cd audiomancer
pip install -e ".[dev]"

# Create a new TidalCycles project
audiomancer init

# Check dependencies
audiomancer doctor

# Start MCP server
audiomancer serve
```

## Documentation

Full documentation: [axiomantic.github.io/audiomancer](https://axiomantic.github.io/audiomancer/)

Includes:
- Installation guides
- Complete MCP tool reference
- TidalCycles integration workflows
- Python API documentation
- Configuration system details
- Development and testing guides

## License

MIT
