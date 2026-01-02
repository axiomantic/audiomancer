"""Type stubs for mido library."""

from typing import Any, BinaryIO, Literal, Optional, Union

class Message:
    """MIDI message."""

    type: str
    time: int
    note: int
    velocity: int
    channel: int

    def __init__(
        self,
        type: str,
        note: int = ...,
        velocity: int = ...,
        time: int = ...,
        channel: int = ...,
        **kwargs: Any,
    ) -> None: ...

class MetaMessage:
    """MIDI meta message."""

    type: str
    time: int
    tempo: int

    def __init__(
        self,
        type: str,
        tempo: int = ...,
        time: int = ...,
        **kwargs: Any,
    ) -> None: ...

class MidiTrack:
    """MIDI track."""

    def append(self, msg: Union[Message, MetaMessage]) -> None: ...
    def __iter__(self) -> Any: ...

class MidiFile:
    """MIDI file."""

    ticks_per_beat: int
    tracks: list[MidiTrack]
    type: int

    def __init__(
        self,
        filename: Optional[str] = None,
        file: Optional[BinaryIO] = None,
        type: int = 1,
        ticks_per_beat: int = 480,
        **kwargs: Any,
    ) -> None: ...

    def save(
        self,
        filename: Optional[str] = None,
        file: Optional[BinaryIO] = None,
    ) -> None: ...
