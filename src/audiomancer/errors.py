"""
Error hierarchy for the audiomancer project.

All exceptions inherit from AudiomancerError and include structured context
via the `details` dictionary for debugging and actionable error messages.
"""

from typing import Optional, Dict, Any


class AudiomancerError(Exception):
    """
    Base exception for all audiomancer errors.

    All audiomancer exceptions include a `details` dictionary for structured
    context that can be serialized to JSON for logging or MCP error responses.

    Attributes:
        details: Dictionary containing error context and debugging information

    Example:
        >>> raise AudiomancerError(
        ...     "Operation failed",
        ...     details={"path": "/tmp/sample.wav", "reason": "file locked"}
        ... )
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize exception to dictionary for JSON responses.

        Returns:
            Dictionary with error type, message, and details

        Example:
            >>> try:
            ...     raise ConfigError("Invalid config", details={"key": "sample_rate"})
            ... except AudiomancerError as e:
            ...     error_dict = e.to_dict()
            ...     # {"type": "ConfigError", "message": "Invalid config",
            ...     #  "details": {"key": "sample_rate"}}
        """
        return {
            "type": self.__class__.__name__,
            "message": str(self.args[0]) if self.args else "",
            "details": self.details
        }


class ConfigError(AudiomancerError):
    """
    Configuration file or validation errors.

    Raised when config.yaml is missing, malformed, or contains invalid values.

    Example:
        >>> raise ConfigError(
        ...     "Missing required configuration key",
        ...     details={"key": "sample_rate", "config_path": "~/.audiomancer/config.yaml"}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "key" in self.details:
            msg += f"\nMissing/invalid key: {self.details['key']}"
        if "config_path" in self.details:
            msg += f"\nConfig file: {self.details['config_path']}"
        return msg


class StorageError(AudiomancerError):
    """
    Database or storage operation errors.

    Base class for all SQLite/storage-related errors.

    Example:
        >>> raise StorageError(
        ...     "Database query failed",
        ...     details={"query": "INSERT INTO samples...", "error": "unique constraint"}
        ... )
    """
    pass


class SampleNotFoundError(StorageError):
    """
    Requested sample does not exist in the database.

    Example:
        >>> raise SampleNotFoundError(
        ...     "Sample not found",
        ...     details={"sample_id": "abc123", "query": "SELECT * FROM samples WHERE id=?"}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "sample_id" in self.details:
            msg += f"\nSample ID: {self.details['sample_id']}"
        if "path" in self.details:
            msg += f"\nPath: {self.details['path']}"
        msg += "\nTip: Run 'audiomancer import' to add samples"
        return msg


class DuplicateSampleError(StorageError):
    """
    Sample with same content hash already exists in database.

    Raised during import when a sample's SHA-256 hash matches an existing entry.
    The `existing_id` attribute contains the ID of the duplicate sample.

    Attributes:
        existing_id: Database ID of the existing duplicate sample

    Example:
        >>> raise DuplicateSampleError(
        ...     existing_id="def456",
        ...     path="/new/location/kick.wav"
        ... )
    """

    def __init__(self, existing_id: str, path: str, details: Optional[Dict[str, Any]] = None):
        merged_details = details or {}
        merged_details["existing_id"] = existing_id
        merged_details["path"] = path

        super().__init__(
            f"Sample already exists: {path}",
            details=merged_details
        )
        self.existing_id = existing_id

    def __str__(self) -> str:
        msg = super().__str__()
        msg += f"\nExisting sample ID: {self.existing_id}"
        msg += f"\nAttempted path: {self.details.get('path', 'unknown')}"
        if "existing_path" in self.details:
            msg += f"\nExisting path: {self.details['existing_path']}"
        msg += "\nTip: Use --skip-duplicates flag or remove duplicate file"
        return msg


class AnalysisError(AudiomancerError):
    """
    Audio analysis errors.

    Base class for errors during feature extraction or audio analysis.

    Example:
        >>> raise AnalysisError(
        ...     "Spectral analysis failed",
        ...     details={"path": "sample.wav", "stage": "FFT computation"}
        ... )
    """
    pass


class UnsupportedFormatError(AnalysisError):
    """
    Audio file format not supported by librosa.

    Example:
        >>> raise UnsupportedFormatError(
        ...     "Cannot decode audio file",
        ...     details={"path": "sample.mp3", "format": "mp3", "error": "codec not available"}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "path" in self.details:
            msg += f"\nFile: {self.details['path']}"
        if "format" in self.details:
            msg += f"\nFormat: {self.details['format']}"
        msg += "\nTip: Convert to WAV, FLAC, or another format supported by librosa/soundfile"
        return msg


class AnalysisFailedError(AnalysisError):
    """
    Audio analysis could not be completed.

    Raised when feature extraction fails for reasons other than format issues
    (e.g., corrupted file, insufficient data, numerical errors).

    Example:
        >>> raise AnalysisFailedError(
        ...     "Pitch detection failed",
        ...     details={"path": "sample.wav", "reason": "signal too noisy", "snr": -15}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "path" in self.details:
            msg += f"\nFile: {self.details['path']}"
        if "reason" in self.details:
            msg += f"\nReason: {self.details['reason']}"
        if "stage" in self.details:
            msg += f"\nFailed at: {self.details['stage']}"
        return msg


class GenerationError(AudiomancerError):
    """
    Pattern or synth generation errors.

    Base class for errors during ML-based pattern generation or synthesis.

    Example:
        >>> raise GenerationError(
        ...     "Pattern generation failed",
        ...     details={"model": "music_vae", "error": "invalid input dimensions"}
        ... )
    """
    pass


class ModelLoadError(GenerationError):
    """
    ML model failed to load.

    Raised when a Magenta or other ML model cannot be loaded from disk or
    downloaded from remote.

    Example:
        >>> raise ModelLoadError(
        ...     "Model not found",
        ...     details={"name": "drums_4bar", "path": "~/.audiomancer/models/"}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "name" in self.details:
            msg += f"\nModel: {self.details['name']}"
        if "path" in self.details:
            msg += f"\nSearched at: {self.details['path']}"
        msg += "\nTip: Run 'audiomancer models download' or check model name spelling"
        return msg


class InferenceTimeoutError(GenerationError):
    """
    ML inference exceeded configured timeout.

    Example:
        >>> raise InferenceTimeoutError(
        ...     "Pattern generation timed out",
        ...     details={"model": "music_vae", "timeout_seconds": 30, "elapsed": 35.2}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "model" in self.details:
            msg += f"\nModel: {self.details['model']}"
        if "timeout_seconds" in self.details:
            msg += f"\nTimeout: {self.details['timeout_seconds']}s"
        if "elapsed" in self.details:
            msg += f"\nElapsed: {self.details['elapsed']:.1f}s"
        msg += "\nTip: Increase timeout in config.yaml or simplify generation parameters"
        return msg


class SynthDefError(AudiomancerError):
    """
    SynthDef parsing or compilation errors.

    Raised when a SuperCollider .scd file cannot be parsed, compiled, or contains
    dangerous operations.

    Example:
        >>> raise SynthDefError(
        ...     "Invalid SynthDef syntax",
        ...     details={"path": "synths/broken.scd", "error": "SyntaxError: line 12"}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "path" in self.details:
            msg += f"\nFile: {self.details['path']}"
        if "error" in self.details:
            msg += f"\nError: {self.details['error']}"
        if "line" in self.details:
            msg += f"\nLine: {self.details['line']}"
        msg += "\nTip: Check SynthDef syntax in SuperCollider IDE"
        return msg


class SuperColliderError(AudiomancerError):
    """
    SuperCollider subprocess errors.

    Base class for errors when interacting with sclang/scsynth processes.

    Example:
        >>> raise SuperColliderError(
        ...     "sclang process crashed",
        ...     details={"command": "sclang -D synth.scd", "exit_code": 1}
        ... )
    """
    pass


class SubprocessTimeoutError(SuperColliderError):
    """
    sclang subprocess call exceeded timeout.

    Example:
        >>> raise SubprocessTimeoutError(
        ...     "sclang compilation timed out",
        ...     details={"command": "sclang -D synth.scd", "timeout": 10, "elapsed": 12.3}
        ... )
    """

    def __str__(self) -> str:
        msg = super().__str__()
        if "command" in self.details:
            msg += f"\nCommand: {self.details['command']}"
        if "timeout" in self.details:
            msg += f"\nTimeout: {self.details['timeout']}s"
        if "elapsed" in self.details:
            msg += f"\nElapsed: {self.details['elapsed']:.1f}s"
        msg += "\nTip: Increase subprocess timeout in config.yaml or check for infinite loops"
        return msg
