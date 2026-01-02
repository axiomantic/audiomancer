# API Reference

Audiomancer provides a Python API for audio analysis, pattern generation, and sample library management.

## Module Overview

- [audiomancer.analyzers](analyzers.md) - Audio analysis (spectral, rhythm, embeddings)
- [audiomancer.converters](converters.md) - Format conversion (MIDI, SuperCollider, TidalCycles)
- [audiomancer.generators](generators.md) - Pattern generation (drums, melody, bass)
- [audiomancer.library](library.md) - Sample library management
- [audiomancer.storage](storage.md) - Database and vector storage
- [audiomancer.templates](templates.md) - Project templates

## Installation

```bash
pip install audiomancer
```

## Quick Example

```python
from audiomancer.analyzers import extract_spectral_features
from audiomancer.generators import generate_drums
import librosa

# Analyze audio
audio, sr = librosa.load("kick.wav")
features = extract_spectral_features(audio, sr)

# Generate pattern
drums = generate_drums(style="techno", bpm=130, bars=4)
print(drums.tidal_code)
```

## Documentation Conventions

- **Parameters:** Type-annotated function parameters
- **Returns:** Return value type and description
- **Raises:** Exceptions that may be raised
- **Examples:** Usage examples in docstrings

## Next Steps

Browse the module documentation:

- [Analyzers API](analyzers.md)
- [Generators API](generators.md)
- [Library API](library.md)
