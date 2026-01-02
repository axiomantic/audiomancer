"""Type stubs for librosa audio analysis library.

Provides type hints for commonly used librosa functions in audiomancer.
"""

from typing import Literal, Optional, Union, overload
import numpy as np
import numpy.typing as npt

# Type aliases for clarity
AudioArray = npt.NDArray[np.float32]
SampleRate = int

@overload
def load(
    path: str,
    *,
    sr: None = None,
    mono: bool = True,
    offset: float = 0.0,
    duration: Optional[float] = None,
    dtype: type[np.float32] = np.float32,
    res_type: str = "soxr_hq",
) -> tuple[AudioArray, SampleRate]: ...

@overload
def load(
    path: str,
    *,
    sr: int,
    mono: bool = True,
    offset: float = 0.0,
    duration: Optional[float] = None,
    dtype: type[np.float32] = np.float32,
    res_type: str = "soxr_hq",
) -> tuple[AudioArray, int]: ...

def load(
    path: str,
    *,
    sr: Optional[int] = 22050,
    mono: bool = True,
    offset: float = 0.0,
    duration: Optional[float] = None,
    dtype: type[np.float32] = np.float32,
    res_type: str = "soxr_hq",
) -> tuple[AudioArray, int]:
    """Load an audio file as a floating point time series.

    Args:
        path: Path to the input file
        sr: Target sample rate. If None, uses the native sample rate
        mono: Convert signal to mono
        offset: Start reading after this time (in seconds)
        duration: Only load up to this much audio (in seconds)
        dtype: Data type of the output array
        res_type: Resample type

    Returns:
        Tuple of (audio_data, sample_rate):
        - audio_data: Audio time series (mono: shape (n,), stereo: shape (2, n))
        - sample_rate: Sampling rate of the audio
    """
    ...

def resample(
    y: AudioArray,
    *,
    orig_sr: int,
    target_sr: int,
    res_type: str = "soxr_hq",
    fix: bool = True,
    scale: bool = False,
    axis: int = -1,
) -> AudioArray:
    """Resample a time series from orig_sr to target_sr.

    Args:
        y: Audio time series (mono or multichannel)
        orig_sr: Original sample rate
        target_sr: Target sample rate
        res_type: Resample type (quality)
        fix: Adjust the length of the resampled signal to be exactly target_sr
        scale: Scale the resampled signal to preserve energy
        axis: Axis along which to resample

    Returns:
        Audio time series resampled to target_sr
    """
    ...

# Additional commonly used functions can be added here as needed
def get_duration(
    y: Optional[AudioArray] = None,
    sr: int = 22050,
    S: Optional[AudioArray] = None,
    n_fft: int = 2048,
    hop_length: int = 512,
    center: bool = True,
    filename: Optional[str] = None,
) -> float:
    """Compute the duration (in seconds) of an audio time series.

    Args:
        y: Audio time series
        sr: Sample rate
        S: STFT matrix, or any STFT-derived matrix
        n_fft: FFT window size
        hop_length: Number of samples between successive frames
        center: If True, frames are centered
        filename: If provided, load audio from this file

    Returns:
        Duration in seconds
    """
    ...

def get_samplerate(path: str) -> int:
    """Get the sampling rate for an audio file.

    Args:
        path: Path to the input file

    Returns:
        Sample rate in Hz
    """
    ...
