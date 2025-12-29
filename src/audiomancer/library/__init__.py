"""Sample library management module.

Provides tools for managing sample packs from Google Drive (or other sources)
with local caching, symlink management, and integration with pattern generation.
"""

from ..errors import LibraryError, PackNotFoundError, SourceNotAvailableError
from .interfaces import LibraryStore, SampleLookup
from .manager import LibraryManager
from .scanner import (
    scan_source_packs,
    scan_pack_files,
    group_files_into_samples,
    detect_category,
    detect_bpm,
    detect_is_loop,
    abbreviate_pack_name,
    generate_sample_id,
)
from .schema import (
    PackInfo,
    PackStatus,
    SampleInfo,
    CopyStats,
    EnableResult,
)

__all__ = [
    # Interfaces
    "LibraryStore",
    "SampleLookup",
    # Manager
    "LibraryManager",
    "LibraryError",
    "PackNotFoundError",
    "SourceNotAvailableError",
    # Scanner
    "scan_source_packs",
    "scan_pack_files",
    "group_files_into_samples",
    "detect_category",
    "detect_bpm",
    "detect_is_loop",
    "abbreviate_pack_name",
    "generate_sample_id",
    # Schema
    "PackInfo",
    "PackStatus",
    "SampleInfo",
    "CopyStats",
    "EnableResult",
]
