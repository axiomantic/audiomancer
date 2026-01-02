# Setup

## Creating a New Project

```bash
# Create a new TidalCycles project with interactive setup
audiomancer init

# Or specify a directory
audiomancer init --path ~/my-music-project
```

The `init` command will:

1. Prompt for project name (defaults to directory name)
2. Prompt for sample source directory (any local directory, network mount, Dropbox, etc.)
3. Create project structure with samples/ and library/ directories
4. Generate project-specific .audiomancer.yaml config file
5. Create TidalCycles session files (session.tidal, start_superdirt.scd)
6. Add Claude Code integration files (.mcp.json, CLAUDE.md)
7. Initialize git repository with .gitignore

## Claude Code Setup

```bash
# Use the full path to the venv's audiomancer binary
claude mcp add audiomancer --scope user -- /path/to/audiomancer/.venv/bin/audiomancer serve

# Example with actual path:
# claude mcp add audiomancer --scope user -- ~/Development/audiomancer/.venv/bin/audiomancer serve
```

## Claude Desktop Setup

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

## Project Structure

After running `audiomancer init`, you'll have:

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

## Next Steps

- [Quick Start Guide](quickstart.md) - Learn common workflows
- [Configuration](../configuration/system.md) - Configure audiomancer
- [MCP Tools](../guide/mcp-tools.md) - Available tools
