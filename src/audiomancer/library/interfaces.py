"""Protocol definitions for library management."""

from typing import Protocol, Optional

from .schema import PackInfo, PackStatus, SampleInfo, EnableResult


class SampleLookup(Protocol):
    """Interface for querying available samples by type.

    Used by pattern generation to find real sample IDs.
    """

    def get_samples_by_type(
        self,
        instrument_type: str,
        bpm: Optional[float] = None,
        is_loop: Optional[bool] = None,
        limit: int = 10,
    ) -> list[str]:
        """Return sample IDs matching the criteria.

        Args:
            instrument_type: Category to match (bd, sn, hh, oh, perc, bass, etc.)
            bpm: Optional BPM to filter by (matches samples with detected BPM)
            is_loop: Optional filter for loops vs one-shots
            limit: Maximum number of results

        Returns:
            List of sample IDs (e.g., ["808dk_bd", "absttex_bd_125"])
        """
        ...


class LibraryStore(Protocol):
    """Interface for library management operations."""

    def list_packs(self) -> list[PackInfo]:
        """List all available packs from source."""
        ...

    def search_packs(self, pattern: str) -> list[PackInfo]:
        """Search packs by name pattern."""
        ...

    def get_pack_status(self, pack_name: str) -> PackStatus:
        """Get detailed status of a pack."""
        ...

    def enable_pack(
        self,
        pack_name: str,
        max_size_mb: int = 10,
        workers: int = 16,
    ) -> EnableResult:
        """Enable a pack (copy from source and create symlinks)."""
        ...

    def disable_pack(self, pack_name: str) -> int:
        """Disable a pack (remove symlinks, keep cache). Returns count disabled."""
        ...

    def purge_pack(self, pack_name: str) -> bool:
        """Remove pack from cache entirely."""
        ...

    def list_enabled_samples(self) -> list[SampleInfo]:
        """List all enabled sample IDs with their info."""
        ...
