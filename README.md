# audiomancer

MCP server for music production metadata, analysis, and generation. Analyzes audio samples and SuperCollider SynthDefs, provides semantic search via embeddings, and generates/evolves patterns and synths.

## Features

- **Audio Analysis**: Extract spectral, rhythm, and tonal features using Essentia
- **ML Classification**: Instrument type, mood, and genre tagging
- **Semantic Search**: Find similar samples via 128-dim audio embeddings
- **SynthDef Parsing**: Parse SuperCollider SynthDefs, extract controls and UGens
- **Pattern Generation**: Generate drums, melodies, basslines using Euclidean rhythms
- **Synth Evolution**: Mutate and breed SynthDefs with lineage tracking
- **MIDI Conversion**: Bidirectional MIDI to TidalCycles and SuperCollider

## Installation

```bash
# Clone and install
git clone https://github.com/youruser/audiomancer
cd audiomancer
pip install -e ".[dev]"

# Initialize (creates config, downloads models)
audiomancer init

# Check dependencies
audiomancer doctor
```

### Requirements

- Python 3.10+
- SuperCollider (for SynthDef parsing)

## Quick Start

### CLI Commands

```bash
audiomancer init          # Initialize config and data directories
audiomancer doctor        # Check all dependencies
audiomancer scan ~/Samples # Scan sample folders
audiomancer search "dark kick"  # Search from CLI
audiomancer stats         # Library statistics
audiomancer serve         # Start MCP server
audiomancer benchmark     # Run performance benchmarks
```

### Python API

```python
from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.analyzers import (
    get_basic_metadata, extract_spectral_features,
    extract_rhythm_features, extract_audio_embedding
)
import librosa

# Load and analyze
audio, sr = librosa.load("kick.wav", sr=None)
basic = get_basic_metadata(Path("kick.wav"))
spectral = extract_spectral_features(audio, sr)
embedding = extract_audio_embedding(audio, sr)

# Store with embedding
storage = UnifiedSampleStorage("samples.db", "embeddings/")
sample_id = storage.add_sample_with_embedding(sample_metadata, embedding)

# Find similar
for sample, distance in storage.find_similar(sample_id, limit=10):
    print(f"{sample['file_path']}: {distance:.3f}")
```

### Pattern Generation

```python
from audiomancer.generators import generate_drums, mutate_pattern
from audiomancer.converters import midi_to_tidal, midi_to_supercollider

pattern = generate_drums(style="techno", bpm=130, bars=4)
tidal_code = midi_to_tidal(pattern.midi_data, bpm=130)
sc_code = midi_to_supercollider(pattern.midi_data, synth_name="bd")
mutant = mutate_pattern(pattern, amount=0.5)
```

## MCP Integration

Add to Claude Desktop config (`~/.config/claude/claude_desktop_config.json`):

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

### MCP Tools

| Tool | Description |
|------|-------------|
| `search_samples` | Search by text, instrument, BPM, key, mood |
| `find_similar` | Find samples similar to a given sample |
| `describe_sample` | Get full metadata for a sample |
| `analyze_file` | Analyze new audio file |
| `list_synths` | List available SynthDefs |
| `get_synth` | Get SynthDef details |
| `get_stats` | Library statistics |

## Configuration

Config file: `~/.config/audiomancer/config.yaml`

```yaml
sources:
  samples:
    - ~/Music/Samples
  synths:
    - ~/synths

analysis:
  sample_rate: 44100

models:
  embeddings: musicnn  # musicnn, vggish, openl3
```

## Project Structure

```
src/audiomancer/
├── analyzers/       # Audio analysis (Essentia)
├── converters/      # MIDI conversion
├── generators/      # Pattern/synth generation
├── storage/         # SQLite + LanceDB
├── server.py        # MCP server
├── cli.py           # Typer CLI
└── errors.py        # Error hierarchy
```

## Testing

```bash
pytest                    # All tests
pytest tests/unit/        # Fast unit tests
pytest --cov=audiomancer  # With coverage
python benchmarks/run_benchmarks.py  # Performance
```

## License

MIT
