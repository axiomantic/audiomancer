"""SynthDef analysis interfaces for audiomancer.

This module defines Protocol interfaces for parsing and analyzing SuperCollider
SynthDef files to extract controls and metadata.
"""

from typing import Literal, Optional, Protocol
from typing_extensions import TypedDict


class ControlSpec(TypedDict, total=False):
    """Specification for a SynthDef control parameter.

    Describes the valid range and characteristics of a synth control.

    Example:
        >>> spec = ControlSpec(
        ...     min=200.0,
        ...     max=4000.0,
        ...     default=1200.0,
        ...     warp="exp",  # Exponential scaling for frequency
        ...     step=1.0,
        ... )
    """
    min: float  # Minimum value
    max: float  # Maximum value
    default: float  # Default value
    warp: Literal["linear", "exp", "log"]  # Value scaling
    step: float  # Step size for discrete values


class SynthControl(TypedDict, total=False):
    """A control parameter extracted from a SynthDef.

    Represents a parameter that can be modified during synthesis.

    Example:
        >>> control = SynthControl(
        ...     name="cutoff",
        ...     default_value=1200.0,
        ...     spec=ControlSpec(
        ...         min=200.0,
        ...         max=4000.0,
        ...         default=1200.0,
        ...         warp="exp",
        ...         step=1.0,
        ...     ),
        ... )
    """
    name: str  # Parameter name (e.g., "cutoff", "resonance")
    default_value: float  # Default value if not specified
    spec: ControlSpec  # Valid range and scaling


class SynthDefMetadata(TypedDict, total=False):
    """Metadata extracted from a SynthDef file.

    Contains all information parsed from a .scd file including controls,
    UGens used, and categorization.

    Example:
        >>> synthdef = SynthDefMetadata(
        ...     id="synt_tb303",
        ...     name="tb303",
        ...     file_path="/synths/tb303.scd",
        ...     file_hash="abc123",
        ...     num_channels=1,
        ...     has_gate=True,
        ...     has_envelope=True,
        ...     ugens_used=["SinOsc", "Resonz", "EnvGen", "Out"],
        ...     category="bass",
        ...     tags=["acid", "303", "classic"],
        ...     source_code="SynthDef(\\tb303, { ... })",
        ...     controls=[
        ...         SynthControl(
        ...             name="cutoff",
        ...             default_value=1200.0,
        ...             spec=ControlSpec(
        ...                 min=200.0,
        ...                 max=4000.0,
        ...                 default=1200.0,
        ...                 warp="exp",
        ...                 step=1.0,
        ...             ),
        ...         ),
        ...         SynthControl(
        ...             name="resonance",
        ...             default_value=0.7,
        ...             spec=ControlSpec(
        ...                 min=0.0,
        ...                 max=1.0,
        ...                 default=0.7,
        ...                 warp="linear",
        ...                 step=0.01,
        ...             ),
        ...         ),
        ...     ],
        ... )
    """
    # Identity (required)
    id: str  # Format: "synt_{hash[:8]}"
    name: str  # SynthDef name (from SynthDef(\name, ...))
    file_path: str  # Absolute path to .scd file
    file_hash: str  # SHA256 hash for deduplication

    # Characteristics (required)
    num_channels: int  # Number of output channels
    has_gate: bool  # Whether synth has gate parameter (for note off)
    has_envelope: bool  # Whether synth uses EnvGen
    ugens_used: list[str]  # List of UGen class names

    # Categorization (optional)
    category: Optional[str]  # Category: bass, lead, pad, drum, fx
    tags: list[str]  # User-defined tags
    similar_to: list[str]  # Similar synth IDs (from embedding similarity)

    # Source (required)
    source_code: str  # Full .scd file contents
    controls: list[SynthControl]  # Extracted control parameters


class SynthDefParser(Protocol):
    """Interface for parsing SuperCollider SynthDef files.

    Extracts controls, UGens, and metadata from .scd files using sclang.
    """

    def parse(
        self,
        file_path: str,
        timeout: int = 5,
    ) -> SynthDefMetadata:
        """Parse a SynthDef file and extract metadata.

        Uses subprocess to run sclang with shell=False and timeout for safety.
        Falls back to binary parser if sclang fails.

        Args:
            file_path: Absolute path to .scd file
            timeout: Maximum time to wait for sclang (seconds)

        Returns:
            Complete SynthDef metadata

        Raises:
            FileNotFoundError: If file_path does not exist
            ParseError: If file cannot be parsed (invalid syntax)
            SubprocessTimeoutError: If sclang exceeds timeout

        Example:
            >>> parser = SynthDefParser()
            >>> metadata = parser.parse("/synths/tb303.scd", timeout=5)
            >>> metadata['name']
            "tb303"
            >>> len(metadata['controls'])
            7
            >>> metadata['controls'][0]['name']
            "cutoff"
        """
        ...

    def parse_batch(
        self,
        file_paths: list[str],
        timeout: int = 5,
    ) -> list[SynthDefMetadata]:
        """Parse multiple SynthDef files in batch.

        More efficient than individual parse() calls for many files.

        Args:
            file_paths: List of absolute paths to .scd files
            timeout: Maximum time per file (seconds)

        Returns:
            List of SynthDef metadata in same order as input

        Raises:
            FileNotFoundError: If any file does not exist (fails fast)
            ParseError: On first parse failure (no partial results)

        Example:
            >>> parser = SynthDefParser()
            >>> files = ["/synths/tb303.scd", "/synths/juno.scd"]
            >>> results = parser.parse_batch(files, timeout=5)
            >>> len(results)
            2
        """
        ...

    def validate_path(self, file_path: str) -> bool:
        """Validate that file path is safe and exists.

        Checks for:
        - File existence
        - .scd extension
        - No path traversal (../)
        - Readable permissions

        Args:
            file_path: Path to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> parser = SynthDefParser()
            >>> parser.validate_path("/synths/tb303.scd")
            True
            >>> parser.validate_path("/etc/passwd")  # Wrong extension
            False
            >>> parser.validate_path("../../etc/passwd.scd")  # Traversal
            False
        """
        ...

    def extract_controls(self, source_code: str) -> list[SynthControl]:
        """Extract control parameters from SynthDef source code.

        Parses arg declarations and infers specs from usage.

        Args:
            source_code: SuperCollider source code

        Returns:
            List of extracted controls

        Example:
            >>> code = '''
            ... SynthDef(\\tb303, { |cutoff=1200, resonance=0.7|
            ...     var sig = Saw.ar(freq);
            ...     sig = Resonz.ar(sig, cutoff, 1/resonance);
            ...     Out.ar(0, sig);
            ... })
            ... '''
            >>> controls = parser.extract_controls(code)
            >>> controls
            [
                SynthControl(name="cutoff", default_value=1200.0, ...),
                SynthControl(name="resonance", default_value=0.7, ...),
            ]
        """
        ...

    def extract_ugens(self, source_code: str) -> list[str]:
        """Extract UGen class names from source code.

        Finds all UGen.ar() and UGen.kr() calls.

        Args:
            source_code: SuperCollider source code

        Returns:
            List of unique UGen class names

        Example:
            >>> code = '''
            ... SynthDef(\\tb303, {
            ...     var sig = Saw.ar(440);
            ...     sig = Resonz.ar(sig, 1200);
            ...     Out.ar(0, sig);
            ... })
            ... '''
            >>> ugens = parser.extract_ugens(code)
            >>> ugens
            ["Saw", "Resonz", "Out"]
        """
        ...

    def infer_category(self, metadata: SynthDefMetadata) -> str:
        """Infer synth category from UGens and controls.

        Categorization rules:
        - bass: Low-pass filter + low frequency range
        - lead: High resonance + envelope
        - pad: Long envelope + multiple oscillators
        - drum: Noise + short envelope
        - fx: No oscillators, effect UGens only

        Args:
            metadata: Parsed SynthDef metadata

        Returns:
            Category string

        Example:
            >>> metadata = SynthDefMetadata(
            ...     ugens_used=["Saw", "Resonz", "EnvGen"],
            ...     controls=[
            ...         SynthControl(name="cutoff", default_value=1200, ...),
            ...     ],
            ...     ...
            ... )
            >>> category = parser.infer_category(metadata)
            >>> category
            "bass"
        """
        ...


class SynthDefStore(Protocol):
    """Interface for SynthDef storage operations.

    Similar to SampleStore but for synthesizer definitions.
    """

    def add(self, synthdef: SynthDefMetadata) -> str:
        """Add SynthDef to database.

        Args:
            synthdef: Complete SynthDef metadata

        Returns:
            Synth ID (format: "synt_{hash[:8]}")

        Raises:
            DuplicateSynthError: If SynthDef with same name already exists

        Example:
            >>> synthdef = SynthDefMetadata(
            ...     name="tb303",
            ...     file_path="/synths/tb303.scd",
            ...     file_hash="abc123",
            ...     num_channels=1,
            ...     has_gate=True,
            ...     has_envelope=True,
            ...     ugens_used=["Saw", "Resonz", "EnvGen", "Out"],
            ...     source_code="SynthDef(...)",
            ...     controls=[...],
            ... )
            >>> synth_id = store.add(synthdef)
            >>> synth_id
            "synt_abc123"
        """
        ...

    def get(self, synth_id: str) -> Optional[SynthDefMetadata]:
        """Retrieve SynthDef by ID.

        Args:
            synth_id: Synth ID (format: "synt_{hash[:8]}")

        Returns:
            SynthDef metadata if found, None otherwise

        Example:
            >>> synthdef = store.get("synt_abc123")
            >>> synthdef['name']
            "tb303"
            >>> store.get("synt_nonexistent")
            None
        """
        ...

    def get_by_name(self, name: str) -> Optional[SynthDefMetadata]:
        """Retrieve SynthDef by name.

        Args:
            name: SynthDef name

        Returns:
            SynthDef metadata if found, None otherwise

        Example:
            >>> synthdef = store.get_by_name("tb303")
            >>> synthdef['id']
            "synt_abc123"
        """
        ...

    def search(
        self,
        category: Optional[str] = None,
        has_gate: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SynthDefMetadata]:
        """Search SynthDefs with filters.

        Args:
            category: Filter by category (bass, lead, pad, drum, fx)
            has_gate: Filter by gate presence
            tags: Filter by tags (matches if ANY tag present)
            limit: Maximum results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of matching SynthDefs

        Example:
            >>> # Find bass synths with gate
            >>> results = store.search(
            ...     category="bass",
            ...     has_gate=True,
            ...     limit=10,
            ... )
            >>> len(results) <= 10
            True
        """
        ...

    def update(self, synth_id: str, updates: dict) -> bool:
        """Update SynthDef fields.

        Args:
            synth_id: Synth ID to update
            updates: Dictionary of field names and new values

        Returns:
            True if updated, False if not found

        Example:
            >>> success = store.update(
            ...     "synt_abc123",
            ...     {"category": "lead", "tags": ["acid", "303"]},
            ... )
            >>> success
            True
        """
        ...

    def delete(self, synth_id: str) -> bool:
        """Delete SynthDef from database.

        Args:
            synth_id: Synth ID to delete

        Returns:
            True if deleted, False if not found

        Example:
            >>> success = store.delete("synt_abc123")
            >>> success
            True
        """
        ...
