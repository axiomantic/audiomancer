# MCP Tools

## Library Management (7 tools)

| Tool                   | Description                            |
| ---------------------- | -------------------------------------- |
| `list_packs`           | List all packs from source with status |
| `search_packs`         | Search packs by name pattern           |
| `get_pack_status`      | Get detailed pack info                 |
| `enable_pack`          | Enable pack (copy + symlink)           |
| `disable_pack`         | Disable pack (remove symlinks)         |
| `purge_pack`           | Remove from cache entirely             |
| `list_enabled_samples` | List enabled sample IDs                |

## Analysis & Search (4 tools)

| Tool              | Description                          |
| ----------------- | ------------------------------------ |
| `search_samples`  | Search by text, instrument, BPM, key |
| `find_similar`    | Find samples similar to given sample |
| `describe_sample` | Get full metadata for a sample       |
| `analyze_file`    | Analyze new audio file               |

## Generation & Synths (3 tools)

| Tool               | Description                       |
| ------------------ | --------------------------------- |
| `generate_pattern` | Generate drum/melody/bass pattern |
| `list_synths`      | List available SynthDefs          |
| `get_synth`        | Get SynthDef details              |

## Stats (1 tool)

| Tool        | Description        |
| ----------- | ------------------ |
| `get_stats` | Library statistics |

## Next Steps

- [Workflows](workflows.md) - Example workflows
- [CLI Commands](cli.md) - Command-line usage
- [API Reference](../api/index.md) - Python API
