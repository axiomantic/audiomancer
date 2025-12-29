"""Tonal analysis for audiomancer.

Extracts key, tuning, and pitch salience using Essentia.
"""

import essentia.standard as es
import numpy as np

from ..errors import AnalysisFailedError


def extract_tonal_features(
    audio: np.ndarray,
    sr: int
) -> dict:
    """
    Extract tonal/pitch features using Essentia.

    Algorithms:
    - KeyExtractor: Key and scale detection
    - PitchYin: Pitch tracking for salience
    - TuningFrequency: Reference tuning detection

    Args:
        audio: Audio samples (mono or stereo)
        sr: Sample rate in Hz

    Returns:
        dict with keys:
        - key: str or None (e.g., "C", "Dm", "F#m", None for percussion/noise)
        - key_confidence: float (0-1)
        - tuning_frequency: float (Hz, typically ~440)
        - pitch_salience: float (0-1, how tonal vs percussive)

    Raises:
        AnalysisFailedError: If extraction fails due to invalid audio data

    Example:
        >>> y, sr = librosa.load("bass_c.wav", sr=None)
        >>> features = extract_tonal_features(y, sr)
        >>> features['key']
        'C'
        >>> features['pitch_salience']
        0.85
    """
    try:
        # Ensure mono float32
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)
        audio = audio.astype(np.float32)

        # Validate audio is not all zeros or NaN
        if len(audio) == 0:
            raise AnalysisFailedError(
                "Cannot analyze empty audio",
                details={"stage": "tonal_extraction", "reason": "empty input"}
            )

        if np.all(audio == 0) or np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
            # Silence or invalid data - return default values
            return {
                'key': None,
                'key_confidence': 0.0,
                'tuning_frequency': 440.0,
                'pitch_salience': 0.0,
            }

        # Key extraction
        key_extractor = es.KeyExtractor()
        key, scale, strength = key_extractor(audio)

        # Format key string (e.g., "C major" -> "C", "A minor" -> "Am")
        # Only report key if confidence is reasonable (> 0.2)
        key_str = None
        if strength > 0.2:
            if scale == "minor":
                key_str = f"{key}m"
            else:
                key_str = key

        # Tuning frequency (requires spectral analysis first)
        # Extract spectrum for tuning detection
        spectrum_extractor = es.Spectrum()
        windowing = es.Windowing(type='hann')
        spectral_peaks = es.SpectralPeaks()

        # Collect spectral peaks from multiple frames
        all_frequencies = []
        all_magnitudes = []

        frame_size = 2048
        hop_size = 512

        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i+frame_size]
            windowed = windowing(frame)
            spectrum = spectrum_extractor(windowed)
            frequencies, magnitudes = spectral_peaks(spectrum)

            if len(frequencies) > 0:
                all_frequencies.extend(frequencies)
                all_magnitudes.extend(magnitudes)

        # Use tuning frequency if we have peaks, otherwise default to 440 Hz
        if len(all_frequencies) > 0:
            tuning_extractor = es.TuningFrequency()
            tuning_freq, tuning_cents = tuning_extractor(
                np.array(all_frequencies, dtype=np.float32),
                np.array(all_magnitudes, dtype=np.float32)
            )

            # Validate tuning frequency (should be around 440 Hz, between 400-480)
            # If detection fails, default to 440 Hz
            if tuning_freq < 400 or tuning_freq > 480 or np.isnan(tuning_freq):
                tuning_freq = 440.0
        else:
            tuning_freq = 440.0

        # Pitch salience (how tonal vs noisy/percussive)
        pitch_salience_extractor = es.PitchSalience()
        saliences = []

        # Process audio in frames (reusing extractors from above)
        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i+frame_size]
            windowed = windowing(frame)
            spectrum = spectrum_extractor(windowed)
            salience = pitch_salience_extractor(spectrum)

            # Only include valid salience values
            if not np.isnan(salience) and not np.isinf(salience):
                saliences.append(salience)

        # Calculate mean salience, or 0.0 if no valid frames
        mean_salience = float(np.mean(saliences)) if saliences else 0.0

        # Ensure all return values are valid (no NaN/inf)
        return {
            'key': key_str,
            'key_confidence': float(strength) if not np.isnan(strength) else 0.0,
            'tuning_frequency': float(tuning_freq),
            'pitch_salience': mean_salience,
        }

    except Exception as e:
        if isinstance(e, AnalysisFailedError):
            raise
        raise AnalysisFailedError(
            "Tonal extraction failed",
            details={
                "stage": "tonal_extraction",
                "error": str(e),
                "audio_shape": audio.shape if hasattr(audio, 'shape') else None,
                "sample_rate": sr,
            }
        ) from e
