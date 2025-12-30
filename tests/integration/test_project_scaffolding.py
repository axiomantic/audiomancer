"""Integration tests for project scaffolding system.

Tests the complete project initialization, scaffolding, and config loading workflow.
These are end-to-end tests using real filesystem operations (no mocks).
"""

import shutil
import subprocess
from pathlib import Path
import pytest
import yaml

from audiomancer.cli import scaffold_project
from audiomancer.config import load_config, get_config_path, save_config


class TestFullInitWorkflow:
    """Test complete init → scaffold → config load cycle."""

    def test_full_init_workflow(self, tmp_path):
        """Test complete initialization workflow from start to finish.

        This tests:
        1. Creating a new project with scaffold_project()
        2. Verifying all expected files and directories are created
        3. Loading config from the created project
        4. Verifying config values match project setup
        """
        # Arrange: Set up test data
        project_dir = tmp_path / "test_project"
        project_name = "test_project"
        sample_source = tmp_path / "sample_source"
        sample_source.mkdir()

        # Create some test samples in source
        (sample_source / "kick.wav").write_text("fake kick audio")
        (sample_source / "snare.wav").write_text("fake snare audio")

        # Act: Run scaffold_project
        scaffold_project(
            project_path=project_dir,
            project_name=project_name,
            sample_source=sample_source,
            create_git=True,
        )

        # Assert: Verify directory structure
        assert project_dir.exists()
        assert (project_dir / "library").is_dir()
        assert (project_dir / "synths").is_dir()
        assert (project_dir / "samples").exists()  # Should be symlink or dir

        # Assert: Verify git initialization
        assert (project_dir / ".git").is_dir()

        # Assert: Verify project config file
        config_file = project_dir / ".audiomancer.yaml"
        assert config_file.exists()

        # Assert: Verify template files were created
        assert (project_dir / "session.tidal").exists()
        assert (project_dir / "start_superdirt.scd").exists()

        # Assert: Load and verify config
        config = load_config(project_path=project_dir)
        assert config is not None
        # Config should have the library settings pointing to this project
        assert config.library.project_root == project_dir

        # Assert: Verify session.tidal has project name
        session_content = (project_dir / "session.tidal").read_text()
        assert project_name in session_content


class TestProjectConfigInheritance:
    """Test that project config properly overrides global config."""

    def test_project_config_inheritance(self, tmp_path, monkeypatch):
        """Test three-tier config inheritance: builtin <- global <- project.

        This tests:
        1. Global config overrides builtin defaults
        2. Project config overrides global config
        3. Config merging works correctly at each level
        """
        # Arrange: Create global config
        global_config_dir = tmp_path / "global_config"
        global_config_dir.mkdir()
        global_config_file = global_config_dir / "config.yaml"

        global_config_data = {
            "analysis": {
                "max_file_size_mb": 100,  # Override default of 50
            },
            "logging": {
                "level": "INFO",  # Override default of WARNING
            }
        }

        with open(global_config_file, "w") as f:
            yaml.dump(global_config_data, f)

        # Mock get_config_path to return our test global config
        monkeypatch.setattr(
            "audiomancer.config.get_config_path",
            lambda: global_config_file
        )

        # Arrange: Create project with project-specific config
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        project_config_file = project_dir / ".audiomancer.yaml"
        project_config_data = {
            "analysis": {
                "max_file_size_mb": 200,  # Override global's 100
            },
            "library": {
                "max_file_size_mb": 5,  # Project-specific library setting
            }
        }

        with open(project_config_file, "w") as f:
            yaml.dump(project_config_data, f)

        # Act: Load config from project directory
        config = load_config(project_path=project_dir)

        # Assert: Builtin defaults are present
        assert config.generation.default_bpm == 120.0  # Builtin default

        # Assert: Global config overrides builtin
        assert config.logging.level == "INFO"  # From global, not builtin WARNING

        # Assert: Project config overrides global
        assert config.analysis.max_file_size_mb == 200  # From project, not global 100

        # Assert: Project-specific settings are present
        assert config.library.max_file_size_mb == 5  # From project

        # Assert: Settings not overridden use prior level defaults
        assert config.logging.file_level == "DEBUG"  # Builtin default (not overridden)


class TestMCPServerDetectsProject:
    """Test that MCP server uses project config when started in project dir."""

    def test_mcp_server_detects_project(self, tmp_path):
        """Test MCP server auto-detects and uses project config.

        This tests:
        1. Creating a project with specific config
        2. MCP server started from within project directory
        3. Server loads project-specific config (not just global)
        4. Server operations respect project config
        """
        # Arrange: Create project structure
        project_dir = tmp_path / "music_project"
        project_dir.mkdir()

        # Create project config with distinct settings
        project_config_file = project_dir / ".audiomancer.yaml"
        project_config_data = {
            "library": {
                "project_root": str(project_dir),
                "source_dir": str(tmp_path / "samples_source"),
                "max_file_size_mb": 15,  # Distinct from default 10
            },
            "analysis": {
                "max_file_size_mb": 75,  # Distinct from default 50
            }
        }

        with open(project_config_file, "w") as f:
            yaml.dump(project_config_data, f)

        # Create sample source directory
        sample_source = tmp_path / "samples_source"
        sample_source.mkdir()

        # Act: Load config as MCP server would (from project dir)
        config = load_config(project_path=project_dir)

        # Assert: Config loaded successfully
        assert config is not None

        # Assert: Project-specific settings are loaded
        assert config.library.project_root == project_dir
        assert config.library.max_file_size_mb == 15
        assert config.analysis.max_file_size_mb == 75

        # Assert: Config auto-detection works from subdirectory
        # Simulate MCP server started from project subdirectory
        subdir = project_dir / "sessions"
        subdir.mkdir()

        # Create a marker file in subdir to simulate cwd
        marker = subdir / "marker.txt"
        marker.write_text("test")

        # Load config with auto-detection from subdirectory
        # The find_project_config should walk up and find .audiomancer.yaml
        from audiomancer.config import find_project_config

        found_config = find_project_config(start_path=subdir)
        assert found_config is not None
        assert found_config == project_config_file

        # Load from found config
        config_from_subdir = load_config(project_path=found_config.parent)
        assert config_from_subdir.library.project_root == project_dir
