# Test Fixtures

## samples/
Audio samples for testing analysis:
- kick_808.wav - Clean 808 kick drum (to be added)
- loop_125bpm.wav - 4-bar drum loop at 125 BPM (to be added)
- synth_c4.wav - 1 second sine tone at C4 (to be added)
- corrupt.wav - Invalid WAV header for error testing (to be added)

## synths/
SuperCollider SynthDef files for testing:
- simple_sine.scd - Minimal working SynthDef
- tb303.scd - Complex acid bass SynthDef

## midi/
MIDI files for converter testing:
- basic_beat.mid - Simple 4/4 beat (to be added)
- melody_cmaj.mid - C major melody (to be added)

## Notes

### Audio Fixtures
Audio fixtures should be created programmatically or added via Git LFS
to avoid bloating the repository. The conftest.py provides a
`sample_audio_data` fixture that generates test audio on-demand.

### Creating Audio Files
To create physical audio files for manual testing:

```python
import numpy as np
import soundfile as sf

# Generate 1 second sine wave at C4 (261.63 Hz)
sample_rate = 44100
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio = np.sin(2 * np.pi * 261.63 * t).astype(np.float32)
sf.write("synth_c4.wav", audio, sample_rate)
```

### Corrupt Files
For error testing, corrupt.wav should have an invalid header.
Create with: `echo "INVALID" > corrupt.wav`
