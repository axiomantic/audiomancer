# Audio Analyzers Quick Start

## Installation

```bash
pip install librosa essentia-tensorflow soundfile numpy
```

## Basic Usage

```python
from pathlib import Path
from audiomancer.analyzers import get_basic_metadata, extract_spectral_features
import librosa

# 1. Extract basic metadata
path = Path("kick.wav")
metadata = get_basic_metadata(path)

# Returns:
# {
#     'duration_ms': 250.0,
#     'sample_rate': 44100,
#     'channels': 1,
#     'bit_depth': 16,
#     'file_size_bytes': 44100,
#     'file_hash': 'abc123...'
# }

# 2. Extract spectral features
y, sr = librosa.load(str(path), sr=None)
features = extract_spectral_features(y, sr)

# Returns:
# {
#     'spectral_centroid': 1523.5,    # Brightness (Hz)
#     'spectral_bandwidth': 850.2,    # Frequency spread
#     'spectral_rolloff': 3200.0,     # High-freq cutoff (Hz)
#     'zero_crossing_rate': 0.15,     # Noisiness (0-1)
#     'rms_energy': 0.45,             # Energy (0-1)
#     'dynamic_range': 18.2           # Peak-to-RMS (dB)
# }
```

## Run Tests

```bash
# Test basic analyzer
pytest tests/unit/test_basic_analyzer.py -v

# Test spectral analyzer
pytest tests/unit/test_spectral_analyzer.py -v

# Test golden files
pytest tests/unit/test_golden_analysis.py -v

# Run all analyzer tests
pytest tests/unit/test_*_analyzer.py tests/unit/test_golden_analysis.py -v
```

## File Locations

- **Implementation**: `src/audiomancer/analyzers/basic.py`, `spectral.py`
- **Tests**: `tests/unit/test_basic_analyzer.py`, `test_spectral_analyzer.py`
- **Golden**: `tests/golden/kick_analysis.json`
- **Docs**: `src/audiomancer/analyzers/README.md`

## Key Features

✅ Comprehensive error handling
✅ Type-safe (TypedDict returns)
✅ NaN/inf validation
✅ 55+ unit tests
✅ Golden file regression tests
✅ Full documentation
