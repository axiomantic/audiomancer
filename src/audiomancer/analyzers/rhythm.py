"""Rhythm analysis for audiomancer.

Extracts tempo, beat positions, and loop detection using Essentia.
"""

import essentia.standard as es
import numpy as np
from typing import Optional, Any

from ..errors import AnalysisFailedError


def extract_rhythm_features(
    audio: np.ndarray,
    sr: int
) -> dict[str, Any]:
    """
    Extract rhythm/tempo features using Essentia.

    Algorithms:
    - RhythmExtractor2013: BPM detection with confidence
    - BeatTrackerDegara: Beat positions
    - OnsetDetection: Transient detection

    Args:
        audio: Audio samples (mono or stereo)
        sr: Sample rate in Hz

    Returns:
        dict with keys:
        - bpm: float or None (tempo in beats per minute, None for non-rhythmic)
        - bpm_confidence: float (0-1)
        - beat_positions: list[float] (beat times in seconds)
        - is_loop: bool (True if audio appears to be a rhythmic loop)

    Raises:
        AnalysisFailedError: If extraction fails due to invalid audio data

    Example:
        >>> y, sr = librosa.load("loop_125bpm.wav", sr=None)
        >>> features = extract_rhythm_features(y, sr)
        >>> features['bpm']
        125.0
        >>> features['bpm_confidence']
        0.95
        >>> features['is_loop']
        True
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
                details={"stage": "rhythm_extraction", "reason": "empty input"}
            )

        if np.all(audio == 0) or np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
            # Silence or invalid data - return None for BPM
            return {
                'bpm': None,
                'bpm_confidence': 0.0,
                'beat_positions': [],
                'is_loop': False,
            }

        # BPM extraction
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, beats, beats_confidence, _, _ = rhythm_extractor(audio)

        # Convert beat positions to seconds (they come as samples from Essentia)
        beat_positions = [float(b) for b in beats]

        # Calculate average confidence (beats_confidence is a float, not array)
        avg_confidence = float(beats_confidence) if not np.isnan(beats_confidence) else 0.0

        # Only report BPM if:
        # 1. BPM > 0 (Essentia returns 0 for non-rhythmic content)
        # 2. Confidence is reasonable (> 0.2)
        # 3. We have some beats detected
        bpm_value = None
        if bpm > 0 and avg_confidence > 0.2 and len(beats) > 0:
            bpm_value = float(bpm)

        # Determine if loop (check if duration matches bar boundaries)
        duration_sec = len(audio) / sr
        is_loop = False

        if bpm_value is not None and bpm_value > 0:
            beat_duration = 60.0 / bpm_value
            bar_duration = beat_duration * 4  # 4/4 time signature
            bars = duration_sec / bar_duration

            # Is loop if:
            # 1. Close to whole number of bars (within 10%)
            # 2. Duration is less than 30 seconds (typical loop length)
            # 3. We have at least 1 bar
            if bars >= 1 and abs(bars - round(bars)) < 0.1 and duration_sec < 30:
                is_loop = True

        return {
            'bpm': bpm_value,
            'bpm_confidence': avg_confidence,
            'beat_positions': beat_positions,
            'is_loop': is_loop,
        }

    except Exception as e:
        if isinstance(e, AnalysisFailedError):
            raise
        raise AnalysisFailedError(
            "Rhythm extraction failed",
            details={
                "stage": "rhythm_extraction",
                "error": str(e),
                "audio_shape": audio.shape if hasattr(audio, 'shape') else None,
                "sample_rate": sr,
            }
        ) from e
