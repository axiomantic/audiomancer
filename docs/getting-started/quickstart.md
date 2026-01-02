# Quick Start

## Common Tasks

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

## Sample Categories

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

## Next Steps

- [Workflows](../guide/workflows.md) - Detailed workflow examples
- [MCP Tools](../guide/mcp-tools.md) - Complete tool reference
- [Configuration](../configuration/system.md) - Advanced configuration
