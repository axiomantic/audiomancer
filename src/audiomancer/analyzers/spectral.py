"""Spectral feature extraction for audiomancer.

This module provides spectral analysis functions using Essentia for
extracting features like spectral centroid, bandwidth, rolloff, and energy.
"""

import essentia.standard as es
import numpy as np
from typing import TypedDict

from ..errors import AnalysisFailedError


class SpectralFeatures(TypedDict):
    """Spectral audio features.

    All frequency values are in Hz, energy values are linear (0-1 range).

    Attributes:
        spectral_centroid: Mean brightness/center of mass of spectrum (Hz)
        spectral_bandwidth: Frequency spread around centroid (Hz proxy)
        spectral_rolloff: High-frequency content cutoff point (Hz)
        zero_crossing_rate: Measure of noisiness/percussiveness (0-1)
        rms_energy: Root-mean-square energy level (0-1 linear)
        dynamic_range: Peak-to-average ratio (dB)
    """
    spectral_centroid: float
    spectral_bandwidth: float
    spectral_rolloff: float
    zero_crossing_rate: float
    rms_energy: float
    dynamic_range: float


def extract_spectral_features(
    audio: np.ndarray,
    sr: int
) -> SpectralFeatures:
    """Extract spectral features using Essentia.

    Performs frame-based spectral analysis to extract features that describe
    the frequency content and energy distribution of the audio signal.

    Algorithms used:
    - Centroid: Spectral center of mass, indicates brightness (Hz)
    - Bandwidth: Frequency spread via 2nd central moment (Hz proxy)
    - Rolloff: Frequency below which 85% of energy is contained (Hz)
    - ZeroCrossingRate: Time-domain noisiness measure (0-1)
    - RMS: Root-mean-square energy level (0-1 linear)
    - DynamicRange: Peak-to-RMS ratio in dB

    Args:
        audio: Audio data as numpy array (mono or stereo)
        sr: Sample rate in Hz

    Returns:
        Dictionary containing spectral features with units documented

    Raises:
        AnalysisFailedError: If audio is too short, empty, or analysis fails

    Example:
        >>> import librosa
        >>> y, sr = librosa.load("kick.wav", sr=None)
        >>> features = extract_spectral_features(y, sr)
        >>> features['spectral_centroid']
        1523.5  # Hz - indicates a bright sound
        >>> features['rms_energy']
        0.45  # Linear energy level
        >>> features['dynamic_range']
        18.2  # dB peak-to-average ratio
    """
    # Ensure mono audio for analysis
    if audio.ndim > 1:
        audio = np.mean(audio, axis=0)

    # Ensure float32 for Essentia compatibility
    audio = audio.astype(np.float32)

    # Validate audio has content
    if len(audio) == 0:
        raise AnalysisFailedError(
            "Cannot analyze empty audio",
            details={
                "reason": "zero samples",
                "stage": "spectral analysis preparation"
            }
        )

    # Check for minimum length (need at least one frame)
    frame_size = 2048
    if len(audio) < frame_size:
        raise AnalysisFailedError(
            "Audio too short for spectral analysis",
            details={
                "reason": f"audio length {len(audio)} < frame size {frame_size}",
                "stage": "spectral analysis preparation",
                "min_samples": frame_size,
                "actual_samples": len(audio)
            }
        )

    # Initialize Essentia algorithms
    try:
        spectrum_extractor = es.Spectrum()
        windowing = es.Windowing(type='hann', size=frame_size)
        centroid_algo = es.Centroid(range=sr/2)
        central_moments = es.CentralMoments()
        rolloff_algo = es.RollOff()
        zcr_algo = es.ZeroCrossingRate()
        rms_algo = es.RMS()
    except Exception as e:
        raise AnalysisFailedError(
            "Failed to initialize Essentia algorithms",
            details={
                "error": str(e),
                "stage": "algorithm initialization"
            }
        )

    # Frame-based analysis
    hop_size = 512
    centroids = []
    bandwidths = []
    rolloffs = []
    zcrs = []
    rms_values = []

    try:
        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i+frame_size]

            # Apply Hann window
            windowed = windowing(frame)

            # Compute spectrum
            spectrum = spectrum_extractor(windowed)

            # Extract features
            centroids.append(centroid_algo(spectrum))

            # Use 2nd central moment as bandwidth proxy
            moments = central_moments(spectrum)
            if len(moments) > 1:
                bandwidths.append(abs(moments[1]))
            else:
                bandwidths.append(0.0)

            rolloffs.append(rolloff_algo(spectrum))
            zcrs.append(zcr_algo(frame))
            rms_values.append(rms_algo(frame))

    except Exception as e:
        raise AnalysisFailedError(
            "Spectral feature extraction failed",
            details={
                "error": str(e),
                "stage": "frame-based analysis"
            }
        )

    # Validate we got features
    if len(centroids) == 0:
        raise AnalysisFailedError(
            "No features extracted",
            details={
                "reason": "no valid frames",
                "stage": "spectral analysis"
            }
        )

    # Compute dynamic range
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio**2)))

    # Avoid log of zero
    if rms > 0 and peak > 0:
        dynamic_range = 20 * np.log10(peak / rms)
    else:
        dynamic_range = 0.0

    # Convert lists to arrays for mean calculation
    centroids_arr = np.array(centroids)
    bandwidths_arr = np.array(bandwidths)
    rolloffs_arr = np.array(rolloffs)
    zcrs_arr = np.array(zcrs)
    rms_arr = np.array(rms_values)

    # Validate no NaN or inf values
    def validate_value(value: float, name: str) -> float:
        if np.isnan(value) or np.isinf(value):
            raise AnalysisFailedError(
                f"Invalid {name} value",
                details={
                    "reason": f"{name} is NaN or inf",
                    "stage": "feature validation",
                    "value": str(value)
                }
            )
        return float(value)

    # Return mean values across all frames
    return SpectralFeatures(
        spectral_centroid=validate_value(np.mean(centroids_arr), "spectral_centroid"),
        spectral_bandwidth=validate_value(np.mean(bandwidths_arr), "spectral_bandwidth"),
        spectral_rolloff=validate_value(np.mean(rolloffs_arr), "spectral_rolloff"),
        zero_crossing_rate=validate_value(np.mean(zcrs_arr), "zero_crossing_rate"),
        rms_energy=validate_value(np.mean(rms_arr), "rms_energy"),
        dynamic_range=validate_value(dynamic_range, "dynamic_range"),
    )
