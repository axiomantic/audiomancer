"""Basic audio metadata extraction for audiomancer.

This module provides functions for extracting fundamental audio file metadata
such as duration, sample rate, channel count, and file hash.
"""

import hashlib
import librosa
from pathlib import Path
from typing import TypedDict

from ..errors import UnsupportedFormatError, AnalysisFailedError


class BasicMetadata(TypedDict):
    """Basic audio file metadata.

    Attributes:
        duration_ms: Audio duration in milliseconds
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        bit_depth: Bit depth (16 assumed for librosa float32 conversion)
        file_size_bytes: File size in bytes
        file_hash: SHA256 hex digest of file contents
    """
    duration_ms: float
    sample_rate: int
    channels: int
    bit_depth: int
    file_size_bytes: int
    file_hash: str


def get_basic_metadata(path: Path) -> BasicMetadata:
    """Extract basic audio metadata.

    Loads audio file using librosa and computes fundamental properties.
    The file is loaded with its native sample rate to preserve metadata accuracy.

    Args:
        path: Path to audio file

    Returns:
        Dictionary containing basic metadata:
        - duration_ms: Audio duration in milliseconds (float)
        - sample_rate: Native sample rate in Hz (int)
        - channels: Number of audio channels (int)
        - bit_depth: Bit depth, 16 assumed for librosa (int)
        - file_size_bytes: File size on disk in bytes (int)
        - file_hash: SHA256 hex digest for deduplication (str)

    Raises:
        UnsupportedFormatError: If file cannot be loaded by librosa
        AnalysisFailedError: If file is too short or contains invalid audio

    Example:
        >>> meta = get_basic_metadata(Path("kick.wav"))
        >>> meta['duration_ms']
        250.5
        >>> meta['sample_rate']
        44100
        >>> meta['channels']
        1
    """
    # Validate path exists
    if not path.exists():
        raise UnsupportedFormatError(
            f"File does not exist: {path}",
            details={"path": str(path), "error": "file not found"}
        )

    # Load audio with native sample rate
    try:
        y, sr = librosa.load(str(path), sr=None, mono=False)
    except Exception as e:
        raise UnsupportedFormatError(
            f"Cannot load audio file",
            details={"path": str(path), "error": str(e)}
        )

    # Determine channel count and duration
    if y.ndim > 1:
        channels = y.shape[0]
        duration_samples = y.shape[1]
    else:
        channels = 1
        duration_samples = len(y)

    # Validate audio has content
    if duration_samples == 0:
        raise AnalysisFailedError(
            "Audio file is empty",
            details={
                "path": str(path),
                "reason": "zero samples",
                "stage": "metadata extraction"
            }
        )

    # Calculate duration in milliseconds
    duration_ms = (duration_samples / sr) * 1000.0

    # Compute SHA256 hash for deduplication
    try:
        with open(path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        raise AnalysisFailedError(
            "Failed to compute file hash",
            details={
                "path": str(path),
                "error": str(e),
                "stage": "hash computation"
            }
        )

    # Get file size
    file_size_bytes = path.stat().st_size

    return BasicMetadata(
        duration_ms=float(duration_ms),
        sample_rate=int(sr),
        channels=int(channels),
        bit_depth=16,  # librosa loads as float32, assume 16-bit source
        file_size_bytes=int(file_size_bytes),
        file_hash=file_hash,
    )
