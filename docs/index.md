# Audiomancer Documentation

**MCP server for AI-assisted music production.** Manages sample libraries, analyzes audio, generates patterns, and integrates with TidalCycles live coding.

## What is Audiomancer?

Audiomancer gives AI assistants deep integration with music production workflows. Instead of just chatting about music, the AI can:

- **Browse and enable sample packs** from your sample library without you leaving the conversation
- **Generate TidalCycles patterns** using your actual sample library (not generic "bd" and "sn")
- **Find similar samples** using audio embeddings and semantic search
- **Analyze audio files** for BPM, key, spectral features, and more

It's designed for TidalCycles live coding but the analysis and search features work for any DAW workflow.

## Architecture

![Audiomancer Architecture](assets/architecture-light.svg#only-light)
![Audiomancer Architecture](assets/architecture-dark.svg#only-dark)

**Quick overview:**

- **Sample Library** (source directory) contains your sample packs
- **Library Manager** copies files to local cache and creates symlinks for SuperDirt
- **Audio Analyzers** extract features and generate ML embeddings
- **Storage** persists metadata (SQLite) and vectors (LanceDB)
- **Pattern Generators** query samples and create TidalCycles code
- **MCP Server** exposes 15 tools to AI clients

See [Technical Architecture](technical/architecture.md) for detailed documentation.

## Quick Links

- [Installation](getting-started/installation.md) - Install audiomancer and prerequisites
- [Setup](getting-started/setup.md) - Create a new project
- [Quick Start](getting-started/quickstart.md) - Common tasks and workflows
- [MCP Tools](guide/mcp-tools.md) - Available MCP tools
- [Configuration](configuration/system.md) - Configuration system
- [API Reference](api/index.md) - Python API documentation

## Project Links

- [GitHub Repository](https://github.com/axiomantic/audiomancer)
- [Issue Tracker](https://github.com/axiomantic/audiomancer/issues)
- [Releases](https://github.com/axiomantic/audiomancer/releases)
