"""Configuration system for audiomancer."""

from pathlib import Path
from typing import Optional
import os
import yaml
from pydantic import BaseModel, Field, field_validator
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
        default_factory=lambda: Path(
            "~/Library/CloudStorage/GoogleDrive-elijahr@gmail.com/"
            "My Drive/Manual Library/Music Production/Samples"
        ).expanduser().resolve()
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


def load_config(config_path: Optional[Path] = None) -> AudiomancerConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        AudiomancerConfig instance

    Raises:
        ConfigError: If config file exists but is invalid

    Example:
        >>> config = load_config()
        >>> config.storage.db_path
        PosixPath('/home/user/.local/share/audiomancer/audiomancer.db')
    """
    from audiomancer.errors import ConfigError

    path = config_path or get_config_path()

    if not path.exists():
        # Return defaults if no config file
        return AudiomancerConfig()

    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return AudiomancerConfig(**data)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}")


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
