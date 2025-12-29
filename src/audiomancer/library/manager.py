"""Library management for sample packs.

Provides LibraryManager class for enabling/disabling sample packs from
Google Drive (or other source) with local caching and symlink management.
"""

import asyncio
import re
import shutil
from pathlib import Path
from typing import Optional

from ..errors import LibraryError, PackNotFoundError, SourceNotAvailableError
from .scanner import (
    scan_source_packs,
    scan_pack_files,
    group_files_into_samples,
    AUDIO_EXTENSIONS,
)
from .schema import (
    PackInfo,
    PackStatus,
    SampleInfo,
    CopyStats,
    EnableResult,
)


class _CopyStats:
    """Thread-safe copy statistics tracker."""

    def __init__(self):
        self.copied = 0
        self.skipped = 0
        self.too_large = 0
        self.errors = 0
        self._lock = asyncio.Lock()

    async def add_copied(self):
        async with self._lock:
            self.copied += 1

    async def add_skipped(self):
        async with self._lock:
            self.skipped += 1

    async def add_too_large(self):
        async with self._lock:
            self.too_large += 1

    async def add_error(self):
        async with self._lock:
            self.errors += 1

    def to_dict(self) -> CopyStats:
        return CopyStats(
            copied=self.copied,
            skipped=self.skipped,
            too_large=self.too_large,
            errors=self.errors,
        )


class LibraryManager:
    """Manages sample library from source (Google Drive) to local project.

    Handles:
    - Scanning source for available packs
    - Copying packs to local cache (samples/)
    - Creating symlinks for enabled packs (library/)
    - Querying enabled samples for pattern generation
    """

    def __init__(
        self,
        source_dir: Path,
        samples_dir: Path,
        library_dir: Path,
        ignore_patterns: Optional[set[str]] = None,
    ):
        """Initialize library manager.

        Args:
            source_dir: Path to source samples (e.g., Google Drive)
            samples_dir: Path to local cache directory
            library_dir: Path to enabled samples directory (symlinks)
            ignore_patterns: Set of pack names to ignore
        """
        self.source_dir = Path(source_dir).expanduser().resolve()
        self.samples_dir = Path(samples_dir).expanduser().resolve()
        self.library_dir = Path(library_dir).expanduser().resolve()
        self.ignore_patterns = ignore_patterns or set()

    def _check_source(self) -> None:
        """Verify source directory is accessible."""
        if not self.source_dir.exists():
            raise SourceNotAvailableError(self.source_dir)

    def _should_ignore(self, pack_name: str) -> bool:
        """Check if pack should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern == pack_name:
                return True
            if pattern.endswith("*") and pack_name.startswith(pattern[:-1]):
                return True
        return False

    def _get_cached_sample_ids(self) -> set[str]:
        """Get sample IDs in local cache."""
        if not self.samples_dir.exists():
            return set()
        return {
            d.name
            for d in self.samples_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        }

    def _get_enabled_sample_ids(self) -> set[str]:
        """Get sample IDs that are enabled (symlinked)."""
        if not self.library_dir.exists():
            return set()
        return {
            d.name
            for d in self.library_dir.iterdir()
            if d.is_symlink() or d.is_dir()
        }

    def list_packs(self) -> list[PackInfo]:
        """List all available packs from source.

        Returns:
            List of PackInfo for each pack in source directory
        """
        self._check_source()

        result = []
        for pack_name in scan_source_packs(self.source_dir):
            if self._should_ignore(pack_name):
                continue

            files = scan_pack_files(self.source_dir, pack_name)
            samples = group_files_into_samples(pack_name, files)
            total_size = sum(f["size"] for f in files)

            result.append(
                PackInfo(
                    name=pack_name,
                    file_count=len(files),
                    size_mb=total_size / (1024 * 1024),
                    sample_ids=list(samples.keys()),
                )
            )

        return result

    def search_packs(self, pattern: str) -> list[PackInfo]:
        """Search packs by name pattern.

        Args:
            pattern: Regex pattern to match against pack names

        Returns:
            List of matching PackInfo
        """
        self._check_source()

        regex = re.compile(pattern, re.IGNORECASE)
        packs = scan_source_packs(self.source_dir)
        matches = [p for p in packs if regex.search(p) and not self._should_ignore(p)]

        result = []
        for pack_name in matches:
            files = scan_pack_files(self.source_dir, pack_name)
            samples = group_files_into_samples(pack_name, files)
            total_size = sum(f["size"] for f in files)

            result.append(
                PackInfo(
                    name=pack_name,
                    file_count=len(files),
                    size_mb=total_size / (1024 * 1024),
                    sample_ids=list(samples.keys()),
                )
            )

        return result

    def get_pack_status(self, pack_name: str) -> PackStatus:
        """Get detailed status of a pack.

        Args:
            pack_name: Name of pack folder

        Returns:
            PackStatus with enabled/cached/remote status for each sample

        Raises:
            PackNotFoundError: If pack doesn't exist in source
        """
        self._check_source()

        pack_dir = self.source_dir / pack_name
        if not pack_dir.exists():
            raise PackNotFoundError(pack_name, self.source_dir)

        files = scan_pack_files(self.source_dir, pack_name)
        samples = group_files_into_samples(pack_name, files)
        total_size = sum(f["size"] for f in files)

        cached_ids = self._get_cached_sample_ids()
        enabled_ids = self._get_enabled_sample_ids()

        sample_statuses = {}
        for sample_id in samples.keys():
            if sample_id in enabled_ids:
                sample_statuses[sample_id] = "enabled"
            elif sample_id in cached_ids:
                sample_statuses[sample_id] = "cached"
            else:
                sample_statuses[sample_id] = "remote"

        # Overall status
        if any(s == "enabled" for s in sample_statuses.values()):
            status = "enabled"
        elif any(s == "cached" for s in sample_statuses.values()):
            status = "cached"
        else:
            status = "remote"

        return PackStatus(
            name=pack_name,
            status=status,
            file_count=len(files),
            size_mb=total_size / (1024 * 1024),
            samples=sample_statuses,
        )

    def _enable_sample(self, sample_id: str) -> bool:
        """Create symlink in library/ for a cached sample."""
        source = self.samples_dir / sample_id
        target = self.library_dir / sample_id

        if not source.exists():
            return False

        self.library_dir.mkdir(parents=True, exist_ok=True)

        if target.exists() or target.is_symlink():
            return True

        target.symlink_to(source)
        return True

    def _disable_sample(self, sample_id: str) -> bool:
        """Remove symlink from library/."""
        target = self.library_dir / sample_id

        if target.is_symlink():
            target.unlink()
            return True
        return False

    def _file_already_copied(self, source: Path, target_dir: Path) -> bool:
        """Check if file already exists in target (by name and size)."""
        target = target_dir / source.name
        if not target.exists():
            return False
        try:
            return target.stat().st_size == source.stat().st_size
        except OSError:
            return False

    def _get_unique_filename(self, target_dir: Path, filename: str) -> str:
        """Generate unique filename if collision exists."""
        target = target_dir / filename
        if not target.exists():
            return filename

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 2
        while (target_dir / f"{stem}_{counter}{suffix}").exists():
            counter += 1
        return f"{stem}_{counter}{suffix}"

    def _copy_file_sync(
        self,
        source: Path,
        target_dir: Path,
        max_size_bytes: int = 0,
    ) -> tuple[bool, str]:
        """Synchronous file copy. Returns (success, status)."""
        if max_size_bytes > 0:
            try:
                if source.stat().st_size > max_size_bytes:
                    return True, "too_large"
            except OSError:
                pass

        if self._file_already_copied(source, target_dir):
            return True, "skipped"

        filename = self._get_unique_filename(target_dir, source.name)
        target = target_dir / filename

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            return True, "copied"
        except Exception:
            return False, "error"

    async def _copy_file_async(
        self,
        source: Path,
        target_dir: Path,
        semaphore: asyncio.Semaphore,
        stats: _CopyStats,
        max_size_bytes: int = 0,
    ) -> bool:
        """Async wrapper for file copy with concurrency control."""
        async with semaphore:
            success, status = await asyncio.to_thread(
                self._copy_file_sync, source, target_dir, max_size_bytes
            )

            if status == "too_large":
                await stats.add_too_large()
            elif status == "skipped":
                await stats.add_skipped()
            elif status == "copied":
                await stats.add_copied()
            else:
                await stats.add_error()

            return success

    async def enable_pack_async(
        self,
        pack_name: str,
        max_size_mb: int = 10,
        workers: int = 16,
    ) -> EnableResult:
        """Enable a pack (copy from source and create symlinks).

        Args:
            pack_name: Name of pack to enable
            max_size_mb: Skip files larger than this (0 = no limit)
            workers: Number of parallel copy workers

        Returns:
            EnableResult with copy stats and enabled sample IDs

        Raises:
            PackNotFoundError: If pack doesn't exist
        """
        self._check_source()

        pack_dir = self.source_dir / pack_name
        if not pack_dir.exists():
            raise PackNotFoundError(pack_name, self.source_dir)

        files = scan_pack_files(self.source_dir, pack_name)
        samples = group_files_into_samples(pack_name, files)
        max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb > 0 else 0

        # Build copy tasks
        copy_tasks: list[tuple[Path, Path]] = []
        for sample_id, sample_data in samples.items():
            target_dir = self.samples_dir / sample_id
            # Get files for this sample from the grouped data
            for f in files:
                # Check if file belongs to this sample
                from .scanner import detect_category, detect_bpm, detect_is_loop, generate_sample_id, abbreviate_pack_name

                pack_abbr = abbreviate_pack_name(pack_name)
                file_category, _ = detect_category(str(f["path"]))
                file_bpm = detect_bpm(str(f["path"]))
                file_is_loop = detect_is_loop(str(f["path"]))
                file_sample_id = generate_sample_id(pack_abbr, file_category, file_bpm, file_is_loop)

                if file_sample_id == sample_id:
                    copy_tasks.append((f["path"], target_dir))

        # Copy files in parallel
        stats = _CopyStats()
        if copy_tasks:
            semaphore = asyncio.Semaphore(workers)
            tasks = [
                self._copy_file_async(src, tgt, semaphore, stats, max_size_bytes)
                for src, tgt in copy_tasks
            ]
            await asyncio.gather(*tasks)

        # Enable (symlink) all samples
        enabled = 0
        sample_ids = []
        for sample_id in samples.keys():
            if self._enable_sample(sample_id):
                enabled += 1
                sample_ids.append(sample_id)

        return EnableResult(
            pack_name=pack_name,
            copy_stats=stats.to_dict(),
            samples_enabled=enabled,
            sample_ids=sample_ids,
        )

    def enable_pack(
        self,
        pack_name: str,
        max_size_mb: int = 10,
        workers: int = 16,
    ) -> EnableResult:
        """Enable a pack (sync wrapper for async operation)."""
        return asyncio.run(self.enable_pack_async(pack_name, max_size_mb, workers))

    def disable_pack(self, pack_name: str) -> int:
        """Disable a pack (remove symlinks, keep cache).

        Args:
            pack_name: Name of pack to disable

        Returns:
            Number of samples disabled
        """
        self._check_source()

        pack_dir = self.source_dir / pack_name
        if not pack_dir.exists():
            raise PackNotFoundError(pack_name, self.source_dir)

        files = scan_pack_files(self.source_dir, pack_name)
        samples = group_files_into_samples(pack_name, files)

        disabled = 0
        for sample_id in samples.keys():
            if self._disable_sample(sample_id):
                disabled += 1

        return disabled

    def purge_pack(self, pack_name: str) -> bool:
        """Remove pack from local cache entirely.

        Args:
            pack_name: Name of pack to purge

        Returns:
            True if any files were removed
        """
        self._check_source()

        pack_dir = self.source_dir / pack_name
        if not pack_dir.exists():
            raise PackNotFoundError(pack_name, self.source_dir)

        files = scan_pack_files(self.source_dir, pack_name)
        samples = group_files_into_samples(pack_name, files)

        removed_any = False
        for sample_id in samples.keys():
            # Disable first
            self._disable_sample(sample_id)

            # Remove from cache
            cache_dir = self.samples_dir / sample_id
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                removed_any = True

        return removed_any

    def list_enabled_samples(self) -> list[SampleInfo]:
        """List all enabled sample IDs with their info.

        Returns:
            List of SampleInfo for all enabled samples
        """
        enabled_ids = self._get_enabled_sample_ids()
        result = []

        for sample_id in sorted(enabled_ids):
            sample_dir = self.library_dir / sample_id

            # Count audio files
            file_count = 0
            if sample_dir.exists():
                for f in sample_dir.iterdir():
                    if f.suffix.lower() in AUDIO_EXTENSIONS:
                        file_count += 1

            # Parse sample ID to extract info
            # Format: {pack}[_lp]_{category}[_{bpm}]
            parts = sample_id.split("_")
            is_loop = "lp" in parts
            bpm = None
            category = "misc"

            # Find BPM (last numeric part)
            for part in reversed(parts):
                if part.isdigit() and 60 <= int(part) <= 200:
                    bpm = int(part)
                    break

            # Find category (common ones)
            categories = {
                "bd", "sn", "cp", "hh", "ch", "oh", "tom", "perc",
                "bass", "synth", "lead", "pad", "vox", "fx", "loop",
            }
            for part in parts:
                if part in categories:
                    category = part
                    break

            result.append(
                SampleInfo(
                    id=sample_id,
                    category=category,
                    category_type="unknown",  # Would need source scan to determine
                    bpm=bpm,
                    is_loop=is_loop,
                    file_count=file_count,
                    pack_name="",  # Would need source scan to determine
                    enabled=True,
                )
            )

        return result

    # SampleLookup protocol implementation
    def get_samples_by_type(
        self,
        instrument_type: str,
        bpm: Optional[float] = None,
        is_loop: Optional[bool] = None,
        limit: int = 10,
    ) -> list[str]:
        """Get sample IDs matching criteria (implements SampleLookup protocol).

        Args:
            instrument_type: Category to match (bd, sn, hh, etc.)
            bpm: Optional BPM to filter by
            is_loop: Optional filter for loops vs one-shots
            limit: Maximum results

        Returns:
            List of sample IDs
        """
        enabled = self.list_enabled_samples()
        matches = []

        # Map common instrument type names to categories
        type_mapping = {
            "kick": ["bd", "bd808", "bd909"],
            "snare": ["sn", "sn808", "sn909"],
            "clap": ["cp"],
            "hihat": ["hh", "ch", "oh"],
            "hat": ["hh", "ch", "oh"],
            "tom": ["tom", "htom", "mtom", "ltom"],
            "perc": ["perc", "conga", "bongo", "shaker", "rim"],
            "bass": ["bass", "sub", "bass808"],
            "synth": ["synth", "lead", "pad", "chord", "stab"],
            "vocal": ["vox", "speech", "chant"],
            "fx": ["fx", "riser", "sweep", "impact"],
        }

        # Get categories to match
        categories = type_mapping.get(instrument_type.lower(), [instrument_type.lower()])

        for sample in enabled:
            # Check category match
            if sample.get("category") not in categories:
                continue

            # Check BPM match (with tolerance)
            if bpm is not None and sample.get("bpm") is not None:
                if abs(sample["bpm"] - bpm) > 10:
                    continue

            # Check loop/one-shot match
            if is_loop is not None and sample.get("is_loop") != is_loop:
                continue

            matches.append(sample["id"])

            if len(matches) >= limit:
                break

        return matches
