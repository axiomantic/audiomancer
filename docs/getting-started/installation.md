# Installation

## Prerequisites

Before installing audiomancer, you need a working TidalCycles setup:

- **TidalCycles**: Live coding language and runtime
  - Installation guide: [https://tidalcycles.org/docs/getting-started/installation/](https://tidalcycles.org/docs/getting-started/installation/)
- **SuperCollider**: Audio synthesis platform (required for TidalCycles)
  - Download: [https://supercollider.github.io/downloads](https://supercollider.github.io/downloads)
- **VS Code TidalCycles Extension**: Editor integration
  - Extension: [https://marketplace.visualstudio.com/items?itemName=tidalcycles.vscode-tidalcycles](https://marketplace.visualstudio.com/items?itemName=tidalcycles.vscode-tidalcycles)
- **ghcup**: Haskell toolchain manager (for TidalCycles)
  - Installation: [https://www.haskell.org/ghcup/](https://www.haskell.org/ghcup/)

Run `audiomancer doctor` after installation to verify all prerequisites are installed.

## Installing Audiomancer

### From Source

```bash
# Clone and install
git clone https://github.com/axiomantic/audiomancer
cd audiomancer
pip install -e ".[dev]"

# Check dependencies (including TidalCycles setup)
audiomancer doctor
```

### Requirements

- Python 3.10+
- SuperCollider (for SynthDef parsing)

## Verifying Installation

Run the doctor command to check all dependencies:

```bash
audiomancer doctor
```

This will verify:

- Python version
- TidalCycles installation
- SuperCollider installation
- Required Python packages
- Audio analysis libraries (librosa, essentia)

## Next Steps

After installation:

1. [Create a new project](setup.md)
2. [Configure MCP servers](setup.md#claude-code-setup)
3. [Start using audiomancer](quickstart.md)
