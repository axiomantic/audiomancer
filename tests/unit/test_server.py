"""Unit tests for MCP server functions."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from audiomancer.server import detect_project_root


class TestDetectProjectRoot:
    """Tests for detect_project_root function."""

    def test_detect_project_root_from_cwd(self, tmp_path, monkeypatch):
        """Test detect_project_root finds config from current working directory."""
        # Setup: Create a project config file
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        config_file = project_dir / ".audiomancer.yaml"
        config_file.write_text("# test config")

        # Change to project directory
        monkeypatch.chdir(project_dir)

        # Act
        result = detect_project_root()

        # Assert: Should return the project directory (parent of config file)
        assert result == project_dir

    def test_detect_project_root_not_found(self, tmp_path, monkeypatch):
        """Test detect_project_root returns None when no config found."""
        # Setup: Empty directory with no config
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Change to empty directory
        monkeypatch.chdir(empty_dir)

        # Act
        result = detect_project_root()

        # Assert: Should return None
        assert result is None

    def test_detect_project_root_returns_path(self, tmp_path, monkeypatch):
        """Test detect_project_root returns Path object when found."""
        # Setup: Create nested directory structure with config in parent
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / ".audiomancer.yaml"
        config_file.write_text("# test config")

        subdir = project_dir / "nested" / "deep"
        subdir.mkdir(parents=True)

        # Change to nested directory
        monkeypatch.chdir(subdir)

        # Act
        result = detect_project_root()

        # Assert: Should return project root (not the nested directory)
        assert result == project_dir
        assert isinstance(result, Path)
