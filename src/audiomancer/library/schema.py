"""TypedDict definitions for library management."""

from typing import TypedDict, Optional


class SampleInfo(TypedDict, total=False):
    """Information about a single sample folder in the library."""

    id: str  # e.g., "808dk_bd", "absttex_hh_125"
    category: str  # e.g., "bd", "sn", "hh", "oh", "perc", "bass", "synth"
    category_type: str  # e.g., "drum", "perc", "bass", "melodic", "vocal", "fx", "loop"
    bpm: Optional[int]  # Detected BPM from filename, if any
    is_loop: bool  # True if detected as loop, False if one-shot
    file_count: int  # Number of audio files in this sample folder
    pack_name: str  # Original pack name from source
    enabled: bool  # True if symlinked in library/


class PackInfo(TypedDict):
    """Information about a sample pack from the source."""

    name: str  # Pack folder name
    file_count: int  # Total audio files in pack
    size_mb: float  # Total size in megabytes
    sample_ids: list[str]  # List of sample IDs that would be created


class PackStatus(TypedDict):
    """Detailed status of a sample pack."""

    name: str
    status: str  # "enabled", "cached", "remote"
    file_count: int
    size_mb: float
    samples: dict[str, str]  # sample_id -> "enabled"/"cached"/"remote"


class CopyStats(TypedDict):
    """Statistics from a copy operation."""

    copied: int  # Files copied
    skipped: int  # Files already existed
    too_large: int  # Files skipped due to size
    errors: int  # Files that failed to copy


class EnableResult(TypedDict):
    """Result from enabling a pack."""

    pack_name: str
    copy_stats: CopyStats
    samples_enabled: int
    sample_ids: list[str]
