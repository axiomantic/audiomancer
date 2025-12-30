"""Tests for configuration system."""
import pytest
from pathlib import Path
from audiomancer.config import (
    AudiomancerConfig,
    StorageConfig,
    load_config,
    save_config,
    get_config_dir,
    get_data_dir,
    get_config_path,
    deep_merge_dicts,
    find_project_config,
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


class TestConfigHelpers:
    """Tests for config helper utilities."""

    def test_get_config_dir_default(self, tmp_path, monkeypatch):
        """Default config dir is ~/.config/audiomancer."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_config_dir() == tmp_path / ".config" / "audiomancer"

    def test_get_config_dir_respects_xdg(self, tmp_path, monkeypatch):
        """XDG_CONFIG_HOME is respected."""
        custom_config = tmp_path / "custom_config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config))
        assert get_config_dir() == custom_config / "audiomancer"

    def test_get_data_dir(self, tmp_path, monkeypatch):
        """Data dir is config_dir/data."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_data_dir() == tmp_path / ".config" / "audiomancer" / "data"

    def test_get_config_path(self, tmp_path, monkeypatch):
        """Config path is config_dir/config.yaml."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_config_path() == tmp_path / ".config" / "audiomancer" / "config.yaml"


class TestDeepMergeDicts:
    """Tests for deep_merge_dicts utility."""

    def test_deep_merge_empty_dicts(self):
        """Merging empty dicts should return empty dict."""
        result = deep_merge_dicts({}, {})
        assert result == {}

    def test_deep_merge_flat_dicts(self):
        """Flat dicts should merge with override taking precedence."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge_dicts(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested_dicts(self):
        """Nested dicts should merge recursively."""
        base = {
            "level1": {
                "a": 1,
                "b": 2,
                "level2": {
                    "x": 10,
                    "y": 20
                }
            }
        }
        override = {
            "level1": {
                "b": 99,
                "level2": {
                    "y": 99,
                    "z": 30
                },
                "c": 3
            }
        }
        result = deep_merge_dicts(base, override)
        assert result == {
            "level1": {
                "a": 1,
                "b": 99,
                "c": 3,
                "level2": {
                    "x": 10,
                    "y": 99,
                    "z": 30
                }
            }
        }

    def test_deep_merge_override_primitive(self):
        """Override should replace primitive values completely."""
        base = {"config": {"value": 100}}
        override = {"config": {"value": 200}}
        result = deep_merge_dicts(base, override)
        assert result == {"config": {"value": 200}}

    def test_deep_merge_none_values(self):
        """None values in override should be preserved."""
        base = {"a": 1, "b": 2}
        override = {"b": None, "c": 3}
        result = deep_merge_dicts(base, override)
        assert result == {"a": 1, "b": None, "c": 3}


class TestAudiomancerConfigPrivateAttrs:
    """Tests for AudiomancerConfig private attributes."""

    def test_config_project_root_default_none(self):
        """_project_root should default to None."""
        config = AudiomancerConfig()
        assert config._project_root is None

    def test_config_project_root_set_via_private_attr(self):
        """_project_root should be settable and retrievable."""
        config = AudiomancerConfig()
        test_path = Path("/test/project/root")
        config._project_root = test_path
        assert config._project_root == test_path

    def test_config_project_root_not_serialized(self):
        """_project_root should not appear in model_dump (private attr)."""
        config = AudiomancerConfig()
        config._project_root = Path("/test/project/root")

        serialized = config.model_dump()

        # Private attributes should NOT be in serialization
        assert "_project_root" not in serialized
        assert "project_root" not in serialized


class TestFindProjectConfig:
    """Tests for find_project_config."""

    def test_find_project_config_in_cwd(self, tmp_path):
        """Should find .audiomancer.yaml in current working directory."""
        config_file = tmp_path / ".audiomancer.yaml"
        config_file.write_text("# test config")

        result = find_project_config(start_path=tmp_path)

        assert result == config_file

    def test_find_project_config_in_parent(self, tmp_path):
        """Should find .audiomancer.yaml in parent directory."""
        config_file = tmp_path / ".audiomancer.yaml"
        config_file.write_text("# test config")

        # Start from nested subdirectory
        nested = tmp_path / "subdir" / "nested"
        nested.mkdir(parents=True)

        result = find_project_config(start_path=nested)

        assert result == config_file

    def test_find_project_config_not_found(self, tmp_path):
        """Should return None when .audiomancer.yaml not found."""
        # No config file created

        result = find_project_config(start_path=tmp_path)

        assert result is None

    def test_find_project_config_max_depth(self, tmp_path):
        """Should respect max_depth limit when searching upward."""
        # Create config file 5 levels up
        config_file = tmp_path / ".audiomancer.yaml"
        config_file.write_text("# test config")

        # Create deeply nested directory
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)

        # Search with max_depth=3 (should not find it)
        result = find_project_config(start_path=deep, max_depth=3)
        assert result is None

        # Search with max_depth=10 (should find it)
        result = find_project_config(start_path=deep, max_depth=10)
        assert result == config_file


class TestMergeConfig:
    """Tests for merge_config function."""

    def test_merge_config_builtin_only(self):
        """Builtin config only (no global or project overrides)."""
        from audiomancer.config import merge_config

        builtin = {
            "analysis": {"max_file_size_mb": 50},
            "library": {"copy_workers": 16}
        }

        result = merge_config(builtin)

        assert result.analysis.max_file_size_mb == 50
        assert result.library.copy_workers == 16
        assert result._project_root is None

    def test_merge_config_global_overrides_builtin(self):
        """Global config overrides builtin defaults."""
        from audiomancer.config import merge_config

        builtin = {
            "analysis": {"max_file_size_mb": 50},
            "library": {"copy_workers": 16}
        }
        global_config = {
            "analysis": {"max_file_size_mb": 100}
        }

        result = merge_config(builtin, global_config=global_config)

        # Global overrides builtin
        assert result.analysis.max_file_size_mb == 100
        # Builtin value preserved where not overridden
        assert result.library.copy_workers == 16
        assert result._project_root is None

    def test_merge_config_project_overrides_all(self):
        """Project config takes precedence over global and builtin."""
        from audiomancer.config import merge_config

        builtin = {
            "analysis": {"max_file_size_mb": 50},
            "library": {"copy_workers": 16, "max_file_size_mb": 10}
        }
        global_config = {
            "analysis": {"max_file_size_mb": 100}
        }
        project_config = {
            "library": {"max_file_size_mb": 20}
        }

        result = merge_config(
            builtin,
            global_config=global_config,
            project_config=project_config
        )

        # Project overrides global
        assert result.library.max_file_size_mb == 20
        # Global overrides builtin
        assert result.analysis.max_file_size_mb == 100
        # Builtin preserved where not overridden
        assert result.library.copy_workers == 16

    def test_merge_config_sets_project_root(self):
        """merge_config sets _project_root when project_root provided."""
        from audiomancer.config import merge_config

        builtin = {
            "analysis": {"max_file_size_mb": 50}
        }
        project_root = Path("/test/project/root")

        result = merge_config(builtin, project_root=project_root)

        assert result._project_root == project_root
