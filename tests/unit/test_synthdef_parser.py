"""Unit tests for SynthDef parser."""

import pytest
from pathlib import Path

from audiomancer.analyzers.synthdef import (
    parse_synthdef,
    categorize_synthdef,
    SynthDefInfo,
    SynthControl,
    _parse_with_regex,
)
from audiomancer.errors import SynthDefError, SubprocessTimeoutError


# Test fixtures paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synths"
SIMPLE_SINE = FIXTURES_DIR / "simple_sine.scd"
TB303 = FIXTURES_DIR / "tb303.scd"


class TestParseSynthDef:
    """Tests for parse_synthdef function."""

    def test_parse_simple_sine(self):
        """Test parsing simple sine wave SynthDef."""
        info = parse_synthdef(SIMPLE_SINE)

        assert info.name == "simple_sine"
        assert info.file_path == str(SIMPLE_SINE.absolute())
        assert len(info.file_hash) == 64  # SHA256 hex
        assert info.num_channels == 2
        assert info.has_gate is True
        assert info.has_envelope is True
        assert "SinOsc" in info.ugens_used
        assert "EnvGen" in info.ugens_used
        assert "Out" in info.ugens_used

        # Check controls
        control_names = {c.name for c in info.controls}
        assert "out" in control_names
        assert "freq" in control_names
        assert "amp" in control_names
        assert "gate" in control_names

        # Check default values
        freq_ctrl = next(c for c in info.controls if c.name == "freq")
        assert freq_ctrl.default_value == 440.0

        amp_ctrl = next(c for c in info.controls if c.name == "amp")
        assert amp_ctrl.default_value == 0.5

        # Should be categorized as lead (has gate and envelope)
        assert info.category in ["lead", "pad"]

    def test_parse_tb303(self):
        """Test parsing TB-303 acid bass SynthDef."""
        info = parse_synthdef(TB303)

        assert info.name == "tb303"
        assert info.file_path == str(TB303.absolute())
        assert info.num_channels == 2
        assert info.has_gate is True
        assert info.has_envelope is True

        # Check for TB-303 characteristic UGens
        assert "Saw" in info.ugens_used
        assert "Pulse" in info.ugens_used
        assert "MoogFF" in info.ugens_used  # Moog filter
        assert "EnvGen" in info.ugens_used
        assert "Lag" in info.ugens_used  # For portamento/slide
        assert "Select" in info.ugens_used  # For wave selection

        # Check TB-303 specific controls
        control_names = {c.name for c in info.controls}
        assert "cutoff" in control_names
        assert "resonance" in control_names
        assert "envmod" in control_names
        assert "decay" in control_names
        assert "accent" in control_names
        assert "slide" in control_names
        assert "wave" in control_names

        # Check default values
        cutoff_ctrl = next(c for c in info.controls if c.name == "cutoff")
        assert cutoff_ctrl.default_value == 1200.0

        resonance_ctrl = next(c for c in info.controls if c.name == "resonance")
        assert resonance_ctrl.default_value == 0.7

        # Should be categorized as bass (has MoogFF filter)
        assert info.category == "bass"

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file raises error."""
        with pytest.raises(SynthDefError) as exc_info:
            parse_synthdef(Path("/nonexistent/path.scd"))

        assert "does not exist" in str(exc_info.value)
        assert exc_info.value.details["error"] == "file not found"

    def test_parse_invalid_extension(self):
        """Test parsing file with wrong extension raises error."""
        with pytest.raises(SynthDefError) as exc_info:
            parse_synthdef(Path("/path/to/file.txt"))

        assert "Invalid file extension" in str(exc_info.value)
        assert exc_info.value.details["error"] == "expected .scd file"

    def test_source_code_is_stored(self):
        """Test that source code is preserved in SynthDefInfo."""
        info = parse_synthdef(SIMPLE_SINE)

        assert "SynthDef" in info.source_code
        assert "simple_sine" in info.source_code
        assert "SinOsc" in info.source_code

    def test_file_hash_consistency(self):
        """Test that file hash is consistent across multiple parses."""
        info1 = parse_synthdef(SIMPLE_SINE)
        info2 = parse_synthdef(SIMPLE_SINE)

        assert info1.file_hash == info2.file_hash


class TestRegexParser:
    """Tests for regex-based fallback parser."""

    def test_regex_parser_simple_sine(self):
        """Test regex parser on simple sine SynthDef."""
        source = SIMPLE_SINE.read_text()
        metadata = _parse_with_regex(SIMPLE_SINE, source)

        assert metadata["name"] == "simple_sine"
        assert metadata["has_gate"] is True
        assert metadata["has_envelope"] is True
        assert "SinOsc" in metadata["ugens"]
        assert "EnvGen" in metadata["ugens"]
        assert metadata["num_channels"] == 2

        # Check controls
        control_names = {c["name"] for c in metadata["controls"]}
        assert "out" in control_names
        assert "freq" in control_names
        assert "amp" in control_names
        assert "gate" in control_names

    def test_regex_parser_tb303(self):
        """Test regex parser on TB-303 SynthDef."""
        source = TB303.read_text()
        metadata = _parse_with_regex(TB303, source)

        assert metadata["name"] == "tb303"
        assert metadata["has_gate"] is True
        assert metadata["has_envelope"] is True

        # Check for key UGens
        ugens = set(metadata["ugens"])
        assert "Saw" in ugens
        assert "Pulse" in ugens
        assert "MoogFF" in ugens
        assert "EnvGen" in ugens

        # Check controls
        control_names = {c["name"] for c in metadata["controls"]}
        assert "cutoff" in control_names
        assert "resonance" in control_names
        assert "envmod" in control_names

    def test_regex_parser_no_synthdef(self):
        """Test regex parser fails on invalid source."""
        invalid_source = "// This is not a SynthDef\nvar x = 10;"

        with pytest.raises(SynthDefError) as exc_info:
            _parse_with_regex(Path("/fake/path.scd"), invalid_source)

        assert "Cannot find SynthDef name" in str(exc_info.value)


class TestCategorization:
    """Tests for SynthDef categorization logic."""

    def test_categorize_bass(self):
        """Test bass categorization (has MoogFF or RLPF)."""
        info = SynthDefInfo(
            name="test_bass",
            file_path="/test.scd",
            file_hash="abc",
            num_channels=2,
            has_gate=True,
            has_envelope=True,
            ugens_used=["Saw", "MoogFF", "EnvGen", "Out"],
            controls=[],
            source_code="SynthDef(...)",
        )

        category = categorize_synthdef(info)
        assert category == "bass"

    def test_categorize_lead(self):
        """Test lead categorization (has gate + envelope, no filter)."""
        info = SynthDefInfo(
            name="test_lead",
            file_path="/test.scd",
            file_hash="abc",
            num_channels=2,
            has_gate=True,
            has_envelope=True,
            ugens_used=["Saw", "EnvGen", "Out"],
            controls=[],
            source_code="SynthDef(\\test, { EnvGen.kr(Env.perc(0.01, 0.2)) })",
        )

        category = categorize_synthdef(info)
        assert category == "lead"

    def test_categorize_pad(self):
        """Test pad categorization (has gate + envelope with asr)."""
        info = SynthDefInfo(
            name="test_pad",
            file_path="/test.scd",
            file_hash="abc",
            num_channels=2,
            has_gate=True,
            has_envelope=True,
            ugens_used=["Saw", "EnvGen", "Out"],
            controls=[],
            source_code="SynthDef(\\test, { EnvGen.kr(Env.asr(0.1, 1, 0.5)) })",
        )

        category = categorize_synthdef(info)
        assert category == "pad"

    def test_categorize_drum(self):
        """Test drum categorization (no gate)."""
        info = SynthDefInfo(
            name="test_drum",
            file_path="/test.scd",
            file_hash="abc",
            num_channels=2,
            has_gate=False,
            has_envelope=True,
            ugens_used=["SinOsc", "EnvGen", "Out"],
            controls=[],
            source_code="SynthDef(...)",
        )

        category = categorize_synthdef(info)
        assert category == "drum"

    def test_categorize_fx(self):
        """Test FX categorization (has noise or effects)."""
        info = SynthDefInfo(
            name="test_fx",
            file_path="/test.scd",
            file_hash="abc",
            num_channels=2,
            has_gate=True,
            has_envelope=False,
            ugens_used=["WhiteNoise", "FreeVerb", "Out"],
            controls=[],
            source_code="SynthDef(...)",
        )

        category = categorize_synthdef(info)
        assert category == "fx"


class TestSynthControl:
    """Tests for SynthControl dataclass."""

    def test_synth_control_creation(self):
        """Test creating SynthControl with required fields."""
        ctrl = SynthControl(name="freq", default_value=440.0)

        assert ctrl.name == "freq"
        assert ctrl.default_value == 440.0
        assert ctrl.spec is None
        assert ctrl.description is None

    def test_synth_control_with_spec(self):
        """Test creating SynthControl with spec."""
        ctrl = SynthControl(
            name="freq",
            default_value=440.0,
            spec="\\freq.asSpec",
            description="Frequency in Hz"
        )

        assert ctrl.name == "freq"
        assert ctrl.default_value == 440.0
        assert ctrl.spec == "\\freq.asSpec"
        assert ctrl.description == "Frequency in Hz"


class TestSynthDefInfo:
    """Tests for SynthDefInfo dataclass."""

    def test_synthdef_info_creation(self):
        """Test creating SynthDefInfo with required fields."""
        info = SynthDefInfo(
            name="test_synth",
            file_path="/path/to/test.scd",
            file_hash="abc123",
            num_channels=2,
            has_gate=True,
            has_envelope=True,
            ugens_used=["SinOsc", "EnvGen", "Out"],
            controls=[SynthControl("freq", 440.0)],
            source_code="SynthDef(...)",
        )

        assert info.name == "test_synth"
        assert info.file_path == "/path/to/test.scd"
        assert info.file_hash == "abc123"
        assert info.num_channels == 2
        assert info.has_gate is True
        assert info.has_envelope is True
        assert len(info.ugens_used) == 3
        assert len(info.controls) == 1
        assert info.category is None
        assert info.tags == []

    def test_synthdef_info_with_category(self):
        """Test creating SynthDefInfo with category and tags."""
        info = SynthDefInfo(
            name="test_synth",
            file_path="/path/to/test.scd",
            file_hash="abc123",
            num_channels=2,
            has_gate=True,
            has_envelope=True,
            ugens_used=["Saw", "MoogFF"],
            controls=[],
            source_code="SynthDef(...)",
            category="bass",
            tags=["acid", "303"],
        )

        assert info.category == "bass"
        assert "acid" in info.tags
        assert "303" in info.tags
