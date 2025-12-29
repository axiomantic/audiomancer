"""Tests for pattern generation."""

import pytest
from unittest.mock import patch

from audiomancer.generators.patterns import (
    Pattern,
    generate_drums,
    generate_melody,
    generate_bass,
    humanize,
    _parse_key,
    _generate_pattern_id,
    MAGENTA_AVAILABLE,
)
from audiomancer.errors import GenerationError, ModelLoadError, InferenceTimeoutError


class TestPatternClass:
    """Tests for Pattern dataclass."""

    def test_pattern_creation(self):
        """Test creating a pattern instance."""
        pattern = Pattern(
            pattern_id="ptrn_test123",
            pattern_type="drums",
            midi_data=b"test_midi",
            tidal_code='d1 $ sound "bd ~ sn ~"',
            sc_code="Pbind(...)",
            bpm=120.0,
            bars=4,
        )

        assert pattern.id == "ptrn_test123"
        assert pattern.type == "drums"
        assert pattern.bpm == 120.0
        assert pattern.bars == 4
        assert pattern.parent_ids == []
        assert pattern.generation_method == "generated"

    def test_pattern_with_lineage(self):
        """Test pattern with parent tracking."""
        pattern = Pattern(
            pattern_id="ptrn_child",
            pattern_type="drums",
            midi_data=b"test",
            tidal_code="",
            sc_code="",
            bpm=125.0,
            bars=4,
            parent_ids=["ptrn_parent1", "ptrn_parent2"],
            generation_method="crossover",
        )

        assert pattern.parent_ids == ["ptrn_parent1", "ptrn_parent2"]
        assert pattern.generation_method == "crossover"

    def test_pattern_to_dict(self):
        """Test pattern serialization."""
        pattern = Pattern(
            pattern_id="ptrn_test",
            pattern_type="melody",
            midi_data=b"\x00\x01\x02",
            tidal_code="d1 $ n '0 3 5'",
            sc_code="Pbind(...)",
            bpm=140.0,
            bars=8,
            key="C",
            scale="minor",
        )

        data = pattern.to_dict()

        assert data["id"] == "ptrn_test"
        assert data["type"] == "melody"
        assert data["midi_data"] == "000102"  # hex encoded
        assert data["bpm"] == 140.0
        assert data["key"] == "C"
        assert data["scale"] == "minor"
        assert "created_at" in data


class TestPatternID:
    """Tests for pattern ID generation."""

    def test_generate_pattern_id(self):
        """Test pattern ID format."""
        pattern_id = _generate_pattern_id()

        assert pattern_id.startswith("ptrn_")
        assert len(pattern_id) == 13  # "ptrn_" + 8 hex chars

    def test_unique_ids(self):
        """Test that IDs are unique."""
        ids = [_generate_pattern_id() for _ in range(100)]
        assert len(ids) == len(set(ids))


class TestKeyParsing:
    """Tests for musical key parsing."""

    def test_parse_simple_keys(self):
        """Test parsing simple key names."""
        assert _parse_key("C") == 0
        assert _parse_key("D") == 2
        assert _parse_key("E") == 4
        assert _parse_key("F") == 5
        assert _parse_key("G") == 7
        assert _parse_key("A") == 9
        assert _parse_key("B") == 11

    def test_parse_sharp_keys(self):
        """Test parsing sharp keys."""
        assert _parse_key("C#") == 1
        assert _parse_key("F#") == 6
        assert _parse_key("G#") == 8

    def test_parse_flat_keys(self):
        """Test parsing flat keys."""
        assert _parse_key("Db") == 1
        assert _parse_key("Eb") == 3
        assert _parse_key("Bb") == 10

    def test_parse_minor_keys(self):
        """Test parsing minor key notation."""
        assert _parse_key("Am") == 9
        assert _parse_key("Dminor") == 2
        assert _parse_key("F#m") == 6

    def test_invalid_key(self):
        """Test error on invalid key."""
        with pytest.raises(GenerationError) as exc_info:
            _parse_key("X")

        assert "Invalid key" in str(exc_info.value)
        assert "X" in exc_info.value.details["key"]


@pytest.mark.skipif(not MAGENTA_AVAILABLE, reason="Magenta not installed")
class TestDrumGeneration:
    """Tests for drum pattern generation."""

    def test_generate_basic_drums(self):
        """Test generating a basic drum pattern."""
        pattern = generate_drums(style="house", bpm=125.0, bars=4)

        assert pattern.type == "drums"
        assert pattern.bpm == 125.0
        assert pattern.bars == 4
        assert pattern.generation_method == "generated"
        assert pattern.parent_ids == []
        assert 'd1 $ sound' in pattern.tidal_code
        assert 'Pdef' in pattern.sc_code

    def test_generate_drums_styles(self):
        """Test different drum styles."""
        styles = ["house", "techno", "breakbeat", "trap", "jazz"]

        for style in styles:
            pattern = generate_drums(style=style, bpm=120.0, bars=2)
            assert pattern.type == "drums"
            assert isinstance(pattern.tidal_code, str)
            assert len(pattern.tidal_code) > 0

    def test_generate_drums_with_temperature(self):
        """Test temperature parameter."""
        # Lower temperature should still work
        pattern_low = generate_drums(temperature=0.1)
        assert pattern_low.type == "drums"

        # Higher temperature should still work
        pattern_high = generate_drums(temperature=1.5)
        assert pattern_high.type == "drums"

    def test_generate_drums_timeout(self):
        """Test timeout handling."""
        # Very short timeout should succeed for simple generation
        pattern = generate_drums(timeout=1.0)
        assert pattern.type == "drums"


@pytest.mark.skipif(not MAGENTA_AVAILABLE, reason="Magenta not installed")
class TestMelodyGeneration:
    """Tests for melody pattern generation."""

    def test_generate_basic_melody(self):
        """Test generating a basic melody."""
        pattern = generate_melody(key="C", scale="major", bpm=120.0, bars=4)

        assert pattern.type == "melody"
        assert pattern.bpm == 120.0
        assert pattern.bars == 4
        assert pattern.key == "C"
        assert pattern.scale == "major"
        assert pattern.generation_method == "generated"

    def test_generate_melody_scales(self):
        """Test different scale types."""
        scales = ["major", "minor", "dorian", "mixolydian", "pentatonic"]

        for scale in scales:
            pattern = generate_melody(key="D", scale=scale, bars=2)
            assert pattern.type == "melody"
            assert pattern.scale == scale

    def test_generate_melody_keys(self):
        """Test different keys."""
        keys = ["C", "F#", "Bb", "Am", "Dmajor"]

        for key in keys:
            pattern = generate_melody(key=key, scale="minor", bars=2)
            assert pattern.type == "melody"
            assert pattern.key is not None

    def test_invalid_scale(self):
        """Test error on invalid scale."""
        with pytest.raises(GenerationError) as exc_info:
            generate_melody(key="C", scale="invalid_scale")

        assert "Invalid scale" in str(exc_info.value)

    def test_melody_timeout(self):
        """Test timeout handling."""
        pattern = generate_melody(timeout=1.0)
        assert pattern.type == "melody"


@pytest.mark.skipif(not MAGENTA_AVAILABLE, reason="Magenta not installed")
class TestBassGeneration:
    """Tests for bass pattern generation."""

    def test_generate_basic_bass(self):
        """Test generating a basic bass line."""
        pattern = generate_bass(key="F#", bpm=140.0, bars=8, style="synth")

        assert pattern.type == "bass"
        assert pattern.bpm == 140.0
        assert pattern.bars == 8
        assert pattern.key == "F#"
        assert pattern.scale == "minor"  # Default
        assert pattern.generation_method == "generated"

    def test_generate_bass_styles(self):
        """Test different bass styles."""
        styles = ["synth", "acoustic", "walking", "slap"]

        for style in styles:
            pattern = generate_bass(key="E", style=style, bars=4)
            assert pattern.type == "bass"

    def test_bass_timeout(self):
        """Test timeout handling."""
        pattern = generate_bass(timeout=1.0)
        assert pattern.type == "bass"


@pytest.mark.skipif(not MAGENTA_AVAILABLE, reason="Magenta not installed")
class TestHumanization:
    """Tests for pattern humanization."""

    def test_humanize_pattern(self):
        """Test humanizing a pattern."""
        original = generate_drums(style="techno", bars=4)
        humanized = humanize(original, amount=0.5)

        assert humanized.id != original.id
        assert humanized.type == original.type
        assert humanized.parent_ids == [original.id]
        assert humanized.generation_method == "humanized"
        assert humanized.mutation_amount == 0.5

    def test_humanize_preserves_metadata(self):
        """Test that humanization preserves pattern metadata."""
        original = generate_drums(style="house", bpm=128.0, bars=8)
        humanized = humanize(original, amount=0.3)

        assert humanized.bpm == original.bpm
        assert humanized.bars == original.bars
        assert humanized.type == original.type

    def test_humanize_amount_range(self):
        """Test humanization with different amounts."""
        original = generate_drums()

        # Low humanization
        low = humanize(original, amount=0.1)
        assert low.mutation_amount == 0.1

        # High humanization
        high = humanize(original, amount=0.9)
        assert high.mutation_amount == 0.9


class TestMagentaNotAvailable:
    """Tests for graceful degradation when Magenta is not installed."""

    @patch('audiomancer.generators.patterns.MAGENTA_AVAILABLE', False)
    def test_drum_generation_without_magenta(self):
        """Test that drum generation fails gracefully without Magenta."""
        with pytest.raises(ModelLoadError) as exc_info:
            generate_drums()

        assert "Magenta not available" in str(exc_info.value)
        assert "magenta" in exc_info.value.details["package"]

    @patch('audiomancer.generators.patterns.MAGENTA_AVAILABLE', False)
    def test_melody_generation_without_magenta(self):
        """Test that melody generation fails gracefully without Magenta."""
        with pytest.raises(ModelLoadError) as exc_info:
            generate_melody()

        assert "Magenta not available" in str(exc_info.value)

    @patch('audiomancer.generators.patterns.MAGENTA_AVAILABLE', False)
    def test_bass_generation_without_magenta(self):
        """Test that bass generation fails gracefully without Magenta."""
        with pytest.raises(ModelLoadError) as exc_info:
            generate_bass()

        assert "Magenta not available" in str(exc_info.value)

    @patch('audiomancer.generators.patterns.MAGENTA_AVAILABLE', False)
    def test_humanize_without_magenta(self):
        """Test that humanization fails gracefully without Magenta."""
        # Create a fake pattern
        pattern = Pattern(
            pattern_id="test",
            pattern_type="drums",
            midi_data=b"",
            tidal_code="",
            sc_code="",
            bpm=120.0,
            bars=4,
        )

        with pytest.raises(ModelLoadError):
            humanize(pattern)
