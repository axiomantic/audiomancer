#!/usr/bin/env python3
"""Generate comprehensive test fixtures for audiomancer.

Creates standardized test audio files with known characteristics:
- Pure tones at specific frequencies
- Drum patterns at known BPMs
- Noise samples with different characteristics
- Edge cases (silence, clipping, etc.)
"""

import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Literal


def create_pure_tone(
    frequency: float,
    duration: float = 1.0,
    sample_rate: int = 44100,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Create a pure sine tone at specified frequency."""
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)
    audio = amplitude * np.sin(2 * np.pi * frequency * t)
    return audio.astype(np.float32)


def create_drum_hit(
    drum_type: Literal["kick", "snare", "hihat", "tom"],
    duration: float = 0.25,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Create synthetic drum hit."""
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    if drum_type == "kick":
        # Low frequency with pitch envelope
        freq_env = 60 * np.exp(-20 * t)
        audio = np.sin(2 * np.pi * freq_env * t)
        amp_env = np.exp(-10 * t)
    elif drum_type == "snare":
        # White noise with fast decay
        audio = np.random.uniform(-1, 1, samples)
        amp_env = np.exp(-25 * t)
    elif drum_type == "hihat":
        # High-pass filtered noise with very fast decay
        audio = np.random.uniform(-1, 1, samples)
        audio = np.diff(audio, prepend=0)  # Simple high-pass
        amp_env = np.exp(-50 * t)
    elif drum_type == "tom":
        # Mid frequency with decay
        freq_env = 200 * np.exp(-15 * t)
        audio = np.sin(2 * np.pi * freq_env * t)
        amp_env = np.exp(-12 * t)
    else:
        raise ValueError(f"Unknown drum type: {drum_type}")

    return (audio * amp_env).astype(np.float32)


def create_drum_pattern(
    bpm: float,
    bars: int = 1,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Create a simple drum pattern at specified BPM."""
    beats_per_bar = 4
    beat_duration = 60.0 / bpm
    pattern_duration = bars * beats_per_bar * beat_duration
    samples = int(sample_rate * pattern_duration)

    audio = np.zeros(samples, dtype=np.float32)

    # Add kicks on beats 1 and 3
    for bar in range(bars):
        for beat in [0, 2]:
            start_time = (bar * beats_per_bar + beat) * beat_duration
            kick = create_drum_hit("kick", duration=0.15, sample_rate=sample_rate)
            start_sample = int(start_time * sample_rate)
            end_sample = min(start_sample + len(kick), len(audio))
            audio[start_sample:end_sample] += kick[:end_sample - start_sample]

    # Add snares on beats 2 and 4
    for bar in range(bars):
        for beat in [1, 3]:
            start_time = (bar * beats_per_bar + beat) * beat_duration
            snare = create_drum_hit("snare", duration=0.1, sample_rate=sample_rate)
            start_sample = int(start_time * sample_rate)
            end_sample = min(start_sample + len(snare), len(audio))
            audio[start_sample:end_sample] += snare[:end_sample - start_sample] * 0.7

    # Add hi-hats on all eighth notes
    for bar in range(bars):
        for eighth in range(beats_per_bar * 2):
            start_time = (bar * beats_per_bar + eighth * 0.5) * beat_duration
            hihat = create_drum_hit("hihat", duration=0.05, sample_rate=sample_rate)
            start_sample = int(start_time * sample_rate)
            end_sample = min(start_sample + len(hihat), len(audio))
            audio[start_sample:end_sample] += hihat[:end_sample - start_sample] * 0.3

    # Normalize to prevent clipping
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio * (0.9 / peak)

    return audio.astype(np.float32)


def create_noise(
    noise_type: Literal["white", "pink", "brown"],
    duration: float = 1.0,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Create different types of noise."""
    samples = int(sample_rate * duration)

    if noise_type == "white":
        audio = np.random.uniform(-1, 1, samples)
    elif noise_type == "pink":
        # Simple pink noise approximation (1/f)
        white = np.random.uniform(-1, 1, samples)
        audio = np.cumsum(white)
        audio = audio / np.max(np.abs(audio))
    elif noise_type == "brown":
        # Brownian noise (1/f^2)
        white = np.random.uniform(-1, 1, samples)
        audio = np.cumsum(np.cumsum(white))
        audio = audio / np.max(np.abs(audio))
    else:
        raise ValueError(f"Unknown noise type: {noise_type}")

    return audio.astype(np.float32)


def create_chord(
    root_freq: float,
    chord_type: Literal["major", "minor", "seventh"],
    duration: float = 1.0,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Create a chord with multiple harmonics."""
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Define intervals (semitones from root)
    if chord_type == "major":
        intervals = [0, 4, 7]  # Root, major third, fifth
    elif chord_type == "minor":
        intervals = [0, 3, 7]  # Root, minor third, fifth
    elif chord_type == "seventh":
        intervals = [0, 4, 7, 10]  # Root, major third, fifth, minor seventh
    else:
        raise ValueError(f"Unknown chord type: {chord_type}")

    audio = np.zeros(samples, dtype=np.float32)
    for semitones in intervals:
        freq = root_freq * (2 ** (semitones / 12))
        audio += np.sin(2 * np.pi * freq * t)

    # Normalize
    audio = audio / len(intervals)

    # Add envelope
    envelope = np.exp(-2 * t)
    audio = audio * envelope

    return audio.astype(np.float32)


def main():
    """Generate all test fixtures."""
    samples_dir = Path(__file__).parent / "samples"
    samples_dir.mkdir(exist_ok=True)

    print("Generating test fixtures...")

    # Pure tones at standard frequencies
    pure_tones = [
        ("tone_a440.wav", 440.0, 1.0),  # A4
        ("tone_c261.wav", 261.63, 1.0),  # C4
        ("tone_low_60hz.wav", 60.0, 0.5),  # Low bass
        ("tone_high_8khz.wav", 8000.0, 0.3),  # High frequency
    ]

    for filename, freq, duration in pure_tones:
        audio = create_pure_tone(freq, duration)
        sf.write(str(samples_dir / filename), audio, 44100)
        print(f"  ✓ {filename} ({freq} Hz, {duration}s)")

    # Drum hits
    drum_hits = [
        ("kick_synthetic.wav", "kick", 0.25),
        ("snare_synthetic.wav", "snare", 0.15),
        ("hihat_synthetic.wav", "hihat", 0.08),
        ("tom_synthetic.wav", "tom", 0.20),
    ]

    for filename, drum_type, duration in drum_hits:
        audio = create_drum_hit(drum_type, duration)
        sf.write(str(samples_dir / filename), audio, 44100)
        print(f"  ✓ {filename} ({drum_type}, {duration}s)")

    # Drum patterns at known BPMs
    drum_patterns = [
        ("pattern_120bpm_1bar.wav", 120.0, 1),
        ("pattern_140bpm_2bar.wav", 140.0, 2),
        ("pattern_90bpm_1bar.wav", 90.0, 1),
    ]

    for filename, bpm, bars in drum_patterns:
        audio = create_drum_pattern(bpm, bars)
        sf.write(str(samples_dir / filename), audio, 44100)
        print(f"  ✓ {filename} ({bpm} BPM, {bars} bars)")

    # Noise samples
    noise_samples = [
        ("noise_white_1s.wav", "white", 1.0),
        ("noise_pink_1s.wav", "pink", 1.0),
        ("noise_brown_1s.wav", "brown", 1.0),
    ]

    for filename, noise_type, duration in noise_samples:
        audio = create_noise(noise_type, duration)
        sf.write(str(samples_dir / filename), audio, 44100)
        print(f"  ✓ {filename} ({noise_type} noise, {duration}s)")

    # Musical chords
    chords = [
        ("chord_c_major.wav", 261.63, "major", 1.0),
        ("chord_a_minor.wav", 220.0, "minor", 1.0),
        ("chord_g_seventh.wav", 196.0, "seventh", 1.0),
    ]

    for filename, root, chord_type, duration in chords:
        audio = create_chord(root, chord_type, duration)
        sf.write(str(samples_dir / filename), audio, 44100)
        print(f"  ✓ {filename} ({chord_type} chord, {duration}s)")

    # Edge cases
    edge_cases = [
        ("silence_1s.wav", np.zeros(44100, dtype=np.float32)),
        ("impulse.wav", np.concatenate([
            np.array([1.0], dtype=np.float32),
            np.zeros(44099, dtype=np.float32)
        ])),
        ("dc_offset.wav", np.ones(44100, dtype=np.float32) * 0.5),
    ]

    for filename, audio in edge_cases:
        sf.write(str(samples_dir / filename), audio, 44100)
        print(f"  ✓ {filename} (edge case)")

    total_files = len(pure_tones) + len(drum_hits) + len(drum_patterns) + \
                  len(noise_samples) + len(chords) + len(edge_cases)

    print(f"\n✓ Generated {total_files} test fixture files in {samples_dir}")


if __name__ == "__main__":
    main()
