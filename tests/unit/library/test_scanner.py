"""Tests for library scanner module."""

import pytest
from pathlib import Path

from audiomancer.library.scanner import (
    detect_category,
    detect_bpm,
    detect_is_loop,
    abbreviate_pack_name,
    generate_sample_id,
    group_files_into_samples,
)


class TestDetectCategory:
    """Tests for detect_category function.

    Note: Category patterns use word boundaries (\\b), so patterns like
    'kick_01' won't match because underscore is a word character.
    Use spaces or hyphens for word separation in sample names.
    """

    def test_detect_kick_category(self):
        """Detect kick/bass drum samples."""
        assert detect_category("kick 01.wav") == ("bd", "drum")
        assert detect_category("bd-hard.wav") == ("bd", "drum")
        assert detect_category("bassdrum soft.wav") == ("bd", "drum")

    def test_detect_snare_category(self):
        """Detect snare samples."""
        assert detect_category("snare 01.wav") == ("sn", "drum")
        assert detect_category("sd-tight.wav") == ("sn", "drum")

    def test_detect_clap_category(self):
        """Detect clap samples."""
        assert detect_category("clap 01.wav") == ("cp", "drum")
        assert detect_category("handclap.wav") == ("cp", "drum")

    def test_detect_hihat_category(self):
        """Detect hi-hat samples."""
        assert detect_category("hihat closed.wav") == ("hh", "drum")
        assert detect_category("hh-open.wav") == ("hh", "drum")
        assert detect_category("hat 01.wav") == ("hh", "drum")

    def test_detect_open_hat_category(self):
        """Detect open hi-hat samples."""
        assert detect_category("open hat.wav") == ("oh", "drum")
        assert detect_category("oh-01.wav") == ("oh", "drum")

    def test_detect_cymbal_category(self):
        """Detect cymbal samples."""
        assert detect_category("crash 01.wav") == ("crash", "drum")
        assert detect_category("ride bell.wav") == ("ride", "drum")
        assert detect_category("cymbal swell.wav") == ("cym", "drum")

    def test_detect_tom_category(self):
        """Detect tom samples."""
        assert detect_category("tom low.wav") == ("tom", "drum")
        assert detect_category("floor tom.wav") == ("tom", "drum")

    def test_detect_percussion_category(self):
        """Detect percussion samples."""
        assert detect_category("perc 01.wav") == ("perc", "perc")
        assert detect_category("shaker.wav") == ("shaker", "perc")
        assert detect_category("conga hit.wav") == ("conga", "perc")
        assert detect_category("bongo low.wav") == ("bongo", "perc")
        assert detect_category("tambourine.wav") == ("tamb", "perc")

    def test_detect_bass_category(self):
        """Detect bass samples."""
        assert detect_category("bass synth C2.wav") == ("bass", "bass")
        assert detect_category("subbass.wav") == ("sub", "bass")

    def test_detect_synth_category(self):
        """Detect synth samples."""
        assert detect_category("synth pad.wav") == ("synth", "melodic")
        assert detect_category("lead saw.wav") == ("lead", "melodic")
        assert detect_category("pad ambient.wav") == ("pad", "melodic")
        assert detect_category("arp sequence.wav") == ("arp", "melodic")

    def test_detect_fx_category(self):
        """Detect FX samples."""
        assert detect_category("fx sample.wav") == ("fx", "fx")
        assert detect_category("impact hit.wav") == ("impact", "fx")
        assert detect_category("riser 01.wav") == ("riser", "fx")

    def test_detect_vocal_category(self):
        """Detect vocal samples."""
        assert detect_category("vocal chop.wav") == ("vox", "vocal")
        assert detect_category("vox 01.wav") == ("vox", "vocal")

    def test_detect_loop_category(self):
        """Detect loop samples."""
        assert detect_category("drum loop 128.wav") == ("dloop", "loop")
        assert detect_category("top loop.wav") == ("tloop", "loop")
        assert detect_category("loop 128.wav") == ("loop", "loop")

    def test_unknown_category(self):
        """Unknown files return misc category."""
        assert detect_category("random_file.wav") == ("misc", "misc")
        assert detect_category("untitled.wav") == ("misc", "misc")


class TestDetectBPM:
    """Tests for detect_bpm function."""

    def test_detect_bpm_from_filename(self):
        """Detect BPM from filename patterns."""
        assert detect_bpm("drum loop 128bpm.wav") == 128
        assert detect_bpm("bass 140 bpm.wav") == 140
        assert detect_bpm("synth_120_.wav") == 120  # Uses _N_ pattern
        assert detect_bpm("loop at 95bpm.wav") == 95

    def test_detect_bpm_range(self):
        """Only detect BPM in valid range (60-200)."""
        assert detect_bpm("sample 50bpm.wav") is None  # Too slow
        assert detect_bpm("sample 250bpm.wav") is None  # Too fast
        assert detect_bpm("sample 60bpm.wav") == 60
        assert detect_bpm("sample 200bpm.wav") == 200

    def test_no_bpm_in_filename(self):
        """Return None when no BPM in filename."""
        assert detect_bpm("kick 01.wav") is None
        assert detect_bpm("snare hard.wav") is None


class TestDetectIsLoop:
    """Tests for detect_is_loop function."""

    def test_detect_loop(self):
        """Detect loop samples."""
        assert detect_is_loop("drum loop.wav") is True
        assert detect_is_loop("top loop 128.wav") is True
        assert detect_is_loop("perc loop.wav") is True

    def test_detect_oneshot(self):
        """Detect one-shot samples."""
        assert detect_is_loop("kick oneshot.wav") is False
        assert detect_is_loop("snare one shot.wav") is False
        assert detect_is_loop("hit 01.wav") is False

    def test_unknown_default_false(self):
        """Unknown files default to False (one-shot)."""
        assert detect_is_loop("synth chord.wav") is False
        assert detect_is_loop("random.wav") is False


class TestAbbreviatePackName:
    """Tests for abbreviate_pack_name function."""

    def test_simple_abbreviation(self):
        """Create simple abbreviation from pack name."""
        assert abbreviate_pack_name("808 Drum Kit") == "808dk"
        # "vinyl house" -> "vhouse" -> "vhse" (house->hse applies to vhouse)
        assert abbreviate_pack_name("Vinyl House") == "vhse"
        # Long names get truncated to first 2 chars of each word
        assert abbreviate_pack_name("Deep Tech Minimal") == "detemi"

    def test_lowercase_output(self):
        """Output is always lowercase."""
        result = abbreviate_pack_name("UPPERCASE PACK")
        assert result == result.lower()

    def test_removes_special_chars(self):
        """Remove special characters from abbreviation."""
        # Parentheses and dots removed, result is "packvol1"
        assert abbreviate_pack_name("Pack (Vol. 1)") == "packvol1"
        # "sample pack" abbreviation removes it, leaving just "v2"
        assert abbreviate_pack_name("Sample-Pack_v2") == "v2"

    def test_consistent_length(self):
        """Abbreviations have reasonable length."""
        short = abbreviate_pack_name("Hi")
        long = abbreviate_pack_name("Very Long Pack Name With Many Words")
        assert len(short) >= 2
        assert len(long) <= 12


class TestGenerateSampleId:
    """Tests for generate_sample_id function.

    Function signature: generate_sample_id(pack_abbr, category, bpm, is_loop)
    Format: {pack}[_lp]_{category}[_{bpm}]
    """

    def test_basic_id_generation(self):
        """Generate basic sample ID from abbreviated pack and category."""
        # is_loop=False, no BPM
        sample_id = generate_sample_id("808dk", "bd", None, False)
        assert sample_id == "808dk_bd"

    def test_id_with_loop(self):
        """Include _lp marker for loops."""
        sample_id = generate_sample_id("techse", "hh", None, True)
        assert sample_id == "techse_lp_hh"

    def test_id_with_bpm(self):
        """Include BPM in ID when provided."""
        sample_id = generate_sample_id("techse", "lp", 125, True)
        assert sample_id == "techse_lp_lp_125"

    def test_id_with_bpm_no_loop(self):
        """BPM without loop marker."""
        sample_id = generate_sample_id("808dk", "bd", 128, False)
        assert sample_id == "808dk_bd_128"

    def test_unique_ids(self):
        """Different inputs produce different IDs."""
        id1 = generate_sample_id("packa", "bd", None, False)
        id2 = generate_sample_id("packb", "bd", None, False)
        id3 = generate_sample_id("packa", "sn", None, False)
        assert id1 != id2
        assert id1 != id3


class TestGroupFilesIntoSamples:
    """Tests for group_files_into_samples function.

    The function expects file info dicts (from scan_pack_files) with keys:
    path, category, cat_type, bpm, is_loop, size

    Returns: dict mapping sample_id to SampleInfo
    """

    def _make_file_info(self, path: str, category: str, cat_type: str,
                        bpm: int | None = None, is_loop: bool = False) -> dict:
        """Create a file info dict like scan_pack_files would."""
        return {
            "path": Path(path),
            "category": category,
            "cat_type": cat_type,
            "bpm": bpm,
            "is_loop": is_loop,
            "size": 1000,
        }

    def test_group_by_category(self):
        """Group files by detected category."""
        files = [
            self._make_file_info("kick 01.wav", "bd", "drum"),
            self._make_file_info("kick 02.wav", "bd", "drum"),
            self._make_file_info("snare 01.wav", "sn", "drum"),
        ]
        result = group_files_into_samples("Test Pack", files)

        # Returns dict mapping sample_id to SampleInfo
        assert isinstance(result, dict)
        # Should have entries for bd and sn categories
        categories = {info["category"] for info in result.values()}
        assert "bd" in categories
        assert "sn" in categories

    def test_multiple_files_same_category(self):
        """Multiple files of same category grouped together."""
        files = [
            self._make_file_info("kick soft.wav", "bd", "drum"),
            self._make_file_info("kick hard.wav", "bd", "drum"),
            self._make_file_info("kick medium.wav", "bd", "drum"),
        ]
        result = group_files_into_samples("Kicks", files)

        # All kicks should be in one group with file_count=3
        assert len(result) == 1
        sample_info = list(result.values())[0]
        assert sample_info["category"] == "bd"
        assert sample_info["file_count"] == 3

    def test_sample_info_structure(self):
        """Returned samples have correct SampleInfo structure."""
        files = [self._make_file_info("kick 01.wav", "bd", "drum")]
        result = group_files_into_samples("Pack", files)

        assert len(result) == 1
        sample_id, sample_info = next(iter(result.items()))
        assert "id" in sample_info
        assert "category" in sample_info
        assert "category_type" in sample_info
        assert "pack_name" in sample_info
        assert "file_count" in sample_info
        assert sample_info["id"] == sample_id

    def test_empty_files_list(self):
        """Empty file list returns empty dict."""
        result = group_files_into_samples("Empty Pack", [])
        assert result == {}

    def test_files_grouped_by_category_bpm_loop(self):
        """Files with same category but different BPM/loop get separate groups."""
        files = [
            self._make_file_info("hh 01.wav", "hh", "drum", bpm=None, is_loop=False),
            self._make_file_info("hh loop 125.wav", "hh", "drum", bpm=125, is_loop=True),
        ]
        result = group_files_into_samples("Test", files)

        # Should have 2 separate groups (different bpm/is_loop)
        assert len(result) == 2
