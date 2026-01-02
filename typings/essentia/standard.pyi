"""Type stubs for essentia.standard module.

This module contains all the standard algorithms from Essentia.
Only classes actually used in the audiomancer codebase are typed here.
"""

import numpy as np
import numpy.typing as npt
from typing import Any, Literal

# TensorFlow prediction models
class TensorflowPredict:
    """Base TensorFlow predictor for audio embeddings."""
    def __init__(
        self,
        graphFilename: str,
        input: str = "model/Placeholder",
        output: str = "model/Sigmoid",
    ) -> None: ...

    def __call__(self, data: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

class TensorflowPredict2D:
    """TensorFlow predictor for 2D outputs (e.g., classifiers)."""
    def __init__(
        self,
        graphFilename: str,
        input: str = "model/Placeholder",
        output: str = "model/Sigmoid",
    ) -> None: ...

    def __call__(self, data: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

class TensorflowPredictEffnetDiscogs:
    """Effnet model for music embeddings from Discogs dataset."""
    def __init__(
        self,
        graphFilename: str,
        input: str = "serving_default_melspectrogram",
        output: str = "PartitionedCall:1",
    ) -> None: ...

    def __call__(self, audio: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Returns embeddings only (single array, not tuple)."""
        ...

class TensorflowPredictMusiCNN:
    """MusiCNN model for music tagging."""
    def __init__(
        self,
        graphFilename: str,
        input: str = "model/Placeholder",
        output: str = "model/Sigmoid",
    ) -> None: ...

    def __call__(self, audio: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

class TensorflowPredictVGGish:
    """VGGish model for audio embeddings."""
    def __init__(
        self,
        graphFilename: str,
        input: str = "model/Placeholder",
        output: str = "model/vggish/embeddings",
    ) -> None: ...

    def __call__(self, audio: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

# Spectral analysis algorithms
class Spectrum:
    """Computes the magnitude spectrum of an audio signal."""
    def __init__(self, size: int = 2048) -> None: ...

    def __call__(self, frame: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

class Windowing:
    """Applies a window function to a frame."""
    def __init__(
        self,
        type: str = "hann",
        size: int = 1024,
        normalized: bool = True,
        zeroPhase: bool = True,
    ) -> None: ...

    def __call__(self, frame: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

class Centroid:
    """Computes the spectral centroid."""
    def __init__(self, range: float = 22050.0) -> None: ...

    def __call__(self, spectrum: npt.NDArray[np.float32]) -> float: ...

class CentralMoments:
    """Computes central moments of an array."""
    def __init__(self, range: float = 22050.0, mode: str = "pdf") -> None: ...

    def __call__(self, spectrum: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]: ...

class RollOff:
    """Computes the spectral rolloff frequency."""
    def __init__(self, cutoff: float = 0.85, sampleRate: float = 44100.0) -> None: ...

    def __call__(self, spectrum: npt.NDArray[np.float32]) -> float: ...

class ZeroCrossingRate:
    """Computes the zero-crossing rate of a signal."""
    def __init__(self, threshold: float = 0.0) -> None: ...

    def __call__(self, frame: npt.NDArray[np.float32]) -> float: ...

class RMS:
    """Computes the root mean square of a signal."""
    def __init__(self) -> None: ...

    def __call__(self, frame: npt.NDArray[np.float32]) -> float: ...

class SpectralPeaks:
    """Detects spectral peaks."""
    def __init__(
        self,
        magnitudeThreshold: float = 0.0,
        maxPeaks: int = 100,
        minPosition: float = 0.0,
        maxPosition: float = 22050.0,
        orderBy: str = "magnitude",
        sampleRate: float = 44100.0,
    ) -> None: ...

    def __call__(
        self,
        spectrum: npt.NDArray[np.float32],
    ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]: ...

# Rhythm analysis
class RhythmExtractor2013:
    """Extracts rhythm features including BPM."""
    def __init__(
        self,
        method: Literal["multifeature", "degara"] = "multifeature",
        maxTempo: float = 208.0,
        minTempo: float = 40.0,
    ) -> None: ...

    def __call__(
        self,
        signal: npt.NDArray[np.float32],
    ) -> tuple[
        float,  # bpm
        npt.NDArray[np.float32],  # beats
        float,  # beats_confidence
        npt.NDArray[np.float32],  # estimates
        npt.NDArray[np.float32],  # bpm_intervals
    ]: ...

# Tonal analysis
class KeyExtractor:
    """Extracts the musical key of a signal."""
    def __init__(
        self,
        averageDetuningCorrection: bool = True,
        profileType: str = "temperley",
    ) -> None: ...

    def __call__(
        self,
        signal: npt.NDArray[np.float32],
    ) -> tuple[str, str, float]: ...  # key, scale, strength

class PitchSalience:
    """Computes pitch salience of a spectrum."""
    def __init__(self, sampleRate: float = 44100.0) -> None: ...

    def __call__(self, spectrum: npt.NDArray[np.float32]) -> float: ...

class TuningFrequency:
    """Estimates the tuning frequency."""
    def __init__(self, resolution: float = 1.0) -> None: ...

    def __call__(
        self,
        frequencies: npt.NDArray[np.float32],
        magnitudes: npt.NDArray[np.float32],
    ) -> tuple[float, float]: ...  # tuning_frequency, tuning_cents

# Audio I/O
class MonoLoader:
    """Loads audio file as mono signal."""
    def __init__(
        self,
        filename: str = "",
        sampleRate: float = 44100.0,
        downmix: str = "mix",
        resampleQuality: int = 1,
    ) -> None: ...

    def __call__(self) -> npt.NDArray[np.float32]: ...
