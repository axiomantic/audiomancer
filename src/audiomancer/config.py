"""Configuration system for audiomancer."""

from pathlib import Path
from typing import Optional, Dict, Any
import os
import yaml
from pydantic import BaseModel, Field, field_validator, PrivateAttr
from pydantic_settings import BaseSettings


class SampleSourceConfig(BaseModel):
    """Configuration for sample source directories."""
    paths: list[Path] = Field(default_factory=list)

    @field_validator("paths", mode="before")
    @classmethod
    def expand_paths(cls, v: list) -> list[Path]:
        return [Path(p).expanduser().resolve() for p in v]


class SynthSourceConfig(BaseModel):
    """Configuration for synth source directories."""
    paths: list[Path] = Field(default_factory=list)

    @field_validator("paths", mode="before")
    @classmethod
    def expand_paths(cls, v: list) -> list[Path]:
        return [Path(p).expanduser().resolve() for p in v]


class SourcesConfig(BaseModel):
    """Configuration for all source directories."""
    samples: SampleSourceConfig = Field(default_factory=SampleSourceConfig)
    synths: SynthSourceConfig = Field(default_factory=SynthSourceConfig)


class AnalysisConfig(BaseModel):
    """Configuration for audio analysis."""
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    skip_patterns: list[str] = Field(default_factory=lambda: ["*.asd", "*.pkf"])
    embedding_dim: int = Field(default=128, ge=64, le=512)

    # Essentia model paths (relative to models_path)
    effnet_model: str = "discogs-effnet-bs64-1.pb"


class SuperColliderConfig(BaseModel):
    """Configuration for SuperCollider integration."""
    sclang_path: Optional[Path] = None
    boot_server: bool = False
    timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)

    @field_validator("sclang_path", mode="before")
    @classmethod
    def find_sclang(cls, v: Optional[str]) -> Optional[Path]:
        if v:
            return Path(v).expanduser().resolve()
        # Auto-detect sclang
        for path in [
            "/usr/local/bin/sclang",
            "/usr/bin/sclang",
            "/Applications/SuperCollider.app/Contents/MacOS/sclang",
        ]:
            if Path(path).exists():
                return Path(path)
        return None


class StorageConfig(BaseModel):
    """Configuration for data storage."""
    db_path: Path = Field(
        default_factory=lambda: Path("~/.local/share/audiomancer/audiomancer.db").expanduser().resolve()
    )
    embeddings_path: Path = Field(
        default_factory=lambda: Path("~/.local/share/audiomancer/embeddings").expanduser().resolve()
    )
    models_path: Path = Field(
        default_factory=lambda: Path("~/.local/share/audiomancer/models").expanduser().resolve()
    )

    @field_validator("db_path", "embeddings_path", "models_path", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()


class GenerationConfig(BaseModel):
    """Configuration for pattern/synth generation."""
    default_bpm: float = Field(default=120.0, ge=60.0, le=200.0)
    default_bars: int = Field(default=4, ge=1, le=32)
    inference_timeout: float = Field(default=30.0, ge=5.0, le=120.0)


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = Field(default="WARNING")
    file_level: str = Field(default="DEBUG")
    log_dir: Path = Field(
        default_factory=lambda: Path("~/.local/share/audiomancer/logs").expanduser().resolve()
    )
    max_days: int = Field(default=7, ge=1, le=30)

    @field_validator("log_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    @field_validator("level", "file_level", mode="before")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid}")
        return v.upper()


class LibraryConfig(BaseModel):
    """Configuration for sample library management.

    The library system manages sample packs from a source (e.g., Google Drive)
    to a local project with the structure:
        {project_root}/samples/  - Local cache
        {project_root}/library/  - Active samples (symlinks)
    """
    # Source directory (e.g., Google Drive samples folder)
    source_dir: Path = Field(
        default_factory=lambda: Path("~/Music/Samples").expanduser().resolve()
    )

    # Project root - expects samples/ and library/ subdirectories
    project_root: Path = Field(
        default_factory=lambda: Path("~/Development/my-music").expanduser().resolve()
    )

    # Auto-analyze samples when enabling packs
    auto_analyze: bool = True

    # Skip files larger than this (MB), 0 = no limit
    max_file_size_mb: int = Field(default=10, ge=0, le=500)

    # Number of parallel copy workers
    copy_workers: int = Field(default=16, ge=1, le=64)

    @field_validator("source_dir", "project_root", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    @property
    def samples_dir(self) -> Path:
        """Local cache directory for copied samples."""
        return self.project_root / "samples"

    @property
    def library_dir(self) -> Path:
        """Active samples directory (symlinks to samples/)."""
        return self.project_root / "library"


class AudiomancerConfig(BaseModel):
    """Root configuration for audiomancer."""
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    supercollider: SuperColliderConfig = Field(default_factory=SuperColliderConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    library: LibraryConfig = Field(default_factory=LibraryConfig)

    _project_root: Optional[Path] = PrivateAttr(default=None)


# Builtin default values for three-tier config system
BUILTIN_DEFAULTS: Dict[str, Any] = {
    "sources": {
        "samples": {"paths": []},
        "synths": {"paths": []}
    },
    "analysis": {
        "max_file_size_mb": 50,
        "skip_patterns": ["*.asd", "*.pkf"],
        "embedding_dim": 128,
        "effnet_model": "discogs-effnet-bs64-1.pb"
    },
    "supercollider": {
        "sclang_path": None,
        "boot_server": False,
        "timeout_seconds": 5.0
    },
    "storage": {
        "db_path": "~/.local/share/audiomancer/audiomancer.db",
        "embeddings_path": "~/.local/share/audiomancer/embeddings",
        "models_path": "~/.local/share/audiomancer/models"
    },
    "generation": {
        "default_bpm": 120.0,
        "default_bars": 4,
        "inference_timeout": 30.0
    },
    "logging": {
        "level": "WARNING",
        "file_level": "DEBUG",
        "log_dir": "~/.local/share/audiomancer/logs",
        "max_days": 7
    },
    "library": {
        "source_dir": "~/Music/Samples",
        "project_root": "~/Development/my-music",
        "auto_analyze": True,
        "max_file_size_mb": 10,
        "copy_workers": 16
    }
}


def deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)

    Returns:
        Merged dictionary where override values take precedence.
        Nested dicts are merged recursively.

    Example:
        >>> base = {"a": 1, "b": {"x": 10}}
        >>> override = {"b": {"y": 20}, "c": 3}
        >>> deep_merge_dicts(base, override)
        {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def get_config_dir() -> Path:
    """Get audiomancer config directory (respects XDG_CONFIG_HOME)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "audiomancer"
    return Path.home() / ".config" / "audiomancer"


def get_data_dir() -> Path:
    """Get audiomancer data directory."""
    return get_config_dir() / "data"


def get_config_path() -> Path:
    """Get configuration file path."""
    return get_config_dir() / "config.yaml"


def load_config(project_path: Optional[Path] = None) -> AudiomancerConfig:
    """
    Load configuration using three-tier inheritance: builtin <- global <- project.

    Merge order (later overrides earlier):
    1. BUILTIN_DEFAULTS - Default values
    2. Global config from ~/.config/audiomancer/config.yaml (if exists)
    3. Project config from .audiomancer.yaml (if found)

    Args:
        project_path: Optional path to project directory containing .audiomancer.yaml.
                     If not provided, searches upward from current directory.

    Returns:
        AudiomancerConfig instance with merged configuration

    Raises:
        ConfigError: If config files exist but are invalid

    Example:
        >>> # Load with auto-detection
        >>> config = load_config()
        >>> # Load from specific project
        >>> config = load_config(Path("/path/to/project"))
    """
    from audiomancer.errors import ConfigError

    # Start with builtin defaults
    merged_config = BUILTIN_DEFAULTS.copy()

    # Load global config if it exists
    global_config_path = get_config_path()
    global_config_data: Optional[Dict[str, Any]] = None
    if global_config_path.exists():
        try:
            with open(global_config_path) as f:
                global_config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in global config file: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load global config: {e}")

    # Determine project config path
    project_config_path: Optional[Path] = None
    project_root: Optional[Path] = None

    if project_path is not None:
        # Explicit project path provided
        project_root = project_path.resolve()
        candidate = project_root / ".audiomancer.yaml"
        if candidate.exists():
            project_config_path = candidate
    else:
        # Auto-detect project config
        found_config = find_project_config()
        if found_config is not None:
            project_config_path = found_config
            project_root = found_config.parent

    # Load project config if found
    project_config_data: Optional[Dict[str, Any]] = None
    if project_config_path is not None:
        try:
            with open(project_config_path) as f:
                project_config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in project config file: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load project config: {e}")

    # Merge all tiers using merge_config
    return merge_config(
        builtin=merged_config,
        global_config=global_config_data,
        project_config=project_config_data,
        project_root=project_root
    )


def save_config(config: AudiomancerConfig, config_path: Optional[Path] = None) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Optional path. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict, handling Path objects
    def path_representer(dumper, data):
        return dumper.represent_str(str(data))

    yaml.add_representer(Path, path_representer)

    with open(path, "w") as f:
        yaml.dump(config.model_dump(mode="json"), f, default_flow_style=False)


def ensure_directories(config: AudiomancerConfig) -> None:
    """
    Ensure all configured directories exist.

    Raises:
        ConfigError: If directories cannot be created
    """
    from audiomancer.errors import ConfigError

    directories = [
        config.storage.db_path.parent,
        config.storage.embeddings_path,
        config.storage.models_path,
        config.logging.log_dir,
        config.library.samples_dir,
        config.library.library_dir,
    ]

    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ConfigError(
                f"Cannot create directory: {directory}",
                {"path": str(directory), "error": "Permission denied"}
            )


def find_project_config(start_path: Optional[Path] = None, max_depth: int = 10) -> Optional[Path]:
    """
    Search upward from start_path for .audiomancer.yaml project config file.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.
        max_depth: Maximum number of parent directories to search. Defaults to 10.

    Returns:
        Path to .audiomancer.yaml if found, None otherwise.

    Example:
        >>> config_path = find_project_config()
        >>> if config_path:
        ...     config = load_config(config_path)
    """
    current = (start_path or Path.cwd()).resolve()

    for _ in range(max_depth):
        config_file = current / ".audiomancer.yaml"
        if config_file.exists():
            return config_file

        # Check if we've reached the root
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def merge_config(
    builtin: Dict[str, Any],
    global_config: Optional[Dict[str, Any]] = None,
    project_config: Optional[Dict[str, Any]] = None,
    project_root: Optional[Path] = None
) -> AudiomancerConfig:
    """
    Merge three-tier config hierarchy: builtin ← global ← project.

    Merge order (later overrides earlier):
    1. builtin (default values)
    2. global_config (from ~/.config/audiomancer/config.yaml)
    3. project_config (from .audiomancer.yaml)

    Args:
        builtin: Base configuration dictionary with default values
        global_config: Optional global config overrides
        project_config: Optional project-specific config overrides
        project_root: Optional project root path (sets _project_root)

    Returns:
        AudiomancerConfig instance with merged configuration

    Example:
        >>> builtin = {"analysis": {"max_file_size_mb": 50}}
        >>> global_cfg = {"analysis": {"max_file_size_mb": 100}}
        >>> config = merge_config(builtin, global_config=global_cfg)
        >>> config.analysis.max_file_size_mb
        100
    """
    # Start with builtin
    merged = builtin.copy()

    # Apply global overrides
    if global_config:
        merged = deep_merge_dicts(merged, global_config)

    # Apply project overrides
    if project_config:
        merged = deep_merge_dicts(merged, project_config)

    # Create validated config
    config = AudiomancerConfig.model_validate(merged)

    # Set project root if provided
    if project_root is not None:
        config._project_root = project_root

    return config
