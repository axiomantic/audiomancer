"""Unit tests for MCP server functions."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
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


class TestServerMain:
    """Tests for server main() function."""

    @pytest.mark.asyncio
    async def test_server_main_uses_project_config(self, tmp_path, monkeypatch):
        """Test main() detects project and passes project_path to load_config."""
        # Setup: Create a project with config
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        config_file = project_dir / ".audiomancer.yaml"
        config_file.write_text("library:\n  project_root: .")

        # Change to project directory
        monkeypatch.chdir(project_dir)

        # Mock dependencies to avoid actually running the server
        with patch('audiomancer.server.load_config') as mock_load_config, \
             patch('audiomancer.server.ensure_directories') as mock_ensure_dirs, \
             patch('audiomancer.server.UnifiedSampleStorage') as mock_storage, \
             patch('audiomancer.server.SynthStore') as mock_synth_store, \
             patch('audiomancer.server.LibraryManager') as mock_library_manager, \
             patch('mcp.server.stdio.stdio_server') as mock_stdio:

            # Configure mocks
            mock_config = MagicMock()
            mock_config.storage.db_path = tmp_path / "test.db"
            mock_config.storage.embeddings_path = tmp_path / "embeddings"
            mock_config.library.source_dir = tmp_path / "source"
            mock_config.library.samples_dir = tmp_path / "samples"
            mock_config.library.library_dir = tmp_path / "library"
            mock_load_config.return_value = mock_config

            # Mock stdio_server to exit immediately instead of running
            async def mock_stdio_context():
                class MockContext:
                    async def __aenter__(self):
                        return (AsyncMock(), AsyncMock())
                    async def __aexit__(self, *args):
                        pass
                return MockContext()

            mock_stdio.return_value = await mock_stdio_context()

            # Need to patch server.run to avoid actually running
            with patch('audiomancer.server.server.run') as mock_run:
                mock_run.return_value = None

                # Import and run main
                from audiomancer.server import main
                await main()

            # Assert: load_config was called with project_path
            mock_load_config.assert_called_once_with(project_path=project_dir)
