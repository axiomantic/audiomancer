"""Sample pack scanning and categorization.

Ported from library_manager.py with improvements for audiomancer integration.
"""

import os
import re
from collections import defaultdict
from pathlib import Path

from .schema import SampleInfo

# Audio file extensions to include
AUDIO_EXTENSIONS = {".wav", ".aiff", ".aif", ".mp3", ".flac", ".ogg"}

# BPM detection patterns
BPM_PATTERNS = [
    r"(\d{2,3})\s*bpm",
    r"_(\d{2,3})_",
    r"-(\d{2,3})-",
    r"@(\d{2,3})",
    r"\[(\d{2,3})\]",
    r"^(\d{2,3})[\s_-]",
]

# Loop detection patterns
LOOP_PATTERNS = [
    r"\bloop\b",
    r"\blp\b",
    r"\bbeat\b",
    r"\bgroove\b",
    r"\bpattern\b",
    r"\bfull\b",
    r"\bbreak\b",
    r"\bbreakbeat\b",
    r"\bdrumloop\b",
    r"\b\d+\s*bar\b",
]

# One-shot detection patterns (takes precedence over loop)
ONESHOT_PATTERNS = [
    r"\bone\s*shot\b",
    r"\boneshot\b",
    r"\bshot\b",
    r"\bhit\b",
    r"\bsingle\b",
]

# Category detection patterns: (regex, category_id, category_type)
CATEGORY_PATTERNS = [
    # Kicks
    (r"\b(kick|bd|bassdrum|bass.?drum)\b", "bd", "drum"),
    (r"\b808.?bd\b", "bd808", "drum"),
    (r"\b909.?bd\b", "bd909", "drum"),
    (r"\bkck\b", "bd", "drum"),
    # Snares
    (r"\b(snare|snr|sd)\b", "sn", "drum"),
    (r"\b808.?sd\b", "sn808", "drum"),
    (r"\b909.?sd\b", "sn909", "drum"),
    # Claps
    (r"\b(clap|clp|cp)\b", "cp", "drum"),
    (r"\bhandclap\b", "cp", "drum"),
    # Hi-hats
    (r"\b(closed?.?hat|ch|closed?.?hh)\b", "ch", "drum"),
    (r"\b(open.?hat|oh|open.?hh)\b", "oh", "drum"),
    (r"\b(hi.?hat|hh|hihat|hat)\b", "hh", "drum"),
    # Cymbals
    (r"\b(crash|crsh)\b", "crash", "drum"),
    (r"\b(ride|rd)\b", "ride", "drum"),
    (r"\b(cymbal|cym)\b", "cym", "drum"),
    # Toms
    (r"\b(hi.?tom|htom|high.?tom)\b", "htom", "drum"),
    (r"\b(lo.?tom|ltom|low.?tom)\b", "ltom", "drum"),
    (r"\b(mid.?tom|mtom)\b", "mtom", "drum"),
    (r"\b(tom|tm)\b", "tom", "drum"),
    # Percussion
    (r"\b(conga|cng)\b", "conga", "perc"),
    (r"\b(bongo|bng)\b", "bongo", "perc"),
    (r"\b(shaker|shkr)\b", "shaker", "perc"),
    (r"\b(tamb|tambourine)\b", "tamb", "perc"),
    (r"\b(rim|rimshot)\b", "rim", "perc"),
    (r"\b(cowbell|cbell)\b", "cbell", "perc"),
    (r"\b(clave)\b", "clave", "perc"),
    (r"\b(tabla)\b", "tabla", "perc"),
    (r"\b(triangle|tri)\b", "tri", "perc"),
    (r"\b(perc|percussion)\b", "perc", "perc"),
    # Bass
    (r"\b(sub.?bass|subbass)\b", "sub", "bass"),
    (r"\b808.?bass\b", "bass808", "bass"),
    (r"\b(bass)\b", "bass", "bass"),
    # Synth/Melodic
    (r"\b(synth|syn)\b", "synth", "melodic"),
    (r"\b(lead)\b", "lead", "melodic"),
    (r"\b(pad)\b", "pad", "melodic"),
    (r"\b(chord|chrd)\b", "chord", "melodic"),
    (r"\b(stab)\b", "stab", "melodic"),
    (r"\b(arp)\b", "arp", "melodic"),
    (r"\b(pluck)\b", "pluck", "melodic"),
    (r"\b(piano)\b", "piano", "melodic"),
    (r"\b(rhodes|wurli)\b", "keys", "melodic"),
    (r"\b(organ)\b", "organ", "melodic"),
    (r"\b(string)\b", "string", "melodic"),
    (r"\b(brass)\b", "brass", "melodic"),
    (r"\b(keys)\b", "keys", "melodic"),
    # Vocals
    (r"\b(vocal|vox|voice)\b", "vox", "vocal"),
    (r"\b(speech)\b", "speech", "vocal"),
    (r"\b(chant)\b", "chant", "vocal"),
    (r"\b(adlib)\b", "adlib", "vocal"),
    # FX
    (r"\b(riser)\b", "riser", "fx"),
    (r"\b(sweep)\b", "sweep", "fx"),
    (r"\b(noise)\b", "noise", "fx"),
    (r"\b(impact)\b", "impact", "fx"),
    (r"\b(whoosh)\b", "whoosh", "fx"),
    (r"\b(downlifter)\b", "down", "fx"),
    (r"\b(uplifter)\b", "up", "fx"),
    (r"\b(transition)\b", "trans", "fx"),
    (r"\b(fx|effect|sfx)\b", "fx", "fx"),
    # Loops
    (r"\b(drum.?loop)\b", "dloop", "loop"),
    (r"\b(top.?loop)\b", "tloop", "loop"),
    (r"\b(perc.?loop)\b", "ploop", "loop"),
    (r"\b(loop|lp)\b", "loop", "loop"),
    (r"\b(break|brk)\b", "break", "loop"),
]

# Pack name abbreviations for shorter sample IDs
PACK_ABBREVIATIONS = {
    "abstract state": "abst",
    "techno expansion": "tex",
    "sample pack": "",
    "drum kit": "dk",
    "drum samples": "ds",
    "loopcloud": "lc",
    "zenhiser": "zen",
    "bandlab": "",
    "artis audio": "artis",
    "complete production": "cp",
    "strangeflow": "sf",
    "ultimate": "ult",
    "vintage": "vint",
    "hy2rogen": "hy2",
    "tribal": "trib",
    "vinyl house": "vhouse",
    "footwork": "ftw",
    "juke": "juke",
    "lo-fi": "lofi",
    "hip-hop": "hiphop",
    "hip hop": "hiphop",
    "acid": "acid",
    "techno": "tech",
    "house": "hse",
    "berlin": "bln",
    "bassadelic": "bass",
    "drum collection": "dc",
    "one shots": "",
    "oneshots": "",
    "samples": "",
}


def detect_category(text: str) -> tuple[str, str]:
    """Detect sample category from text (filename/path).

    Returns:
        Tuple of (category_id, category_type)
    """
    text_lower = text.lower()
    for pattern, category, cat_type in CATEGORY_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return category, cat_type
    return "misc", "misc"


def detect_bpm(text: str) -> int | None:
    """Detect BPM from text (filename/path).

    Returns:
        BPM value if detected and in valid range (60-200), None otherwise
    """
    text_lower = text.lower()
    for pattern in BPM_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            bpm = int(match.group(1))
            if 60 <= bpm <= 200:
                return bpm
    return None


def detect_is_loop(text: str) -> bool:
    """Detect if sample is a loop vs one-shot.

    Returns:
        True if detected as loop, False otherwise
    """
    text_lower = text.lower()
    # One-shot patterns take precedence
    for pattern in ONESHOT_PATTERNS:
        if re.search(pattern, text_lower):
            return False
    # Check for loop patterns
    for pattern in LOOP_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def abbreviate_pack_name(pack_name: str) -> str:
    """Generate short abbreviation for pack name.

    Args:
        pack_name: Original pack folder name

    Returns:
        Short abbreviation (max 8 chars) for use in sample IDs
    """
    name = pack_name.lower()
    # Remove common suffixes
    name = re.sub(r"\s*\(sample pack\)\s*", "", name)
    name = re.sub(r"\s*sample\s*pack\s*", "", name)
    name = re.sub(r"\s*-\s*bandlab\s*$", "", name)
    name = re.sub(r"\s+\([a-f0-9]+\)\s*$", "", name)
    name = re.sub(r"[_\-]+", " ", name)

    # Apply abbreviations
    for full, abbr in PACK_ABBREVIATIONS.items():
        name = name.replace(full, abbr)

    # Clean up
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", "", name)

    # Truncate if still too long
    if len(name) > 8:
        words = re.findall(r"[a-z]+", pack_name.lower())
        if words:
            name = "".join(w[:2] for w in words[:4])[:8]

    return name or "pack"


def generate_sample_id(
    pack_abbr: str,
    category: str,
    bpm: int | None,
    is_loop: bool,
) -> str:
    """Generate a sample ID from components.

    Format: {pack}[_lp]_{category}[_{bpm}]

    Examples:
        - "808dk_bd" (808 Drum Kit, kick)
        - "absttex_lp_hh_125" (Abstract Techno, loop, hi-hat, 125 BPM)
    """
    parts = [pack_abbr] if pack_abbr else []
    if is_loop:
        parts.append("lp")
    parts.append(category)
    if bpm:
        parts.append(str(bpm))

    base_id = "_".join(parts)
    base_id = re.sub(r"[^a-z0-9_]", "", base_id.lower())
    base_id = re.sub(r"_+", "_", base_id).strip("_")

    return base_id if len(base_id) >= 2 else f"smp_{base_id}"


def scan_source_packs(source_dir: Path) -> list[str]:
    """Get list of top-level pack folders from source directory.

    Args:
        source_dir: Path to source directory (e.g., Google Drive samples folder)

    Returns:
        Sorted list of pack folder names
    """
    if not source_dir.exists():
        return []

    return sorted(
        d.name
        for d in source_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def scan_pack_files(source_dir: Path, pack_name: str) -> list[dict]:
    """Scan a pack and categorize all audio files.

    Args:
        source_dir: Path to source directory
        pack_name: Name of pack folder to scan

    Returns:
        List of file info dicts with path, category, bpm, is_loop, size
    """
    pack_dir = source_dir / pack_name
    files = []

    for root, _, filenames in os.walk(pack_dir):
        for f in filenames:
            if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                file_path = Path(root) / f
                rel_path = file_path.relative_to(source_dir)
                search_text = str(rel_path)

                category, cat_type = detect_category(search_text)
                bpm = detect_bpm(search_text)
                is_loop = detect_is_loop(search_text)

                try:
                    size = file_path.stat().st_size
                except OSError:
                    size = 0

                files.append(
                    {
                        "path": file_path,
                        "category": category,
                        "cat_type": cat_type,
                        "bpm": bpm,
                        "is_loop": is_loop,
                        "size": size,
                    }
                )

    return files


def group_files_into_samples(
    pack_name: str,
    files: list[dict],
) -> dict[str, SampleInfo]:
    """Group files into sample folders by category.

    Args:
        pack_name: Pack folder name
        files: List of file info dicts from scan_pack_files

    Returns:
        Dict mapping sample_id to SampleInfo
    """
    pack_abbr = abbreviate_pack_name(pack_name)
    groups: dict[tuple, list[dict]] = defaultdict(list)

    for f in files:
        key = (f["category"], f["bpm"], f["is_loop"])
        groups[key].append(f)

    result: dict[str, SampleInfo] = {}
    for (category, bpm, is_loop), group_files in groups.items():
        sample_id = generate_sample_id(pack_abbr, category, bpm, is_loop)
        result[sample_id] = SampleInfo(
            id=sample_id,
            category=category,
            category_type=group_files[0]["cat_type"] if group_files else "misc",
            bpm=bpm,
            is_loop=is_loop,
            file_count=len(group_files),
            pack_name=pack_name,
            enabled=False,
        )

    return result
