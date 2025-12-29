#!/usr/bin/env python3
"""Script to generate test sample fixtures.

This creates standardized test audio files for use in unit tests.
Run this script to regenerate test fixtures if needed.
"""
import numpy as np
import soundfile as sf
from pathlib import Path


def create_test_audio(
    duration: float = 1.0,
    sample_rate: int = 44100,
    frequency: float = 440.0,
    waveform: str = "sine",
) -> np.ndarray:
    """Create test audio data."""
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    if waveform == "sine":
        audio = np.sin(2 * np.pi * frequency * t)
    elif waveform == "square":
        audio = np.sign(np.sin(2 * np.pi * frequency * t))
    elif waveform == "saw":
        audio = 2 * (t * frequency % 1) - 1
    elif waveform == "noise":
        audio = np.random.uniform(-1, 1, samples)
    elif waveform == "silence":
        audio = np.zeros(samples)
    else:
        raise ValueError(f"Unknown waveform: {waveform}")

    return audio.astype(np.float32)


def main():
    """Generate test sample fixtures."""
    samples_dir = Path(__file__).parent / "samples"
    samples_dir.mkdir(exist_ok=True)

    # Create various test samples
    test_cases = [
        ("kick_440hz.wav", 0.25, 44100, 440, "sine"),
        ("snare_noise.wav", 0.15, 44100, 0, "noise"),
        ("hihat_8khz.wav", 0.08, 44100, 8000, "sine"),
        ("bass_100hz.wav", 0.5, 44100, 100, "sine"),
        ("silence_1s.wav", 1.0, 44100, 0, "silence"),
    ]

    for filename, duration, sr, freq, waveform in test_cases:
        audio = create_test_audio(duration, sr, freq, waveform)
        output_path = samples_dir / filename
        sf.write(str(output_path), audio, sr)
        print(f"Created: {output_path}")

    print(f"\nGenerated {len(test_cases)} test sample files")


if __name__ == "__main__":
    main()
