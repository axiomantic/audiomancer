# Audio Analyzers

This module provides audio analysis capabilities for extracting metadata and features from audio files.

## Modules

### `basic.py` - Basic Metadata Extraction

Extracts fundamental audio file properties:

```python
from audiomancer.analyzers import get_basic_metadata
from pathlib import Path

metadata = get_basic_metadata(Path("kick.wav"))

# Returns BasicMetadata TypedDict:
# {
#     'duration_ms': 250.5,        # Duration in milliseconds
#     'sample_rate': 44100,         # Sample rate in Hz
#     'channels': 1,                # Number of channels
#     'bit_depth': 16,              # Bit depth (assumed 16 for librosa)
#     'file_size_bytes': 44100,     # File size on disk
#     'file_hash': 'abc123...'      # SHA256 hex digest
# }
```

**Features:**
- Native sample rate preservation (no resampling)
- Automatic mono/stereo detection
- SHA256 hash for deduplication
- Comprehensive error handling

**Supported Formats:**
All formats supported by librosa (WAV, FLAC, MP3, OGG, etc.)

### `spectral.py` - Spectral Feature Extraction

Extracts frequency-domain features using Essentia:

```python
from audiomancer.analyzers import extract_spectral_features
import librosa

# Load audio
y, sr = librosa.load("kick.wav", sr=None)

# Extract features
features = extract_spectral_features(y, sr)

# Returns SpectralFeatures TypedDict:
# {
#     'spectral_centroid': 1523.5,    # Brightness (Hz)
#     'spectral_bandwidth': 850.2,    # Frequency spread (Hz)
#     'spectral_rolloff': 3200.0,     # High-freq cutoff (Hz)
#     'zero_crossing_rate': 0.15,     # Noisiness (0-1)
#     'rms_energy': 0.45,             # Energy level (0-1)
#     'dynamic_range': 18.2           # Peak-to-RMS (dB)
# }
```

**Features:**
- Frame-based analysis (2048 samples, 512 hop)
- Hann windowing for spectral smoothing
- Mean values aggregated across frames
- NaN/inf validation

**Algorithms Used:**
- **Centroid**: Spectral center of mass (brightness indicator)
- **Bandwidth**: 2nd central moment (frequency spread)
- **Rolloff**: 85% energy cutoff point
- **ZCR**: Zero crossing rate (percussiveness/noisiness)
- **RMS**: Root-mean-square energy
- **Dynamic Range**: Peak-to-average ratio in dB

## Error Handling

Both analyzers use the audiomancer error hierarchy:

```python
from audiomancer.errors import UnsupportedFormatError, AnalysisFailedError

try:
    metadata = get_basic_metadata(path)
except UnsupportedFormatError as e:
    # File format not supported or file doesn't exist
    print(f"Cannot load: {e.details['path']}")
except AnalysisFailedError as e:
    # Analysis failed (empty audio, corrupted, etc.)
    print(f"Analysis failed: {e.details['reason']}")
```

## Usage Examples

### Complete Sample Analysis

```python
from pathlib import Path
from audiomancer.analyzers import get_basic_metadata, extract_spectral_features
import librosa

def analyze_sample(sample_path: Path) -> dict:
    """Complete analysis of an audio sample."""
    # Extract basic metadata
    metadata = get_basic_metadata(sample_path)

    # Load audio for spectral analysis
    y, sr = librosa.load(str(sample_path), sr=None)

    # Extract spectral features
    spectral = extract_spectral_features(y, sr)

    # Combine results
    return {
        'basic': dict(metadata),
        'spectral': dict(spectral)
    }

# Usage
analysis = analyze_sample(Path("samples/kick_808.wav"))
print(f"Duration: {analysis['basic']['duration_ms']}ms")
print(f"Brightness: {analysis['spectral']['spectral_centroid']}Hz")
```

### Batch Processing

```python
from pathlib import Path
from audiomancer.analyzers import get_basic_metadata

def analyze_directory(directory: Path):
    """Analyze all WAV files in a directory."""
    results = {}

    for wav_file in directory.glob("**/*.wav"):
        try:
            metadata = get_basic_metadata(wav_file)
            results[wav_file.name] = metadata
        except Exception as e:
            print(f"Failed to analyze {wav_file}: {e}")

    return results

# Usage
all_samples = analyze_directory(Path("sample_library/"))
```

### Feature-Based Classification

```python
from audiomancer.analyzers import extract_spectral_features
import librosa

def classify_sample(audio_path):
    """Classify sample based on spectral features."""
    y, sr = librosa.load(str(audio_path), sr=None)
    features = extract_spectral_features(y, sr)

    # Simple heuristic classification
    if features['spectral_centroid'] < 500:
        category = 'bass'
    elif features['zero_crossing_rate'] > 0.3:
        category = 'noise/hihat'
    elif features['spectral_centroid'] > 2000:
        category = 'bright/lead'
    else:
        category = 'mid-range'

    return category

# Usage
category = classify_sample("samples/mystery_sound.wav")
print(f"Classified as: {category}")
```

## Performance Considerations

### Basic Metadata
- **Speed**: Very fast (~1-2ms for typical samples)
- **Memory**: Loads full audio into memory
- **I/O**: Reads file twice (once for audio, once for hash)

### Spectral Features
- **Speed**: ~10-50ms for 1-second audio
- **Memory**: Minimal (frame-based processing)
- **CPU**: Compute-intensive (FFT operations)

### Optimization Tips

```python
# For large batches, reuse librosa load
y, sr = librosa.load(path, sr=None)

# Can extract multiple features from same audio
spectral = extract_spectral_features(y, sr)
# Add other analyses here...

# Avoid reloading the same file multiple times
```

## Testing

See `tests/unit/test_basic_analyzer.py` and `tests/unit/test_spectral_analyzer.py` for comprehensive test coverage.

Golden file regression tests in `tests/unit/test_golden_analysis.py` ensure consistent results.

## Requirements

- **librosa**: Audio loading and preprocessing
- **essentia**: Spectral feature extraction
- **numpy**: Numerical operations
- **soundfile**: WAV file I/O (via librosa)

## See Also

- `interfaces.py`: Protocol definitions for SynthDef parsing
- `../errors.py`: Error class hierarchy
- `../../storage/`: Database storage for analysis results
