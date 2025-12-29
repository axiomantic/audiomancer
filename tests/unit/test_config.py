"""Tests for configuration system."""
import pytest
from pathlib import Path
from audiomancer.config import (
    AudiomancerConfig,
    StorageConfig,
    load_config,
    save_config,
)


class TestAudiomancerConfig:
    """Tests for AudiomancerConfig."""

    def test_default_config(self):
        """Default config should have valid defaults."""
        config = AudiomancerConfig()
        assert config.analysis.max_file_size_mb == 50
        assert config.generation.default_bpm == 120.0

    def test_storage_paths_expanded(self):
        """Paths should be expanded from ~."""
        config = AudiomancerConfig()
        assert "~" not in str(config.storage.db_path)
        assert "~" not in str(config.storage.embeddings_path)
        assert "~" not in str(config.storage.models_path)

    def test_storage_paths_are_absolute(self):
        """All storage paths should be absolute."""
        config = AudiomancerConfig()
        assert config.storage.db_path.is_absolute()
        assert config.storage.embeddings_path.is_absolute()
        assert config.storage.models_path.is_absolute()

    def test_invalid_log_level_rejected(self):
        """Invalid log levels should raise error."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AudiomancerConfig(
                logging={"level": "INVALID"}
            )

    def test_negative_max_file_size_rejected(self):
        """Negative max file size should be rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AudiomancerConfig(
                analysis={"max_file_size_mb": -10}
            )

    def test_invalid_bpm_rejected(self):
        """Invalid BPM values should be rejected."""
        from pydantic import ValidationError

        # Too low
        with pytest.raises(ValidationError):
            AudiomancerConfig(
                generation={"default_bpm": 0}
            )

        # Too high
        with pytest.raises(ValidationError):
            AudiomancerConfig(
                generation={"default_bpm": 500}
            )

    def test_custom_storage_paths(self, temp_dir):
        """Custom storage paths should be respected."""
        config = AudiomancerConfig(
            storage=StorageConfig(
                db_path=temp_dir / "custom.db",
                embeddings_path=temp_dir / "embeddings",
                models_path=temp_dir / "models",
            )
        )
        # Paths are resolved, so compare resolved versions
        assert config.storage.db_path == (temp_dir / "custom.db").resolve()
        assert config.storage.embeddings_path == (temp_dir / "embeddings").resolve()

    def test_analysis_config_defaults(self):
        """Analysis config should have sensible defaults."""
        config = AudiomancerConfig()
        assert config.analysis.max_file_size_mb > 0
        assert config.analysis.embedding_dim > 0
        assert len(config.analysis.skip_patterns) > 0
        assert isinstance(config.analysis.effnet_model, str)

    def test_generation_config_defaults(self):
        """Generation config should have sensible defaults."""
        config = AudiomancerConfig()
        assert 60 <= config.generation.default_bpm <= 240
        assert config.generation.default_bars > 0
        assert config.generation.inference_timeout > 0

    def test_logging_config_defaults(self):
        """Logging config should have sensible defaults."""
        config = AudiomancerConfig()
        assert config.logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert config.logging.file_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert config.logging.max_days > 0


class TestConfigPersistence:
    """Tests for config save/load."""

    def test_save_and_load_roundtrip(self, temp_dir):
        """Config should survive save/load cycle."""
        config_path = temp_dir / "config.yaml"
        original = AudiomancerConfig()
        original.generation.default_bpm = 140.0

        save_config(original, config_path)
        loaded = load_config(config_path)

        assert loaded.generation.default_bpm == 140.0

    def test_save_creates_parent_directories(self, temp_dir):
        """Save should create parent directories if needed."""
        config_path = temp_dir / "nested" / "config.yaml"
        config = AudiomancerConfig()

        save_config(config, config_path)

        assert config_path.exists()
        assert config_path.parent.exists()

    def test_missing_config_returns_defaults(self, temp_dir):
        """Missing config file should return defaults."""
        config = load_config(temp_dir / "nonexistent.yaml")
        assert isinstance(config, AudiomancerConfig)
        assert config.analysis.max_file_size_mb == 50

    def test_load_preserves_all_sections(self, temp_dir):
        """Load should preserve all config sections."""
        config_path = temp_dir / "config.yaml"
        original = AudiomancerConfig()
        original.analysis.max_file_size_mb = 100
        original.generation.default_bpm = 140.0
        original.logging.level = "DEBUG"

        save_config(original, config_path)
        loaded = load_config(config_path)

        assert loaded.analysis.max_file_size_mb == 100
        assert loaded.generation.default_bpm == 140.0
        assert loaded.logging.level == "DEBUG"

    def test_partial_config_uses_defaults(self, temp_dir):
        """Partial config should fill missing values with defaults."""
        config_path = temp_dir / "config.yaml"

        # Write minimal config
        config_path.write_text("generation:\n  default_bpm: 150.0\n")

        loaded = load_config(config_path)

        # Custom value preserved
        assert loaded.generation.default_bpm == 150.0
        # Defaults filled in
        assert loaded.analysis.max_file_size_mb == 50

    def test_invalid_yaml_raises_error(self, temp_dir):
        """Invalid YAML should raise appropriate error."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("invalid: yaml: content: {")

        with pytest.raises(Exception):
            load_config(config_path)

    def test_config_with_comments_preserved(self, temp_dir):
        """Comments in config should not break loading."""
        config_path = temp_dir / "config.yaml"

        # Write config with comments
        config_path.write_text("""
# Analysis settings
analysis:
  max_file_size_mb: 100  # Maximum file size

# Generation settings
generation:
  default_bpm: 140.0  # Default tempo
""")

        loaded = load_config(config_path)
        assert loaded.analysis.max_file_size_mb == 100
        assert loaded.generation.default_bpm == 140.0


class TestStorageConfig:
    """Tests for StorageConfig."""

    def test_relative_paths_converted_to_absolute(self):
        """Relative paths should be converted to absolute."""
        config = StorageConfig(
            db_path=Path("relative/path.db"),
            embeddings_path=Path("relative/embeddings"),
            models_path=Path("relative/models"),
        )
        assert config.db_path.is_absolute()
        assert config.embeddings_path.is_absolute()
        assert config.models_path.is_absolute()

    def test_tilde_paths_expanded(self):
        """Paths with ~ should be expanded."""
        config = StorageConfig(
            db_path=Path("~/audiomancer/db.sqlite"),
            embeddings_path=Path("~/audiomancer/embeddings"),
            models_path=Path("~/audiomancer/models"),
        )
        assert "~" not in str(config.db_path)
        assert "~" not in str(config.embeddings_path)
        assert "~" not in str(config.models_path)

    def test_db_path_has_sqlite_extension(self):
        """Database path should end with .db or .sqlite."""
        config = StorageConfig()
        assert config.db_path.suffix in [".db", ".sqlite"]
