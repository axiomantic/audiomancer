"""MIDI conversion interfaces for audiomancer.

This module defines Protocol interfaces for converting between MIDI, TidalCycles,
and SuperCollider pattern formats.
"""

from typing import Literal, Optional, Protocol
from typing_extensions import TypedDict


# MIDI pitch to drum sample mapping (GM standard)
DRUM_MIDI_MAP: dict[int, str] = {
    # Kicks
    35: "bd",      # Acoustic Bass Drum
    36: "bd",      # Bass Drum 1
    # Snares
    38: "sn",      # Acoustic Snare
    40: "sn",      # Electric Snare
    # Hi-hats
    42: "hc",      # Closed Hi-Hat
    44: "hc",      # Pedal Hi-Hat
    46: "ho",      # Open Hi-Hat
    # Toms
    41: "lt",      # Low Floor Tom
    43: "lt",      # High Floor Tom
    45: "mt",      # Low Tom
    47: "mt",      # Low-Mid Tom
    48: "ht",      # Hi-Mid Tom
    50: "ht",      # High Tom
    # Cymbals
    49: "cc",      # Crash Cymbal 1
    51: "cr",      # Ride Cymbal 1
    52: "cc",      # Chinese Cymbal
    53: "cr",      # Ride Bell
    55: "cc",      # Splash Cymbal
    57: "cc",      # Crash Cymbal 2
    59: "cr",      # Ride Cymbal 2
    # Percussion
    37: "cp",      # Side Stick
    39: "cp",      # Hand Clap
    54: "perc",    # Tambourine
    56: "perc",    # Cowbell
    58: "perc",    # Vibraslap
    60: "perc",    # Hi Bongo
    61: "perc",    # Low Bongo
    62: "perc",    # Mute Hi Conga
    63: "perc",    # Open Hi Conga
    64: "perc",    # Low Conga
    65: "perc",    # High Timbale
    66: "perc",    # Low Timbale
    67: "perc",    # High Agogo
    68: "perc",    # Low Agogo
    69: "perc",    # Cabasa
    70: "perc",    # Maracas
    71: "perc",    # Short Whistle
    72: "perc",    # Long Whistle
    73: "perc",    # Short Guiro
    74: "perc",    # Long Guiro
    75: "perc",    # Claves
    76: "perc",    # Hi Wood Block
    77: "perc",    # Low Wood Block
    78: "perc",    # Mute Cuica
    79: "perc",    # Open Cuica
    80: "perc",    # Mute Triangle
    81: "perc",    # Open Triangle
}


class MidiNote(TypedDict, total=False):
    """A single MIDI note event.

    Example:
        >>> note = MidiNote(
        ...     pitch=36,      # MIDI note number (0-127)
        ...     start=0.0,     # Start time in seconds
        ...     end=0.25,      # End time in seconds
        ...     velocity=100,  # Velocity (0-127)
        ... )
    """
    pitch: int  # MIDI note number (0-127)
    start: float  # Start time in seconds
    end: float  # End time in seconds
    velocity: int  # Note velocity (0-127, 0=off)


class MidiTrack(TypedDict, total=False):
    """A MIDI track containing notes.

    Example:
        >>> track = MidiTrack(
        ...     notes=[
        ...         MidiNote(pitch=36, start=0.0, end=0.25, velocity=100),
        ...         MidiNote(pitch=38, start=0.5, end=0.75, velocity=80),
        ...     ],
        ...     channel=0,
        ...     name="Drums",
        ... )
    """
    notes: list[MidiNote]  # Notes in this track
    channel: int  # MIDI channel (0-15)
    name: str  # Track name


class MidiData(TypedDict, total=False):
    """Complete MIDI file data.

    Example:
        >>> midi = MidiData(
        ...     tracks=[
        ...         MidiTrack(notes=[...], channel=0, name="Drums"),
        ...         MidiTrack(notes=[...], channel=1, name="Bass"),
        ...     ],
        ...     tempo=120.0,
        ...     time_signature=(4, 4),
        ...     ticks_per_beat=480,
        ... )
    """
    tracks: list[MidiTrack]  # All tracks
    tempo: float  # Tempo in BPM
    time_signature: tuple[int, int]  # (numerator, denominator)
    ticks_per_beat: int  # MIDI resolution


class TidalPattern(TypedDict, total=False):
    """TidalCycles pattern in mininotation format.

    Example:
        >>> pattern = TidalPattern(
        ...     channel="d1",
        ...     pattern="bd ~ sn ~",
        ...     sample_mapping={36: "bd", 38: "sn"},
        ... )
    """
    channel: str  # Tidal channel (d1-d9)
    pattern: str  # Mininotation string
    sample_mapping: dict[int, str]  # MIDI pitch to sample name


class SCPattern(TypedDict, total=False):
    """SuperCollider Pbind pattern.

    Example:
        >>> pattern = SCPattern(
        ...     synth="tb303",
        ...     pbind_code='''
        ...         Pbind(
        ...             \\instrument, \\tb303,
        ...             \\midinote, Pseq([36, 38], inf),
        ...             \\dur, Pseq([0.5, 0.5], inf),
        ...             \\amp, Pseq([0.8, 0.6], inf),
        ...         )
        ...     ''',
        ... )
    """
    synth: str  # Synth name
    pbind_code: str  # Complete Pbind code


class MidiConverter(Protocol):
    """Interface for converting between MIDI and pattern formats.

    Supports bidirectional conversion between MIDI, TidalCycles, and
    SuperCollider patterns.
    """

    def midi_to_tidal(
        self,
        midi: MidiData,
        sample_map: Optional[dict[int, str]] = None,
        channel: str = "d1",
    ) -> TidalPattern:
        """Convert MIDI to TidalCycles mininotation.

        Algorithm:
        1. Quantize notes to 16th note grid
        2. Map MIDI pitch to sample name (using DRUM_MIDI_MAP or custom)
        3. Convert to mininotation:
           - Note on 16th → sample name
           - Rest on 16th → ~
           - Multiple notes → [sample1, sample2]
        4. Handle timing subdivisions (8ths, 16ths, triplets)

        Args:
            midi: MIDI data to convert
            sample_map: Custom pitch→sample mapping (uses DRUM_MIDI_MAP if None)
            channel: Tidal channel to target (d1-d9)

        Returns:
            TidalPattern with mininotation string

        Example:
            >>> midi = MidiData(
            ...     tracks=[MidiTrack(notes=[
            ...         MidiNote(pitch=36, start=0.0, end=0.25, velocity=100),
            ...         MidiNote(pitch=38, start=0.5, end=0.75, velocity=80),
            ...     ])],
            ...     tempo=120.0,
            ...     time_signature=(4, 4),
            ... )
            >>> pattern = converter.midi_to_tidal(midi, channel="d1")
            >>> pattern['pattern']
            "bd ~ sn ~"
            >>> pattern['sample_mapping']
            {36: "bd", 38: "sn"}
        """
        ...

    def tidal_to_midi(
        self,
        pattern: TidalPattern,
        bpm: float = 120.0,
        bars: int = 1,
    ) -> MidiData:
        """Convert TidalCycles pattern to MIDI.

        Inverse of midi_to_tidal(). Parses mininotation and generates MIDI notes.

        Args:
            pattern: TidalPattern to convert
            bpm: Tempo for MIDI output
            bars: Number of bars to generate

        Returns:
            MIDI data with notes

        Example:
            >>> pattern = TidalPattern(
            ...     channel="d1",
            ...     pattern="bd ~ sn ~",
            ...     sample_mapping={36: "bd", 38: "sn"},
            ... )
            >>> midi = converter.tidal_to_midi(pattern, bpm=120, bars=1)
            >>> len(midi['tracks'][0]['notes'])
            2
        """
        ...

    def midi_to_sc(
        self,
        midi: MidiData,
        synth: str = "default",
    ) -> SCPattern:
        """Convert MIDI to SuperCollider Pbind.

        Algorithm:
        1. Extract note pitches, durations, velocities from MIDI
        2. Generate Pbind with Pseq patterns
        3. Map velocity to amplitude (0-127 → 0.0-1.0)

        Args:
            midi: MIDI data to convert
            synth: SuperCollider synth name

        Returns:
            SCPattern with Pbind code

        Example:
            >>> midi = MidiData(...)
            >>> pattern = converter.midi_to_sc(midi, synth="tb303")
            >>> print(pattern['pbind_code'])
            Pbind(
                \\instrument, \\tb303,
                \\midinote, Pseq([36, 38, 36, 38], inf),
                \\dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                \\amp, Pseq([0.8, 0.6, 0.8, 0.6], inf),
            )
        """
        ...

    def sc_to_midi(
        self,
        pattern: SCPattern,
        bpm: float = 120.0,
    ) -> MidiData:
        """Convert SuperCollider Pbind to MIDI.

        Parses Pbind code and extracts note data.

        Args:
            pattern: SCPattern to convert
            bpm: Tempo for MIDI output

        Returns:
            MIDI data with notes

        Example:
            >>> pattern = SCPattern(
            ...     synth="tb303",
            ...     pbind_code="Pbind(...)",
            ... )
            >>> midi = converter.sc_to_midi(pattern, bpm=125)
            >>> midi['tempo']
            125.0
        """
        ...

    def load_midi_file(self, file_path: str) -> MidiData:
        """Load MIDI file from disk.

        Args:
            file_path: Path to .mid file

        Returns:
            Parsed MIDI data

        Raises:
            FileNotFoundError: If file does not exist
            MidiParseError: If file is not valid MIDI

        Example:
            >>> midi = converter.load_midi_file("/patterns/beat.mid")
            >>> midi['tempo']
            120.0
            >>> len(midi['tracks'])
            2
        """
        ...

    def save_midi_file(
        self,
        midi: MidiData,
        file_path: str,
    ) -> None:
        """Save MIDI data to disk.

        Args:
            midi: MIDI data to save
            file_path: Destination path for .mid file

        Raises:
            IOError: If file cannot be written

        Example:
            >>> midi = MidiData(...)
            >>> converter.save_midi_file(midi, "/patterns/beat.mid")
        """
        ...

    def quantize_midi(
        self,
        midi: MidiData,
        grid: Literal["8th", "16th", "32nd"] = "16th",
    ) -> MidiData:
        """Quantize MIDI notes to grid.

        Snaps note start times to nearest grid position.

        Args:
            midi: MIDI data to quantize
            grid: Quantization grid resolution

        Returns:
            Quantized MIDI data (new copy, original unchanged)

        Example:
            >>> midi = MidiData(...)
            >>> quantized = converter.quantize_midi(midi, grid="16th")
            >>> # All note starts now align to 16th notes
        """
        ...

    def transpose_midi(
        self,
        midi: MidiData,
        semitones: int,
    ) -> MidiData:
        """Transpose MIDI notes by semitones.

        Args:
            midi: MIDI data to transpose
            semitones: Number of semitones (positive = up, negative = down)

        Returns:
            Transposed MIDI data (new copy)

        Example:
            >>> midi = MidiData(...)
            >>> up_octave = converter.transpose_midi(midi, semitones=12)
            >>> down_fifth = converter.transpose_midi(midi, semitones=-7)
        """
        ...

    def change_tempo(
        self,
        midi: MidiData,
        new_bpm: float,
    ) -> MidiData:
        """Change MIDI tempo without affecting note timing.

        Adjusts note durations to maintain same musical rhythm at new tempo.

        Args:
            midi: MIDI data
            new_bpm: New tempo in BPM

        Returns:
            MIDI data with new tempo (new copy)

        Example:
            >>> midi = MidiData(tempo=120, ...)
            >>> faster = converter.change_tempo(midi, new_bpm=140)
            >>> faster['tempo']
            140.0
        """
        ...

    def merge_tracks(
        self,
        tracks: list[MidiTrack],
        tempo: float = 120.0,
    ) -> MidiData:
        """Merge multiple MIDI tracks into single MIDI file.

        Args:
            tracks: List of MIDI tracks to merge
            tempo: Tempo for merged file

        Returns:
            MIDI data with all tracks

        Example:
            >>> drums = MidiTrack(...)
            >>> bass = MidiTrack(...)
            >>> midi = converter.merge_tracks([drums, bass], tempo=125)
            >>> len(midi['tracks'])
            2
        """
        ...

    def split_by_channel(self, midi: MidiData) -> dict[int, MidiTrack]:
        """Split MIDI file into separate tracks by channel.

        Args:
            midi: MIDI data to split

        Returns:
            Dictionary mapping channel number to track

        Example:
            >>> midi = MidiData(...)
            >>> by_channel = converter.split_by_channel(midi)
            >>> drums = by_channel[9]  # Channel 10 (0-indexed = 9)
            >>> bass = by_channel[0]
        """
        ...
