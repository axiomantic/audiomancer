"""SynthDef generation and evolution for audiomancer.

This module provides evolutionary synthesis through genetic operations on SuperCollider
SynthDefs. It includes:
- Generation of new synths from templates or descriptions
- Mutation of existing synths (UGen swapping, parameter tweaking)
- Crossover breeding of two parent synths
- Lineage tracking for evolutionary history

Example:
    >>> from audiomancer.generators.synths import generate_synth, mutate_synth
    >>> from audiomancer.analyzers.synthdef import parse_synthdef
    >>> from pathlib import Path
    >>>
    >>> # Generate from template
    >>> synth = generate_synth("acid bass with filter sweep", category="bass")
    >>> synth.name
    'acid_bass_001'
    >>>
    >>> # Mutate existing synth
    >>> tb303 = parse_synthdef(Path("synths/tb303.scd"))
    >>> variant = mutate_synth(tb303, amount=0.5)
    >>> variant.mutation_log
    ['Saw → Pulse', 'Added tanh distortion']
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from pathlib import Path
import random
import re
import hashlib

from ..errors import SynthDefError
from ..analyzers.synthdef import SynthDefInfo, SynthControl


@dataclass
class GeneratedSynth:
    """A generated or mutated SynthDef.

    Attributes:
        name: SynthDef name (unique identifier)
        source_code: Full SuperCollider .scd code
        controls: List of control parameters
        parent_ids: Parent synth IDs (empty if generated from scratch)
        generation_method: How synth was created (generated/mutation/crossover)
        mutation_log: Human-readable list of mutations applied
        category: Inferred category (bass, lead, pad, drum, fx)

    Example:
        >>> synth = GeneratedSynth(
        ...     name="tb303_evolved_1",
        ...     source_code="SynthDef(...)",
        ...     controls=[SynthControl("cutoff", 1500.0)],
        ...     parent_ids=["tb303"],
        ...     generation_method="mutation",
        ...     mutation_log=["Saw → Pulse", "cutoff: 1200 → 1500"],
        ... )
    """
    name: str
    source_code: str
    controls: list[SynthControl]
    parent_ids: Optional[list[str]] = None
    generation_method: str = "generated"
    mutation_log: Optional[list[str]] = None
    category: Optional[str] = None


# UGen substitution categories for mutation
UGEN_CATEGORIES = {
    "oscillators": ["SinOsc", "Saw", "Pulse", "Tri", "VarSaw", "LFSaw", "Blip"],
    "filters": ["LPF", "HPF", "BPF", "RLPF", "MoogFF", "BLowPass", "MoogLadder"],
    "distortion": ["tanh", "softclip", "Shaper", "CrossoverDistortion", "Decimator"],
    "envelopes": ["Perc", "ADSR", "ASR", "Linen"],
    "modulation": ["LFO", "SinOsc.kr", "LFNoise1", "LFTri.kr", "LFNoise0"],
}


def generate_synth(
    description: str,
    base_synth: Optional[SynthDefInfo] = None,
    category: Literal["bass", "lead", "pad", "drum", "fx"] = "bass"
) -> GeneratedSynth:
    """Generate a new SynthDef from description.

    If base_synth provided, uses it as starting point and applies transformations
    based on description keywords. Otherwise generates from category template.

    Description keywords:
    - "acid": Adds resonant filter with envelope
    - "warm": Uses saw wave with low-pass filter
    - "bright": Uses pulse wave with high cutoff
    - "filtered": Adds MoogFF or RLPF
    - "distorted": Adds distortion/saturation
    - "sweep": Adds LFO modulation to filter

    Args:
        description: Natural language description of desired sound
        base_synth: Optional existing synth to modify
        category: Sound category (bass, lead, pad, drum, fx)

    Returns:
        GeneratedSynth with source code and metadata

    Raises:
        SynthDefError: If template cannot be loaded or customized

    Example:
        >>> synth = generate_synth("warm acid bass with filter sweep", category="bass")
        >>> synth.name
        'warm_acid_bass_001'
        >>> "MoogFF" in synth.source_code
        True
        >>> "LFO" in synth.source_code  # For sweep
        True
    """
    if base_synth:
        # Modify existing synth based on description
        code = base_synth.source_code
        mutations = []

        # Apply transformations based on keywords
        if "acid" in description.lower():
            code, msg = _add_acid_filter(code)
            if msg:
                mutations.append(msg)

        if "warm" in description.lower():
            code, msg = _make_warm(code)
            if msg:
                mutations.append(msg)

        if "sweep" in description.lower():
            code, msg = add_modulation(code, "cutoff")
            if msg:
                mutations.append(msg)

        if "distorted" in description.lower():
            code, msg = add_distortion(code)
            if msg:
                mutations.append(msg)

        # Generate unique name
        name = _generate_name_from_description(description, base_synth.name)

        return GeneratedSynth(
            name=name,
            source_code=code,
            controls=extract_controls(code),
            parent_ids=[base_synth.name] if hasattr(base_synth, 'name') else None,
            generation_method="from_description",
            mutation_log=mutations,
            category=category,
        )
    else:
        # Generate from template
        template_path = _get_template_path(category)
        template_code = template_path.read_text()

        # Customize template with description
        code = customize_template(template_code, description, category)
        name = _generate_name_from_description(description, category)

        return GeneratedSynth(
            name=name,
            source_code=code,
            controls=extract_controls(code),
            parent_ids=[],
            generation_method="from_template",
            mutation_log=[f"Generated from {category} template"],
            category=category,
        )


def mutate_synth(
    synth: SynthDefInfo,
    amount: float = 0.3,
    seed: Optional[int] = None,
) -> GeneratedSynth:
    """Create a variation of a SynthDef through mutation.

    Mutation operations (probability based on amount parameter):
    1. Swap oscillator UGen (e.g., Saw → Pulse) - amount * 0.4
    2. Swap filter UGen (e.g., LPF → MoogFF) - amount * 0.3
    3. Add modulation (LFO to parameter) - amount * 0.3
    4. Add distortion effect - amount * 0.2
    5. Modify parameter defaults - amount * 0.5
    6. Modify envelope shape - amount * 0.2

    All mutations preserve synth structure (SynthDef, Out, envelope).

    Args:
        synth: Source SynthDef to mutate
        amount: Mutation strength (0.0-1.0, higher = more drastic changes)
        seed: Random seed for deterministic testing

    Returns:
        GeneratedSynth with mutations applied and logged

    Raises:
        SynthDefError: If mutation produces invalid SuperCollider code

    Example:
        >>> from audiomancer.analyzers.synthdef import parse_synthdef
        >>> tb303 = parse_synthdef(Path("synths/tb303.scd"))
        >>> variant = mutate_synth(tb303, amount=0.5, seed=42)
        >>> variant.name
        'tb303_m427'
        >>> variant.mutation_log
        ['Saw → Pulse', 'Added LFO modulation to cutoff', 'cutoff: 1200.0 → 1440.0']
        >>> variant.parent_ids
        ['tb303']
    """
    if seed is not None:
        random.seed(seed)

    code = synth.source_code
    mutations = []

    # 1. Swap oscillator (probability: amount * 0.4)
    if random.random() < amount * 0.4:
        code, msg = swap_oscillator(code)
        if msg:
            mutations.append(msg)

    # 2. Swap filter (probability: amount * 0.3)
    if random.random() < amount * 0.3:
        code, msg = swap_filter(code)
        if msg:
            mutations.append(msg)

    # 3. Add modulation (probability: amount * 0.3)
    if random.random() < amount * 0.3:
        # Pick a random parameter to modulate
        params = ["cutoff", "freq", "resonance", "amp"]
        param = random.choice(params)
        code, msg = add_modulation(code, param)
        if msg:
            mutations.append(msg)

    # 4. Add distortion (probability: amount * 0.2)
    if random.random() < amount * 0.2:
        code, msg = add_distortion(code)
        if msg:
            mutations.append(msg)

    # 5. Modify parameter defaults (probability: amount * 0.5)
    if random.random() < amount * 0.5:
        code, msgs = modify_parameter_defaults(code, amount)
        mutations.extend(msgs)

    # 6. Modify envelope (probability: amount * 0.2)
    if random.random() < amount * 0.2:
        code, msg = modify_envelope(code)
        if msg:
            mutations.append(msg)

    # Generate unique mutant name
    mutation_id = random.randint(1, 999) if seed is None else seed % 1000
    name = f"{synth.name}_m{mutation_id}"

    return GeneratedSynth(
        name=name,
        source_code=code,
        controls=extract_controls(code),
        parent_ids=[synth.name],
        generation_method="mutation",
        mutation_log=mutations if mutations else ["No mutations applied"],
        category=synth.category,
    )


def breed_synths(
    synth_a: SynthDefInfo,
    synth_b: SynthDefInfo,
    seed: Optional[int] = None,
) -> GeneratedSynth:
    """Crossover two SynthDefs to create a hybrid child.

    Crossover strategy:
    1. Take oscillator section from parent A
    2. Take filter section from parent B
    3. Randomly mix effects from both parents
    4. Combine unique controls from both parents
    5. Average numeric parameter defaults

    Args:
        synth_a: First parent SynthDef
        synth_b: Second parent SynthDef
        seed: Random seed for deterministic testing

    Returns:
        GeneratedSynth combining features of both parents

    Raises:
        SynthDefError: If crossover produces invalid code

    Example:
        >>> tb303 = parse_synthdef(Path("synths/tb303.scd"))
        >>> juno = parse_synthdef(Path("synths/juno_pad.scd"))
        >>> child = breed_synths(tb303, juno, seed=42)
        >>> child.name
        'tb303_x_juno_pad'
        >>> child.parent_ids
        ['tb303', 'juno_pad']
        >>> "Saw" in child.source_code  # From tb303
        True
    """
    if seed is not None:
        random.seed(seed)

    mutations = []

    # Extract sections from both parents
    osc_a = _extract_oscillator_section(synth_a.source_code)
    osc_b = _extract_oscillator_section(synth_b.source_code)

    filter_a = _extract_filter_section(synth_a.source_code)
    filter_b = _extract_filter_section(synth_b.source_code)

    # Choose which parent contributes which section
    if random.random() < 0.5:
        osc_section = osc_a
        filter_section = filter_b
        mutations.append(f"Oscillator from {synth_a.name}, filter from {synth_b.name}")
    else:
        osc_section = osc_b
        filter_section = filter_a
        mutations.append(f"Oscillator from {synth_b.name}, filter from {synth_a.name}")

    # Combine controls from both parents
    combined_controls = _combine_controls(synth_a, synth_b)

    # Build new SynthDef
    child_name = f"{synth_a.name}_x_{synth_b.name}"
    child_code = _build_synthdef(
        name=child_name,
        controls=combined_controls,
        oscillator_code=osc_section,
        filter_code=filter_section,
    )

    return GeneratedSynth(
        name=child_name,
        source_code=child_code,
        controls=combined_controls,
        parent_ids=[synth_a.name, synth_b.name],
        generation_method="crossover",
        mutation_log=mutations,
        category=synth_a.category,  # Inherit from first parent
    )


# ============================================================================
# Mutation Helper Functions
# ============================================================================

def swap_oscillator(code: str) -> tuple[str, Optional[str]]:
    """Replace one oscillator with another from same category.

    Args:
        code: SuperCollider source code

    Returns:
        Tuple of (modified_code, mutation_message)

    Example:
        >>> code = "sig = Saw.ar(freq);"
        >>> new_code, msg = swap_oscillator(code)
        >>> msg
        'Saw → Pulse'
    """
    for osc in UGEN_CATEGORIES["oscillators"]:
        # Match UGen with .ar or .kr
        pattern = rf'\b{osc}\s*\.\s*(ar|kr)'
        if re.search(pattern, code):
            # Pick a different oscillator
            alternatives = [o for o in UGEN_CATEGORIES["oscillators"] if o != osc]
            replacement = random.choice(alternatives)

            # Replace first occurrence only
            new_code = re.sub(pattern, f"{replacement}.\\1", code, count=1)
            return new_code, f"{osc} → {replacement}"

    return code, None


def swap_filter(code: str) -> tuple[str, Optional[str]]:
    """Replace filter UGen with another from same category.

    Args:
        code: SuperCollider source code

    Returns:
        Tuple of (modified_code, mutation_message)

    Example:
        >>> code = "sig = LPF.ar(sig, 1000);"
        >>> new_code, msg = swap_filter(code)
        >>> msg
        'LPF → MoogFF'
    """
    for filt in UGEN_CATEGORIES["filters"]:
        pattern = rf'\b{filt}\s*\.\s*ar'
        if re.search(pattern, code):
            alternatives = [f for f in UGEN_CATEGORIES["filters"] if f != filt]
            replacement = random.choice(alternatives)
            new_code = re.sub(pattern, f"{replacement}.ar", code, count=1)
            return new_code, f"{filt} → {replacement}"

    return code, None


def add_modulation(code: str, param: str) -> tuple[str, Optional[str]]:
    """Add LFO modulation to a parameter.

    Adds a low-frequency oscillator to modulate a synth parameter over time.

    Args:
        code: SuperCollider source code
        param: Parameter to modulate (e.g., "cutoff", "freq")

    Returns:
        Tuple of (modified_code, mutation_message)

    Example:
        >>> code = "sig = MoogFF.ar(sig, cutoff, resonance);"
        >>> new_code, msg = add_modulation(code, "cutoff")
        >>> "LFO" in new_code or "SinOsc.kr" in new_code
        True
        >>> msg
        'Added LFO modulation to cutoff'
    """
    # Check if parameter exists in code
    if param not in code:
        return code, None

    # Choose random LFO type
    lfo_type = random.choice(UGEN_CATEGORIES["modulation"])

    # Generate LFO variable name
    lfo_var = f"{param}_lfo"

    # Insert LFO declaration after variable declarations
    # Find the var line
    var_match = re.search(r'(var\s+[^;]+;)', code)
    if var_match:
        var_line = var_match.group(1)
        # Add lfo_var to variable list
        new_var_line = var_line.replace(';', f', {lfo_var};')
        code = code.replace(var_line, new_var_line)

    # Add LFO assignment after var declarations
    lfo_code = f"\n    {lfo_var} = {lfo_type}({random.uniform(0.1, 5.0):.2f}).range(0.5, 1.5);"

    # Insert after var line
    if var_match:
        insert_pos = var_match.end()
        code = code[:insert_pos] + lfo_code + code[insert_pos:]

    # Multiply parameter by LFO
    # Find parameter usage (not in declaration)
    param_pattern = rf'(\W){param}(\W)'

    def replace_param(match: re.Match[str]) -> str:
        # Don't replace in |param=default| declaration
        if '|' in code[max(0, match.start()-20):match.start()]:
            return match.group(0)
        return f"{match.group(1)}{param} * {lfo_var}{match.group(2)}"

    code = re.sub(param_pattern, replace_param, code)

    return code, f"Added LFO modulation to {param}"


def add_distortion(code: str) -> tuple[str, Optional[str]]:
    """Add distortion/saturation effect to signal.

    Args:
        code: SuperCollider source code

    Returns:
        Tuple of (modified_code, mutation_message)

    Example:
        >>> code = "sig = SinOsc.ar(freq) * env;"
        >>> new_code, msg = add_distortion(code)
        >>> "tanh" in new_code or "distort" in new_code
        True
    """
    # Find the signal variable (usually 'sig')
    sig_var = "sig"

    # Choose random distortion type
    dist_types = ["tanh", "softclip", "distort"]
    dist_type = random.choice(dist_types)

    # Find last assignment to sig before Out.ar
    out_match = re.search(r'Out\.ar', code)
    if not out_match:
        return code, None

    # Find last sig = ... before Out.ar
    sig_pattern = r'(sig\s*=\s*[^;]+;)'
    matches = list(re.finditer(sig_pattern, code[:out_match.start()]))

    if not matches:
        return code, None

    last_match = matches[-1]
    old_line = last_match.group(1)

    # Apply distortion
    if dist_type == "tanh":
        new_line = old_line.replace(';', '.tanh;')
        msg = "Added tanh distortion"
    elif dist_type == "softclip":
        new_line = old_line.replace(';', '.softclip;')
        msg = "Added softclip distortion"
    else:  # distort
        new_line = old_line.replace(';', '.distort;')
        msg = "Added distortion"

    code = code.replace(old_line, new_line)
    return code, msg


def modify_parameter_defaults(code: str, amount: float) -> tuple[str, list[str]]:
    """Modify default values of control parameters.

    Args:
        code: SuperCollider source code
        amount: Mutation strength (0.0-1.0)

    Returns:
        Tuple of (modified_code, list of mutation messages)

    Example:
        >>> code = "|out=0, freq=440, cutoff=1200|"
        >>> new_code, msgs = modify_parameter_defaults(code, 0.3)
        >>> msgs
        ['cutoff: 1200.0 → 1440.0']
    """
    mutations = []

    # Find parameter declarations: |param=value, param2=value2|
    param_block = re.search(r'\|([^|]+)\|', code)
    if not param_block:
        return code, mutations

    params_str = param_block.group(1)

    # Parse individual parameters
    param_pattern = r'(\w+)\s*=\s*([\d.]+)'

    def modify_value(match: re.Match[str]) -> str:
        param_name = match.group(1)
        old_value = float(match.group(2))

        # Skip 'out' and 'gate' parameters
        if param_name in ['out', 'gate']:
            return match.group(0)

        # Randomly modify value by ±20% * amount
        change_factor = 1.0 + random.uniform(-0.2, 0.2) * amount
        new_value = old_value * change_factor

        # Round to reasonable precision
        new_value = round(new_value, 2)

        if new_value != old_value:
            mutations.append(f"{param_name}: {old_value} → {new_value}")

        return f"{param_name}={new_value}"

    new_params_str = re.sub(param_pattern, modify_value, params_str)
    code = code.replace(params_str, new_params_str)

    return code, mutations


def modify_envelope(code: str) -> tuple[str, Optional[str]]:
    """Modify envelope shape (attack, decay, sustain, release times).

    Args:
        code: SuperCollider source code

    Returns:
        Tuple of (modified_code, mutation_message)
    """
    # Find envelope declarations (Env.asr, Env.perc, Env.adsr)
    env_patterns = [
        (r'Env\.asr\(([^)]+)\)', 'asr'),
        (r'Env\.perc\(([^)]+)\)', 'perc'),
        (r'Env\.adsr\(([^)]+)\)', 'adsr'),
    ]

    for pattern, env_type in env_patterns:
        match = re.search(pattern, code)
        if match:
            old_env = match.group(0)
            params = match.group(1)

            # Parse numeric parameters
            nums = re.findall(r'[\d.]+', params)
            if not nums:
                continue

            # Modify times by ±30%
            new_nums = []
            for num in nums:
                val = float(num)
                new_val = val * random.uniform(0.7, 1.3)
                new_nums.append(f"{new_val:.3f}")

            # Rebuild envelope
            new_params = ', '.join(new_nums)
            new_env = f"Env.{env_type}({new_params})"

            code = code.replace(old_env, new_env)
            return code, f"Modified {env_type} envelope times"

    return code, None


# ============================================================================
# Crossover Helper Functions
# ============================================================================

def _extract_oscillator_section(code: str) -> str:
    """Extract oscillator code section from SynthDef."""
    # Find oscillator assignments (variables assigned with UGen.ar)
    osc_pattern = r'((?:osc\d*|sig)\s*=\s*(?:Saw|SinOsc|Pulse|Tri|VarSaw)[^;]+;)'
    matches = re.findall(osc_pattern, code)
    return '\n    '.join(matches) if matches else "sig = SinOsc.ar(freq);"


def _extract_filter_section(code: str) -> str:
    """Extract filter code section from SynthDef."""
    filter_pattern = r'(sig\s*=\s*(?:LPF|HPF|BPF|RLPF|MoogFF|BLowPass)[^;]+;)'
    matches = re.findall(filter_pattern, code)
    return '\n    '.join(matches) if matches else ""


def _combine_controls(synth_a: SynthDefInfo, synth_b: SynthDefInfo) -> list[SynthControl]:
    """Combine and deduplicate controls from both parents."""
    combined = {}

    # Add controls from both parents
    for ctrl in synth_a.controls + synth_b.controls:
        if ctrl.name not in combined:
            combined[ctrl.name] = ctrl
        else:
            # Average numeric defaults
            existing = combined[ctrl.name]
            avg_value = (existing.default_value + ctrl.default_value) / 2
            combined[ctrl.name] = SynthControl(ctrl.name, avg_value)

    return list(combined.values())


def _build_synthdef(
    name: str,
    controls: list[SynthControl],
    oscillator_code: str,
    filter_code: str,
) -> str:
    """Build complete SynthDef from components."""
    # Build parameter list
    params = ', '.join([
        f"{c.name}={c.default_value}" for c in controls
    ])

    # Extract variable names from oscillator and filter code
    vars_needed = set(re.findall(r'\b(osc\d*|sig|env|fenv)\b', oscillator_code + filter_code))
    var_decl = ', '.join(sorted(vars_needed))

    template = f'''// Crossover synth: {name}
SynthDef(\\{name}, {{
    |{params}|
    var {var_decl};

    // Envelope
    env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate, doneAction: 2);

    // Oscillator section
    {oscillator_code}

    // Filter section
    {filter_code}

    // Output
    sig = sig * env * amp;
    Out.ar(out, sig ! 2);
}}).add;
'''
    return template


# ============================================================================
# Template and Utility Functions
# ============================================================================

def extract_controls(code: str) -> list[SynthControl]:
    """Extract control parameters from SynthDef source code.

    Args:
        code: SuperCollider source code

    Returns:
        List of SynthControl objects
    """
    controls = []

    # Find parameter block: |param=value, ...|
    param_match = re.search(r'\|([^|]+)\|', code)
    if param_match:
        params_str = param_match.group(1)
        # Parse each param=value pair
        for match in re.finditer(r'(\w+)\s*=\s*([\d.]+)', params_str):
            name = match.group(1)
            value = float(match.group(2))
            controls.append(SynthControl(name=name, default_value=value))

    return controls


def _get_template_path(category: str) -> Path:
    """Get path to template SynthDef for category."""
    templates_dir = Path(__file__).parent / "templates"
    template_file = templates_dir / f"{category}_template.scd"

    if not template_file.exists():
        raise SynthDefError(
            f"Template not found for category: {category}",
            details={"category": category, "path": str(template_file)}
        )

    return template_file


def customize_template(template_code: str, description: str, category: str) -> str:
    """Customize template with description-based modifications."""
    code = template_code

    # Apply description-based customizations
    if "bright" in description.lower():
        code = code.replace("LPF", "HPF")  # High-pass for brightness

    if "warm" in description.lower():
        code = code.replace("Pulse", "Saw")  # Saw waves are warmer

    return code


def _generate_name_from_description(description: str, base: str) -> str:
    """Generate unique SynthDef name from description."""
    # Extract keywords
    keywords = []
    for word in description.lower().split():
        if word in ["acid", "warm", "bright", "filtered", "distorted", "sweep"]:
            keywords.append(word)

    # Combine with base name or category
    if keywords:
        name_part = '_'.join(keywords[:2])  # Max 2 keywords
    else:
        name_part = base

    # Add random suffix
    suffix = random.randint(1, 999)
    return f"{name_part}_{suffix:03d}"


def _add_acid_filter(code: str) -> tuple[str, Optional[str]]:
    """Add resonant filter with envelope modulation (acid sound)."""
    # Check if already has acid filter
    if "MoogFF" in code or "RLPF" in code:
        return code, None

    # Find the signal variable line (before Out.ar)
    out_match = re.search(r'Out\.ar', code)
    if not out_match:
        return code, None

    # Find last sig = ... before Out.ar
    sig_pattern = r'(sig\s*=\s*[^;]+;)'
    matches = list(re.finditer(sig_pattern, code[:out_match.start()]))
    if not matches:
        return code, None

    last_match = matches[-1]
    old_line = last_match.group(1)

    # Add filter envelope and MoogFF filter
    # Insert after envelope declaration
    env_match = re.search(r'(env\s*=\s*[^;]+;)', code)
    if env_match:
        insert_pos = env_match.end()
        fenv_code = "\n    fenv = EnvGen.kr(Env.perc(0.01, 0.3)) * 2000;"
        code = code[:insert_pos] + fenv_code + code[insert_pos:]

    # Add cutoff and resonance parameters if not present
    param_match = re.search(r'\|([^|]+)\|', code)
    if param_match and "cutoff" not in code:
        params = param_match.group(1)
        new_params = params + ", cutoff=1200, resonance=0.7"
        code = code.replace(f"|{params}|", f"|{new_params}|")

    # Add fenv to var declaration
    var_match = re.search(r'(var\s+[^;]+;)', code)
    if var_match and "fenv" not in code:
        var_line = var_match.group(1)
        new_var_line = var_line.replace(';', ', fenv;')
        code = code.replace(var_line, new_var_line)

    # Replace signal line with filtered version
    new_line = old_line.replace(';', '')
    new_line = f"sig = MoogFF.ar({new_line.split('=')[1].strip()}, cutoff + fenv, resonance);"
    code = code.replace(old_line, new_line)

    return code, "Added acid filter with envelope"


def _make_warm(code: str) -> tuple[str, Optional[str]]:
    """Make sound warmer by using saw wave and low-pass filter."""
    modifications = []

    # Replace pulse with saw
    if "Pulse" in code:
        code = code.replace("Pulse", "Saw")
        modifications.append("Pulse → Saw")

    # Ensure low-pass filter
    if "HPF" in code:
        code = code.replace("HPF", "LPF")
        modifications.append("HPF → LPF")

    return code, ", ".join(modifications) if modifications else None
