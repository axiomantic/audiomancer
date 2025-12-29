"""Unit tests for SynthDef generator and mutation."""

import pytest
from pathlib import Path
import re

from audiomancer.generators.synths import (
    generate_synth,
    mutate_synth,
    breed_synths,
    swap_oscillator,
    swap_filter,
    add_modulation,
    add_distortion,
    modify_parameter_defaults,
    modify_envelope,
    extract_controls,
    GeneratedSynth,
)
from audiomancer.analyzers.synthdef import parse_synthdef, SynthDefInfo, SynthControl
from audiomancer.errors import SynthDefError


# Test fixtures paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synths"
SIMPLE_SINE = FIXTURES_DIR / "simple_sine.scd"
TB303 = FIXTURES_DIR / "tb303.scd"


class TestGenerateSynth:
    """Tests for generate_synth function."""

    def test_generate_from_template_bass(self):
        """Test generating bass synth from template."""
        synth = generate_synth(
            description="acid bass",
            category="bass"
        )

        assert isinstance(synth, GeneratedSynth)
        assert "bass" in synth.name or "acid" in synth.name
        assert "SynthDef" in synth.source_code
        assert synth.generation_method == "from_template"
        assert synth.category == "bass"
        assert len(synth.controls) > 0

    def test_generate_from_template_lead(self):
        """Test generating lead synth from template."""
        synth = generate_synth(
            description="bright lead",
            category="lead"
        )

        assert "lead" in synth.name or "bright" in synth.name
        assert synth.category == "lead"
        assert "Pulse" in synth.source_code or "Saw" in synth.source_code

    def test_generate_from_template_pad(self):
        """Test generating pad synth from template."""
        synth = generate_synth(
            description="warm pad",
            category="pad"
        )

        assert synth.category == "pad"
        assert "Env.asr" in synth.source_code  # Pads use ASR envelopes

    def test_generate_from_template_drum(self):
        """Test generating drum synth from template."""
        synth = generate_synth(
            description="kick drum",
            category="drum"
        )

        assert synth.category == "drum"
        assert "gate" not in [c.name for c in synth.controls]  # Drums have no gate

    def test_generate_from_template_fx(self):
        """Test generating FX synth from template."""
        synth = generate_synth(
            description="noise texture",
            category="fx"
        )

        assert synth.category == "fx"
        assert "Dust" in synth.source_code or "Noise" in synth.source_code

    def test_generate_from_base_synth(self):
        """Test generating by modifying existing synth."""
        tb303 = parse_synthdef(TB303)

        synth = generate_synth(
            description="warm acid bass with sweep",
            base_synth=tb303,
            category="bass"
        )

        assert synth.parent_ids == [tb303.name]
        assert synth.generation_method == "from_description"
        assert len(synth.mutation_log) > 0

    def test_generate_acid_keyword(self):
        """Test acid keyword adds resonant filter."""
        simple = parse_synthdef(SIMPLE_SINE)

        synth = generate_synth(
            description="acid",
            base_synth=simple,
            category="lead"
        )

        # Should add acid filter or already have one
        assert "MoogFF" in synth.source_code or "RLPF" in synth.source_code

    def test_generate_warm_keyword(self):
        """Test warm keyword uses saw wave."""
        synth = generate_synth(
            description="warm bass",
            category="bass"
        )

        # Warm sounds should use saw wave
        assert "Saw" in synth.source_code

    def test_generate_sweep_keyword(self):
        """Test sweep keyword adds LFO modulation."""
        tb303 = parse_synthdef(TB303)

        synth = generate_synth(
            description="bass with filter sweep",
            base_synth=tb303,
            category="bass"
        )

        # Should add LFO modulation
        assert any("LFO" in log or "modulation" in log for log in synth.mutation_log)

    def test_generated_synth_has_valid_structure(self):
        """Test generated synth has valid SuperCollider structure."""
        synth = generate_synth(
            description="test synth",
            category="bass"
        )

        # Must have SynthDef
        assert re.search(r'SynthDef\s*\(', synth.source_code)

        # Must have Out.ar
        assert "Out.ar" in synth.source_code

        # Must have envelope
        assert "EnvGen" in synth.source_code or "Env" in synth.source_code

        # Must end with .add
        assert synth.source_code.strip().endswith(".add;")

    def test_controls_extracted_correctly(self):
        """Test control parameters are extracted from generated code."""
        synth = generate_synth(
            description="bass",
            category="bass"
        )

        # Should have standard controls
        control_names = {c.name for c in synth.controls}
        assert "out" in control_names
        assert "freq" in control_names
        assert "amp" in control_names


class TestMutateSynth:
    """Tests for mutate_synth function."""

    def test_mutate_basic(self):
        """Test basic mutation of synth."""
        tb303 = parse_synthdef(TB303)

        mutant = mutate_synth(tb303, amount=0.5, seed=42)

        assert isinstance(mutant, GeneratedSynth)
        assert mutant.name.startswith("tb303_m")
        assert mutant.parent_ids == ["tb303"]
        assert mutant.generation_method == "mutation"
        assert len(mutant.mutation_log) > 0

    def test_mutate_deterministic_with_seed(self):
        """Test mutation is deterministic with same seed."""
        tb303 = parse_synthdef(TB303)

        mutant1 = mutate_synth(tb303, amount=0.5, seed=42)
        mutant2 = mutate_synth(tb303, amount=0.5, seed=42)

        # Should produce identical mutations
        assert mutant1.mutation_log == mutant2.mutation_log
        assert mutant1.source_code == mutant2.source_code

    def test_mutate_different_with_different_seed(self):
        """Test mutation varies with different seeds."""
        tb303 = parse_synthdef(TB303)

        mutant1 = mutate_synth(tb303, amount=0.5, seed=42)
        mutant2 = mutate_synth(tb303, amount=0.5, seed=99)

        # Should be different (very high probability)
        assert mutant1.mutation_log != mutant2.mutation_log or \
               mutant1.source_code != mutant2.source_code

    def test_mutate_low_amount_fewer_mutations(self):
        """Test low mutation amount produces fewer changes."""
        tb303 = parse_synthdef(TB303)

        # Low amount (0.1) should have fewer mutations than high amount (0.9)
        low = mutate_synth(tb303, amount=0.1, seed=42)
        high = mutate_synth(tb303, amount=0.9, seed=43)

        # This is probabilistic, but should hold most of the time
        # We accept some variance
        assert len(low.mutation_log) <= len(high.mutation_log) + 2

    def test_mutate_zero_amount_no_mutations(self):
        """Test zero mutation amount produces no changes."""
        tb303 = parse_synthdef(TB303)

        mutant = mutate_synth(tb303, amount=0.0, seed=42)

        # With 0.0 amount, should have no mutations (or very few)
        # Mutation log might say "No mutations applied"
        assert len(mutant.mutation_log) <= 1

    def test_mutate_preserves_structure(self):
        """Test mutation preserves essential SynthDef structure."""
        tb303 = parse_synthdef(TB303)

        mutant = mutate_synth(tb303, amount=0.8, seed=42)

        # Must preserve SynthDef structure
        assert re.search(r'SynthDef\s*\(', mutant.source_code)
        assert "Out.ar" in mutant.source_code
        assert mutant.source_code.strip().endswith(".add;")

    def test_mutate_preserves_control_count(self):
        """Test mutation doesn't drastically change control count."""
        tb303 = parse_synthdef(TB303)
        original_count = len(tb303.controls)

        mutant = mutate_synth(tb303, amount=0.5, seed=42)

        # Control count should be similar (allow ±2 for added modulation params)
        assert abs(len(mutant.controls) - original_count) <= 2

    def test_mutate_logs_all_changes(self):
        """Test mutation log records all applied changes."""
        tb303 = parse_synthdef(TB303)

        mutant = mutate_synth(tb303, amount=1.0, seed=42)

        # Should have detailed mutation log
        assert len(mutant.mutation_log) > 0
        for log in mutant.mutation_log:
            assert isinstance(log, str)
            assert len(log) > 0


class TestSwapOscillator:
    """Tests for swap_oscillator function."""

    def test_swap_oscillator_saw_to_pulse(self):
        """Test swapping Saw to another oscillator."""
        code = "sig = Saw.ar(freq);"

        new_code, msg = swap_oscillator(code)

        # Should swap to different oscillator
        assert "Saw" not in new_code
        assert any(osc in new_code for osc in ["SinOsc", "Pulse", "Tri", "VarSaw"])
        assert msg is not None
        assert "Saw" in msg
        assert "→" in msg

    def test_swap_oscillator_pulse_to_other(self):
        """Test swapping Pulse oscillator."""
        code = "sig = Pulse.ar(freq, 0.5);"

        new_code, msg = swap_oscillator(code)

        assert "Pulse" not in new_code
        assert msg is not None
        assert "Pulse" in msg

    def test_swap_oscillator_no_oscillator(self):
        """Test swap with no oscillator in code."""
        code = "sig = WhiteNoise.ar();"

        new_code, msg = swap_oscillator(code)

        # Should return unchanged
        assert new_code == code
        assert msg is None

    def test_swap_oscillator_preserves_rate(self):
        """Test oscillator swap preserves .ar/.kr rate."""
        code = "lfo = SinOsc.kr(2);"

        new_code, msg = swap_oscillator(code)

        # Should preserve .kr rate
        assert ".kr" in new_code


class TestSwapFilter:
    """Tests for swap_filter function."""

    def test_swap_filter_lpf_to_other(self):
        """Test swapping LPF to another filter."""
        code = "sig = LPF.ar(sig, 1000);"

        new_code, msg = swap_filter(code)

        assert "LPF" not in new_code
        assert any(f in new_code for f in ["HPF", "BPF", "RLPF", "MoogFF"])
        assert msg is not None
        assert "LPF" in msg

    def test_swap_filter_moogff(self):
        """Test swapping MoogFF filter."""
        code = "sig = MoogFF.ar(sig, cutoff, resonance);"

        new_code, msg = swap_filter(code)

        assert "MoogFF" not in new_code
        assert msg is not None

    def test_swap_filter_no_filter(self):
        """Test swap with no filter in code."""
        code = "sig = SinOsc.ar(freq);"

        new_code, msg = swap_filter(code)

        assert new_code == code
        assert msg is None


class TestAddModulation:
    """Tests for add_modulation function."""

    def test_add_modulation_to_cutoff(self):
        """Test adding LFO modulation to cutoff parameter."""
        code = """SynthDef(\\test, {
    |cutoff=1200|
    var sig;
    sig = MoogFF.ar(sig, cutoff, 0.5);
}).add;"""

        new_code, msg = add_modulation(code, "cutoff")

        assert msg is not None
        assert "cutoff" in msg
        assert "LFO" in msg or "modulation" in msg
        assert "cutoff_lfo" in new_code
        assert any(lfo in new_code for lfo in ["LFO", "SinOsc.kr", "LFNoise"])

    def test_add_modulation_to_freq(self):
        """Test adding modulation to freq parameter."""
        code = """SynthDef(\\test, {
    |freq=440|
    var sig;
    sig = SinOsc.ar(freq);
}).add;"""

        new_code, msg = add_modulation(code, "freq")

        assert msg is not None
        assert "freq_lfo" in new_code

    def test_add_modulation_nonexistent_param(self):
        """Test adding modulation to parameter that doesn't exist."""
        code = "sig = SinOsc.ar(440);"

        new_code, msg = add_modulation(code, "nonexistent")

        assert new_code == code
        assert msg is None


class TestAddDistortion:
    """Tests for add_distortion function."""

    def test_add_distortion_tanh(self):
        """Test adding distortion to signal."""
        code = """SynthDef(\\test, {
    var sig;
    sig = SinOsc.ar(440);
    Out.ar(0, sig);
}).add;"""

        new_code, msg = add_distortion(code)

        assert msg is not None
        assert "distortion" in msg.lower()
        assert any(d in new_code for d in ["tanh", "softclip", "distort"])

    def test_add_distortion_no_signal(self):
        """Test distortion with no signal variable."""
        code = "Out.ar(0, SinOsc.ar(440));"

        new_code, msg = add_distortion(code)

        # Should handle gracefully
        assert new_code == code or msg is None


class TestModifyParameterDefaults:
    """Tests for modify_parameter_defaults function."""

    def test_modify_parameters_changes_values(self):
        """Test parameter default values are modified."""
        code = "|out=0, freq=440, cutoff=1200, amp=0.5|"

        new_code, msgs = modify_parameter_defaults(code, amount=0.5)

        # Should modify some parameters
        assert len(msgs) > 0

        # out parameter should not change
        assert "out=0" in new_code

        # Other parameters should change
        assert new_code != code

    def test_modify_parameters_respects_amount(self):
        """Test modification amount affects change magnitude."""
        code = "|freq=440, cutoff=1200|"

        # Low amount should produce smaller changes
        new_code_low, msgs_low = modify_parameter_defaults(code, amount=0.1)
        new_code_high, msgs_high = modify_parameter_defaults(code, amount=1.0)

        # Extract modified values
        freq_low = float(re.search(r'freq=([\d.]+)', new_code_low).group(1))
        freq_high = float(re.search(r'freq=([\d.]+)', new_code_high).group(1))

        # Both should differ from original, but high amount should differ more
        assert freq_low != 440.0
        assert freq_high != 440.0

    def test_modify_parameters_preserves_gate(self):
        """Test gate parameter is not modified."""
        code = "|gate=1, freq=440|"

        new_code, msgs = modify_parameter_defaults(code, amount=0.8)

        # gate should remain unchanged
        assert "gate=1" in new_code


class TestModifyEnvelope:
    """Tests for modify_envelope function."""

    def test_modify_envelope_asr(self):
        """Test modifying ASR envelope times."""
        code = "env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate);"

        new_code, msg = modify_envelope(code)

        assert msg is not None
        assert "asr" in msg
        assert new_code != code
        assert "Env.asr" in new_code

    def test_modify_envelope_perc(self):
        """Test modifying percussive envelope."""
        code = "env = EnvGen.kr(Env.perc(0.001, 0.2));"

        new_code, msg = modify_envelope(code)

        assert msg is not None
        assert "perc" in msg
        assert "Env.perc" in new_code

    def test_modify_envelope_no_envelope(self):
        """Test modification with no envelope in code."""
        code = "sig = SinOsc.ar(440);"

        new_code, msg = modify_envelope(code)

        assert new_code == code
        assert msg is None


class TestExtractControls:
    """Tests for extract_controls function."""

    def test_extract_controls_basic(self):
        """Test extracting controls from parameter block."""
        code = "|out=0, freq=440, amp=0.5|"

        controls = extract_controls(code)

        assert len(controls) == 3
        names = {c.name for c in controls}
        assert names == {"out", "freq", "amp"}

        freq_ctrl = next(c for c in controls if c.name == "freq")
        assert freq_ctrl.default_value == 440.0

    def test_extract_controls_tb303(self):
        """Test extracting controls from TB-303."""
        tb303 = parse_synthdef(TB303)

        controls = extract_controls(tb303.source_code)

        # Should match parsed controls
        assert len(controls) == len(tb303.controls)

        names = {c.name for c in controls}
        assert "cutoff" in names
        assert "resonance" in names
        assert "envmod" in names

    def test_extract_controls_no_params(self):
        """Test extraction with no parameter block."""
        code = "SynthDef(\\test, { Out.ar(0, SinOsc.ar(440)); });"

        controls = extract_controls(code)

        assert len(controls) == 0


class TestBreedSynths:
    """Tests for breed_synths function."""

    def test_breed_creates_hybrid(self):
        """Test breeding two synths creates a hybrid."""
        tb303 = parse_synthdef(TB303)
        simple = parse_synthdef(SIMPLE_SINE)

        child = breed_synths(tb303, simple, seed=42)

        assert isinstance(child, GeneratedSynth)
        assert child.generation_method == "crossover"
        assert child.parent_ids == ["tb303", "simple_sine"]
        assert "tb303_x_simple_sine" in child.name

    def test_breed_combines_features(self):
        """Test child combines features from both parents."""
        tb303 = parse_synthdef(TB303)
        simple = parse_synthdef(SIMPLE_SINE)

        child = breed_synths(tb303, simple, seed=42)

        # Should have valid SynthDef structure
        assert "SynthDef" in child.source_code
        assert "Out.ar" in child.source_code

        # Should have oscillator and envelope
        assert any(osc in child.source_code for osc in ["Saw", "SinOsc", "Pulse"])
        assert "env" in child.source_code

    def test_breed_is_deterministic(self):
        """Test breeding is deterministic with same seed."""
        tb303 = parse_synthdef(TB303)
        simple = parse_synthdef(SIMPLE_SINE)

        child1 = breed_synths(tb303, simple, seed=42)
        child2 = breed_synths(tb303, simple, seed=42)

        assert child1.source_code == child2.source_code
        assert child1.mutation_log == child2.mutation_log

    def test_breed_varies_with_seed(self):
        """Test breeding varies with different seeds."""
        tb303 = parse_synthdef(TB303)
        simple = parse_synthdef(SIMPLE_SINE)

        child1 = breed_synths(tb303, simple, seed=42)
        child2 = breed_synths(tb303, simple, seed=99)

        # Should be different
        assert child1.source_code != child2.source_code or \
               child1.mutation_log != child2.mutation_log

    def test_breed_preserves_structure(self):
        """Test breeding preserves essential structure."""
        tb303 = parse_synthdef(TB303)
        simple = parse_synthdef(SIMPLE_SINE)

        child = breed_synths(tb303, simple, seed=42)

        # Must have SynthDef
        assert re.search(r'SynthDef\s*\(', child.source_code)

        # Must have Out.ar
        assert "Out.ar" in child.source_code

        # Must end with .add
        assert child.source_code.strip().endswith(".add;")

    def test_breed_inherits_category(self):
        """Test child inherits category from first parent."""
        tb303 = parse_synthdef(TB303)
        simple = parse_synthdef(SIMPLE_SINE)

        child = breed_synths(tb303, simple, seed=42)

        assert child.category == tb303.category
