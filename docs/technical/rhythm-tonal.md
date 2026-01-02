# Rhythm and Tonal Analysis Implementation

## Overview

This document describes the rhythm and tonal analysis features implemented for audiomancer using Essentia.

## Components

### 1. Rhythm Analysis (`src/audiomancer/analyzers/rhythm.py`)

Extracts tempo, beat positions, and loop detection using Essentia's RhythmExtractor2013.

**Features Extracted:**
- `bpm`: float or None (beats per minute, None for non-rhythmic content)
- `bpm_confidence`: float (0-1, confidence in BPM detection)
- `beat_positions`: list[float] (beat times in seconds)
- `is_loop`: bool (True if audio appears to be a rhythmic loop)

**Key Algorithms:**
- `RhythmExtractor2013(method="multifeature")` - BPM detection with confidence

**Loop Detection Logic:**
- Duration matches bar boundaries (within 10% tolerance)
- Duration is less than 30 seconds (typical loop length)
- At least 1 bar of audio
- Assumes 4/4 time signature

**Error Handling:**
- Returns None for BPM on silence, NaN, or non-rhythmic content
- Returns empty beat_positions list for silence
- Raises AnalysisFailedError for invalid input (empty audio)

### 2. Tonal Analysis (`src/audiomancer/analyzers/tonal.py`)

Extracts key, tuning, and pitch salience using Essentia's KeyExtractor and spectral analysis.

**Features Extracted:**
- `key`: str or None (e.g., "C", "Dm", "F#m", None for percussion/noise)
- `key_confidence`: float (0-1, confidence in key detection)
- `tuning_frequency`: float (Hz, reference tuning, typically ~440)
- `pitch_salience`: float (0-1, how tonal vs percussive)

**Key Algorithms:**
- `KeyExtractor()` - Key and scale detection
- `TuningFrequency()` - Reference tuning detection (requires spectral peaks)
- `PitchSalience()` - Tonal vs percussive distinction
- `SpectralPeaks()` - Extract frequency peaks for tuning analysis

**Key Formatting:**
- Major keys: "C", "D", "F#", etc.
- Minor keys: "Am", "Dm", "F#m", etc.
- Returns None if confidence < 0.2

**Pitch Salience:**
- Higher values (>0.5) indicate tonal/melodic content
- Lower values (<0.5) indicate percussive/noisy content
- Computed as mean across all audio frames

**Error Handling:**
- Returns None for key on silence, NaN, or non-tonal content
- Defaults tuning_frequency to 440 Hz if detection fails
- Returns 0.0 for pitch_salience on silence
- Raises AnalysisFailedError for invalid input (empty audio)

## Usage Examples

```python
from audiomancer.analyzers import extract_rhythm_features, extract_tonal_features
import librosa

# Load audio
y, sr = librosa.load("sample.wav", sr=None)

# Extract rhythm features
rhythm = extract_rhythm_features(y, sr)
print(f"BPM: {rhythm['bpm']}")
print(f"Is loop: {rhythm['is_loop']}")
print(f"Beat positions: {rhythm['beat_positions'][:5]}...")

# Extract tonal features
tonal = extract_tonal_features(y, sr)
print(f"Key: {tonal['key']}")
print(f"Tuning: {tonal['tuning_frequency']} Hz")
print(f"Pitch salience: {tonal['pitch_salience']}")
```

## Test Coverage

### Unit Tests (25 tests)

**Rhythm Analyzer Tests:**
- Silence handling (returns None for BPM)
- Sine wave (non-rhythmic, returns None)
- Impulse (low confidence)
- 4/4 loop detection
- Feature shape validation
- Stereo to mono conversion
- Empty audio error handling
- NaN audio handling
- Long audio (>30s) not marked as loop
- Beat positions are sorted
- No NaN/inf in output

**Tonal Analyzer Tests:**
- Silence handling (returns None for key)
- Sine wave (measurable pitch salience)
- Impulse (low pitch salience)
- Feature shape validation
- Major key format (e.g., "C")
- Minor key format (e.g., "Am")
- Stereo to mono conversion
- Empty audio error handling
- NaN audio handling
- Tuning frequency defaults
- Pitch salience range validation
- No NaN/inf in output
- Percussion handling
- Tonal vs percussive distinction

### Integration Tests (5 tests)

- Complete analysis on silence
- Complete analysis on tonal content (C major arpeggio)
- Complete analysis on rhythmic percussion
- Output consistency across different audio types
- Combined features for sample classification

## Dependencies

- `essentia-tensorflow>=2.1b6.dev1110,<3` - Audio analysis algorithms
- `numpy>=1.24.0,<2` - Array operations
- `librosa>=0.10.0,<0.11` - Audio loading (optional, for examples)

## Design Decisions

### Why None instead of 0 for BPM?

Using None makes it clear that BPM could not be determined, rather than implying a BPM of 0. This is important for:
- Distinguishing non-rhythmic content from silence
- Avoiding division by zero in downstream calculations
- Making API contracts clearer (Optional[float] vs float)

### Why threshold key confidence at 0.2?

Key detection on noise/percussion can produce spurious results with low confidence. Only reporting keys with confidence > 0.2 reduces false positives while allowing detection on real tonal content.

### Why default tuning to 440 Hz?

When tuning detection fails (e.g., on pure noise), defaulting to 440 Hz provides a sensible reference value that won't break downstream calculations. This is the standard concert pitch.

### Why frame-based pitch salience?

Computing pitch salience across multiple frames and averaging provides a more robust measure of overall tonality than analyzing the entire signal at once. This handles:
- Varying tonal content over time
- Mixed percussive and tonal elements
- Transients and noise

## Validation

All values returned by the analyzers are validated to ensure:
- No NaN or inf values
- Confidence values in [0, 1] range
- Tuning frequency in reasonable range (400-480 Hz)
- BPM is positive when detected
- Beat positions are sorted in ascending order

## Future Improvements

Potential enhancements for future versions:

1. **Multi-tempo detection**: Handle tempo changes within a single file
2. **Time signature detection**: Beyond assumed 4/4
3. **Downbeat detection**: Identify measure boundaries
4. **Harmonic analysis**: Chord progressions, harmonic rhythm
5. **Melodic analysis**: Contour, intervals, motifs
6. **Rhythmic pattern extraction**: Quantized groove templates
7. **Genre classification**: Using rhythm and tonal features
8. **Tempo stability**: Measure tempo variance over time

## References

- Essentia Documentation: [https://essentia.upf.edu/documentation/](https://essentia.upf.edu/documentation/)
- RhythmExtractor2013 Algorithm: [https://essentia.upf.edu/reference/std_RhythmExtractor2013.html](https://essentia.upf.edu/reference/std_RhythmExtractor2013.html)
- KeyExtractor Algorithm: [https://essentia.upf.edu/reference/std_KeyExtractor.html](https://essentia.upf.edu/reference/std_KeyExtractor.html)
- PitchSalience Algorithm: [https://essentia.upf.edu/reference/std_PitchSalience.html](https://essentia.upf.edu/reference/std_PitchSalience.html)
