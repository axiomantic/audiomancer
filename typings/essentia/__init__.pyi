"""Type stubs for essentia-tensorflow (C++ bindings).

Essentia is a C++ library with Python bindings for audio analysis.
These stubs cover the subset of the API actually used by audiomancer.

See: https://essentia.upf.edu/
"""
import numpy as np
import numpy.typing as npt

# Essentia standard module
class standard:
    """Essentia standard algorithms namespace."""

    # TensorFlow models
    class TensorflowPredict:
        """Generic TensorFlow model predictor."""
        def __init__(
            self,
            graphFilename: str,
            input: str = ...,
            output: str = ...,
        ) -> None: ...
        def __call__(
            self, audio: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class TensorflowPredict2D:
        """TensorFlow model predictor with 2D output."""
        def __init__(
            self,
            graphFilename: str,
            input: str = ...,
            output: str = ...,
        ) -> None: ...
        def __call__(
            self, embeddings: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class TensorflowPredictEffnetDiscogs:
        """Discogs-EffNet embedding extractor."""
        def __init__(
            self,
            graphFilename: str,
            output: str = ...,
        ) -> None: ...
        def __call__(
            self, audio: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class TensorflowPredictMusiCNN:
        """MusiCNN embedding extractor."""
        def __init__(
            self,
            graphFilename: str,
            output: str = ...,
        ) -> None: ...
        def __call__(
            self, audio: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class TensorflowPredictVGGish:
        """VGGish embedding extractor."""
        def __init__(
            self,
            graphFilename: str,
            output: str = ...,
        ) -> None: ...
        def __call__(
            self, audio: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    # Spectral analysis
    class Spectrum:
        """Extract spectrum from audio frame."""
        def __init__(self) -> None: ...
        def __call__(
            self, frame: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class Windowing:
        """Apply window function to audio frame."""
        def __init__(
            self,
            type: str = "hann",
            size: int = 2048,
        ) -> None: ...
        def __call__(
            self, frame: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class Centroid:
        """Compute spectral centroid."""
        def __init__(self, range: float = ...) -> None: ...
        def __call__(
            self, spectrum: npt.NDArray[np.float32]
        ) -> float: ...

    class CentralMoments:
        """Compute central moments of spectrum."""
        def __init__(self) -> None: ...
        def __call__(
            self, spectrum: npt.NDArray[np.float32]
        ) -> npt.NDArray[np.float32]: ...

    class RollOff:
        """Compute spectral rolloff."""
        def __init__(self) -> None: ...
        def __call__(
            self, spectrum: npt.NDArray[np.float32]
        ) -> float: ...

    class ZeroCrossingRate:
        """Compute zero crossing rate."""
        def __init__(self) -> None: ...
        def __call__(
            self, frame: npt.NDArray[np.float32]
        ) -> float: ...

    class RMS:
        """Compute RMS energy."""
        def __init__(self) -> None: ...
        def __call__(
            self, frame: npt.NDArray[np.float32]
        ) -> float: ...

    class SpectralPeaks:
        """Detect spectral peaks."""
        def __init__(self) -> None: ...
        def __call__(
            self, spectrum: npt.NDArray[np.float32]
        ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]: ...

    # Rhythm analysis
    class RhythmExtractor2013:
        """Extract rhythm features (BPM, beats, etc.)."""
        def __init__(self, method: str = "multifeature") -> None: ...
        def __call__(
            self, audio: npt.NDArray[np.float32]
        ) -> tuple[
            float,  # bpm
            npt.NDArray[np.float32],  # beats
            float,  # beats_confidence
            npt.NDArray[np.float32],  # estimates
            npt.NDArray[np.float32],  # bpm_intervals
        ]: ...

    # Tonal analysis
    class KeyExtractor:
        """Extract musical key."""
        def __init__(self) -> None: ...
        def __call__(
            self, audio: npt.NDArray[np.float32]
        ) -> tuple[str, str, float]: ...  # (key, scale, strength)

    class TuningFrequency:
        """Detect tuning frequency."""
        def __init__(self) -> None: ...
        def __call__(
            self,
            frequencies: npt.NDArray[np.float32],
            magnitudes: npt.NDArray[np.float32],
        ) -> tuple[float, float]: ...  # (tuning_freq, tuning_cents)

    class PitchSalience:
        """Compute pitch salience."""
        def __init__(self) -> None: ...
        def __call__(
            self, spectrum: npt.NDArray[np.float32]
        ) -> float: ...
