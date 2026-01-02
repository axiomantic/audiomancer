# Audiomancer MCP Server

Model Context Protocol (MCP) server for audio sample search, analysis, and synth metadata.

## Overview

The Audiomancer MCP server provides LLM-friendly tools for:

- **Sample Search**: Semantic search across audio samples with filters
- **Similarity Search**: Find samples similar to a given sample using embeddings
- **Audio Analysis**: Analyze new audio files and extract features
- **Synth Management**: Browse and query SuperCollider SynthDefs
- **Library Statistics**: Get insights into your audio library

## Setup

### 1. Install Dependencies

```bash
pip install audiomancer
```

### 2. Initialize Configuration

```bash
audiomancer init
```

This creates:
- `~/.config/audiomancer/config.yaml` - Configuration file
- `~/.local/share/audiomancer/` - Data directory for database and embeddings

### 3. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### 4. Start the Server

The server starts automatically when Claude Desktop launches. You can also test it manually:

```bash
audiomancer serve
```

## Available Tools

### search_samples

Search audio samples by text query and filters.

**Parameters:**
- `query` (string, optional): Text search query (searches file paths and instrument types)
- `instrument_type` (string, optional): Filter by instrument (e.g., "kick", "snare", "bass")
- `bpm_min` (number, optional): Minimum BPM
- `bpm_max` (number, optional): Maximum BPM
- `key` (string, optional): Musical key (e.g., "C", "Am", "F#")
- `mood` (string, optional): Mood tag (e.g., "dark", "bright", "aggressive")
- `limit` (integer, default: 20): Maximum results

**Example:**
```json
{
  "query": "kick",
  "bpm_min": 120,
  "bpm_max": 130,
  "key": "C",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "smpl_abc123",
      "file_path": "/samples/kick_001.wav",
      "instrument_type": "kick",
      "bpm": 128.0,
      "key": "C",
      "duration_ms": 250.5,
      "sample_rate": 44100,
      "channels": 1
    }
  ],
  "count": 1,
  "query": {
    "text": "kick",
    "bpm_range": [120, 130],
    "key": "C"
  }
}
```

### find_similar

Find samples similar to a given sample using audio embeddings.

**Parameters:**
- `sample_id` (string, required): Sample ID to find similar samples for
- `limit` (integer, default: 10): Maximum results

**Example:**
```json
{
  "sample_id": "smpl_abc123",
  "limit": 5
}
```

**Response:**
```json
{
  "query_sample_id": "smpl_abc123",
  "similar_samples": [
    {
      "id": "smpl_def456",
      "file_path": "/samples/kick_002.wav",
      "instrument_type": "kick",
      "bpm": 128.0,
      "key": "C",
      "distance": 0.15
    }
  ],
  "count": 1
}
```

### describe_sample

Get complete metadata and analysis for a sample.

**Parameters:**
- `sample_id` (string, required): Sample ID

**Example:**
```json
{
  "sample_id": "smpl_abc123"
}
```

**Response:**
```json
{
  "id": "smpl_abc123",
  "file_path": "/samples/kick_001.wav",
  "file_hash": "abc123...",
  "duration_ms": 250.5,
  "sample_rate": 44100,
  "channels": 1,
  "bit_depth": 16,
  "spectral_centroid": 1000.0,
  "spectral_bandwidth": 500.0,
  "bpm": 128.0,
  "bpm_confidence": 0.95,
  "key": "C",
  "key_confidence": 0.85,
  "instrument_type": "kick",
  "instrument_confidence": 0.98,
  "mood": ["dark", "punchy"],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### analyze_file

Analyze a new audio file and add it to the database.

**Parameters:**
- `path` (string, required): Absolute path to audio file

**Example:**
```json
{
  "path": "/path/to/sample.wav"
}
```

**Response:**
```json
{
  "success": true,
  "sample_id": "smpl_new123",
  "file_path": "/path/to/sample.wav",
  "analysis": {
    "instrument_type": "kick",
    "bpm": 128.0,
    "key": "C",
    "duration_ms": 250.5
  }
}
```

### list_synths

List available SuperCollider SynthDefs.

**Parameters:**
- `category` (string, optional): Filter by category (e.g., "bass", "pad", "lead")
- `limit` (integer, default: 50): Maximum results

**Example:**
```json
{
  "category": "bass",
  "limit": 10
}
```

**Response:**
```json
{
  "synths": [
    {
      "id": "synth_tb303",
      "name": "tb303",
      "category": "bass",
      "num_controls": 8,
      "has_gate": true
    }
  ],
  "count": 1,
  "filter": {"category": "bass"}
}
```

### get_synth

Get full details for a SuperCollider SynthDef.

**Parameters:**
- `name` (string, required): SynthDef name

**Example:**
```json
{
  "name": "tb303"
}
```

**Response:**
```json
{
  "id": "synth_tb303",
  "name": "tb303",
  "file_path": "/synths/tb303.scd",
  "controls": [
    {"name": "freq", "default": 440.0},
    {"name": "resonance", "default": 0.7},
    {"name": "cutoff", "default": 1200.0}
  ],
  "characteristics": {
    "has_gate": true,
    "num_channels": 2
  },
  "categorization": {
    "category": "bass",
    "subcategory": "acid"
  },
  "source_code": "SynthDef(\\tb303, { ... })"
}
```

### get_stats

Get library statistics.

**Parameters:** None

**Response:**
```json
{
  "samples": {
    "total": 1234,
    "by_instrument": {
      "kick": 234,
      "snare": 189,
      "hat": 345,
      "bass": 156
    }
  },
  "synths": {
    "total": 45
  }
}
```

## Error Handling

All tools return structured error responses on failure:

```json
{
  "error": "SampleNotFoundError",
  "message": "Sample not found: smpl_missing123",
  "details": {
    "sample_id": "smpl_missing123",
    "reason": "No sample with this ID exists"
  }
}
```

Common error types:
- `AudiomancerError`: Base error (e.g., storage not initialized)
- `SampleNotFoundError`: Sample ID not found in database
- `AnalysisError`: Audio analysis failed
- `ConfigError`: Configuration issue
- `StorageError`: Database operation failed

## Usage Examples

### Example 1: Find Similar Kicks

```
User: Find me 5 kicks similar to smpl_kick001

Claude uses:
1. describe_sample(sample_id="smpl_kick001") - Get details
2. find_similar(sample_id="smpl_kick001", limit=5) - Find similar
```

### Example 2: Search for Dark Bass Samples

```
User: Show me dark bass samples around 140 BPM

Claude uses:
search_samples(
  instrument_type="bass",
  mood="dark",
  bpm_min=135,
  bpm_max=145,
  limit=20
)
```

### Example 3: Analyze New Sample

```
User: Analyze this new kick sample at /samples/new_kick.wav

Claude uses:
analyze_file(path="/samples/new_kick.wav")
```

### Example 4: Browse Synths

```
User: What bass synths do I have?

Claude uses:
list_synths(category="bass")
```

## Troubleshooting

### Server not responding

1. Check Claude Desktop logs: `~/Library/Logs/Claude/mcp.log`
2. Verify configuration: `audiomancer doctor`
3. Test manually: `audiomancer serve`

### No samples found

1. Index your samples: `audiomancer scan /path/to/samples`
2. Check database: `ls ~/.local/share/audiomancer/`
3. Verify paths in config: `~/.config/audiomancer/config.yaml`

### Analysis errors

1. Ensure dependencies installed: `audiomancer doctor`
2. Check file format (WAV, FLAC supported)
3. Verify file permissions

## Development

### Running Tests

```bash
pytest tests/integration/test_mcp_server.py -v
```

### Adding New Tools

1. Add tool definition to `list_tools()` in `server.py`
2. Implement handler function
3. Add to `call_tool()` dispatcher
4. Write integration tests

## Performance

- Initial startup: ~2-5 seconds (loads models)
- Search queries: ~10-50ms
- Similarity search: ~50-200ms
- File analysis: ~2-10 seconds (depending on file length)

## Limitations

- Maximum file size: 50MB (configurable)
- Supported formats: WAV, FLAC, OGG, MP3
- Embedding dimension: 128 (fixed)
- Maximum results per query: 1000

## See Also

- [Configuration Guide](config.md)
- [Audio Analysis](analysis.md)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
