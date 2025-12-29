# MIDI to SuperCollider Converter

Bidirectional conversion between MIDI files and SuperCollider pattern code.

## Features

- **MIDI → SuperCollider**: Convert MIDI files to Pbind, Routine, or Pdef patterns
- **SuperCollider → MIDI**: Parse SuperCollider code and generate MIDI files
- **Three output formats**:
  - `pbind`: Standard Pbind patterns (most common)
  - `routine`: Explicit timing with Routine
  - `pattern`: Pdef pattern definitions
- **Utilities**: MIDI note ↔ frequency conversion, time quantization

## Installation

```bash
pip install mido  # Required dependency
```

## Quick Start

```python
from audiomancer.converters import midi_to_supercollider, supercollider_to_midi

# Convert MIDI to SuperCollider
with open('pattern.mid', 'rb') as f:
    midi_bytes = f.read()

sc_code = midi_to_supercollider(
    midi_bytes,
    synth_name="tb303",
    output_format="pbind"
)
print(sc_code)

# Convert SuperCollider to MIDI
sc_pattern = '''Pbind(
    \\instrument, \\default,
    \\freq, Pseq([440, 880], 1),
    \\dur, Pseq([0.5, 0.5], 1)
).play;'''

midi_bytes = supercollider_to_midi(sc_pattern, bpm=120)
with open('output.mid', 'wb') as f:
    f.write(midi_bytes)
```

## API Reference

### `midi_to_supercollider(midi_data, synth_name="default", bpm=120.0, output_format="pbind")`

Convert MIDI bytes to SuperCollider code.

**Arguments:**
- `midi_data` (bytes): Raw MIDI file data
- `synth_name` (str): SuperCollider synth name (default: "default")
- `bpm` (float): Tempo for timing calculations (default: 120.0)
- `output_format` (str): "pbind", "routine", or "pattern" (default: "pbind")

**Returns:** SuperCollider code as string

**Example:**
```python
sc_code = midi_to_supercollider(midi_bytes, synth_name="tb303")
```

### `supercollider_to_midi(sc_code, bpm=120.0)`

Convert SuperCollider Pbind code to MIDI.

**Arguments:**
- `sc_code` (str): SuperCollider Pbind pattern code
- `bpm` (float): Tempo for MIDI file (default: 120.0)

**Returns:** MIDI data as bytes

**Example:**
```python
midi = supercollider_to_midi('Pbind(\\freq, Pseq([440], 1)).play;', bpm=140)
```

### Utility Functions

#### `midi_to_freq(note)`

Convert MIDI note number to frequency in Hz.

```python
>>> midi_to_freq(69)  # A4
440.0
>>> midi_to_freq(60)  # C4
261.63
```

#### `freq_to_midi(freq)`

Convert frequency to nearest MIDI note.

```python
>>> freq_to_midi(440.0)
69
>>> freq_to_midi(261.63)
60
```

#### `quantize_time(time, grid=0.25)`

Quantize time to grid (in beats).

```python
>>> quantize_time(0.23, grid=0.25)  # Snap to 16th note
0.25
>>> quantize_time(1.1, grid=0.5)    # Snap to 8th note
1.0
```

## Output Formats

### Pbind (Default)

Standard pattern binding with Pseq arrays:

```supercollider
Pbind(
    \instrument, \tb303,
    \dur, Pseq([0.25, 0.25, 0.5], 1),
    \freq, Pseq([261.63, 293.66, 329.63], 1),
    \amp, Pseq([0.8, 0.6, 0.9], 1),
    \legato, Pseq([1.0, 0.8, 1.0], 1)
).play;
```

### Routine

Explicit timing with Synth creation:

```supercollider
Routine({
    Synth(\tb303, [\freq, 261.63, \amp, 0.8, \sustain, 0.25]);
    0.25.wait;
    Synth(\tb303, [\freq, 293.66, \amp, 0.6, \sustain, 0.25]);
    0.25.wait;
}).play;
```

### Pdef

Named pattern definition with infinite looping:

```supercollider
Pdef(\midi_pattern,
    Pbind(
        \instrument, \tb303,
        \dur, Pseq([0.25, 0.25, 0.5], inf),
        \freq, Pseq([261.63, 293.66, 329.63], inf),
        \amp, Pseq([0.8, 0.6, 0.9], inf)
    )
);
```

## Common Patterns

### TB-303 Acid Bassline

```python
# Create acid pattern in MIDI
midi_bytes = create_acid_pattern()

# Convert with tb303 synth
sc_code = midi_to_supercollider(
    midi_bytes,
    synth_name="tb303",
    output_format="pbind"
)

# Add effects in SuperCollider
enhanced = sc_code.replace('.play;', '''
    <> (cutoff: 1200, resonance: 0.85)
).play;''')
```

### Drum Patterns

```python
# Convert drum MIDI
drum_pattern = midi_to_supercollider(
    drum_midi,
    synth_name="808",
    output_format="pbind"
)
```

### Round-Trip Conversion

```python
# MIDI → SC → MIDI
original_midi = load_midi('pattern.mid')
sc_code = midi_to_supercollider(original_midi)
reconstructed_midi = supercollider_to_midi(sc_code)

# Notes are preserved (timing may be quantized)
```

## Implementation Details

### MIDI Parsing
- Uses `mido` library for MIDI file parsing
- Extracts note on/off events with timing
- Tracks polyphonic notes (multiple simultaneous notes)
- Handles missing note_off events gracefully

### Timing
- Converts MIDI ticks to beats using `ticks_per_beat`
- Calculates durations between consecutive notes
- Preserves legato information (note duration vs. inter-note spacing)
- Default minimum duration: 0.01 beats

### SuperCollider Parsing
- Uses regex to extract Pseq arrays
- Supports both `\\freq` and `\\midinote` parameters
- Handles missing duration/amplitude arrays with defaults
- Fallback to minimal valid code on parse errors

### Polyphony
- Sequential playback: Overlapping notes are played one after another
- Each note becomes a separate event in the pattern
- Future enhancement: Could generate multiple Pbind layers

## Examples

See `examples/midi_sc_example.py` for complete working examples including:
- Simple melody conversion
- TB-303 acid bassline
- All three output formats
- Round-trip conversion
- Utility function usage

## Testing

```bash
# Run all tests
pytest tests/unit/converters/test_midi_sc.py -v

# Run specific test
pytest tests/unit/converters/test_midi_sc.py::TestMidiToSupercollider::test_simple_midi_to_pbind
```

Tests cover:
- Basic MIDI → SC conversion
- All output formats (Pbind, Routine, Pdef)
- SC → MIDI conversion
- Round-trip conversion
- Polyphonic content
- Edge cases (empty MIDI, invalid data, extreme note ranges)
- Utility functions

## Requirements

- Python 3.12+
- mido >= 1.3.0

## Related Modules

- `midi_tidal.py`: MIDI ↔ TidalCycles conversion
- `interfaces.py`: Protocol definitions and type hints
