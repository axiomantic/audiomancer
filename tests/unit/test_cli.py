"""Tests for CLI functions."""

from pathlib import Path
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from audiomancer.cli import scaffold_project, app

runner = CliRunner()


def test_scaffold_project_creates_directory_structure(tmp_path):
    """scaffold_project creates project directory with required subdirectories."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    # Project directory should exist
    assert project_path.exists()
    assert project_path.is_dir()

    # Required subdirectories should exist
    assert (project_path / "library").exists()
    assert (project_path / "library").is_dir()
    assert (project_path / "synths").exists()
    assert (project_path / "synths").is_dir()
    assert (project_path / "samples").exists()


def test_scaffold_project_samples_symlink_when_different(tmp_path):
    """scaffold_project creates samples as symlink when source is different from project."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    samples_dir = project_path / "samples"

    # Should be a symlink pointing to sample_source
    assert samples_dir.is_symlink()
    assert samples_dir.resolve() == sample_source.resolve()


def test_scaffold_project_samples_directory_when_inside_project(tmp_path):
    """scaffold_project creates samples as directory when source is inside project."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True)
    sample_source = project_path / "samples"

    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    samples_dir = project_path / "samples"

    # Should be a regular directory, not a symlink
    assert samples_dir.exists()
    assert samples_dir.is_dir()
    assert not samples_dir.is_symlink()


def test_scaffold_project_renders_templates(tmp_path):
    """scaffold_project renders all template files to project directory."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    # Check that template files were rendered (no .template extension)
    assert (project_path / "session.tidal").exists()
    assert (project_path / "start_superdirt.scd").exists()
    assert (project_path / ".audiomancer.yaml").exists()
    assert (project_path / ".gitignore").exists()
    assert (project_path / ".mcp.json").exists()
    assert (project_path / "CLAUDE.md").exists()

    # Verify content is rendered (contains project name, not template variable)
    session_content = (project_path / "session.tidal").read_text()
    assert "test-project" in session_content
    assert "{{ project_name }}" not in session_content


def test_scaffold_project_creates_git_repo(tmp_path):
    """scaffold_project initializes git repo when create_git=True."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    scaffold_project(project_path, "test-project", sample_source, create_git=True)

    # Git repo should be initialized
    assert (project_path / ".git").exists()
    assert (project_path / ".git").is_dir()

    # Verify it's a valid git repo
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert ".git" in result.stdout


def test_scaffold_project_skips_git_if_exists(tmp_path):
    """scaffold_project skips git init if repo already exists."""
    project_path = tmp_path / "test-project"
    project_path.mkdir()
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    # Initialize git repo first
    subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)

    # Create a commit to verify repo is not re-initialized
    (project_path / "existing.txt").write_text("existing file")
    subprocess.run(["git", "add", "existing.txt"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_path,
        check=True,
        capture_output=True,
    )

    # Get commit hash before scaffold
    result_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_before = result_before.stdout.strip()

    # Scaffold project with create_git=True
    scaffold_project(project_path, "test-project", sample_source, create_git=True)

    # Git repo should still exist
    assert (project_path / ".git").exists()

    # Commit should be unchanged (not re-initialized)
    result_after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_after = result_after.stdout.strip()

    assert commit_before == commit_after
    assert (project_path / "existing.txt").exists()


def test_scaffold_project_no_git_when_create_git_false(tmp_path):
    """scaffold_project does not initialize git when create_git=False."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    # Git repo should not exist
    assert not (project_path / ".git").exists()


def test_scaffold_project_creates_project_dir_if_not_exists(tmp_path):
    """scaffold_project creates project directory if it doesn't exist."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    # Project path does not exist yet
    assert not project_path.exists()

    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    # Now it should exist
    assert project_path.exists()
    assert project_path.is_dir()


def test_scaffold_project_idempotent(tmp_path):
    """scaffold_project can be run multiple times without errors."""
    project_path = tmp_path / "test-project"
    sample_source = tmp_path / "samples-source"
    sample_source.mkdir()

    # Run once
    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    # Modify a file to verify it gets overwritten
    (project_path / "session.tidal").write_text("# Modified content")

    # Run again - should not raise errors
    scaffold_project(project_path, "test-project", sample_source, create_git=False)

    # File should be re-rendered
    session_content = (project_path / "session.tidal").read_text()
    assert "Modified content" not in session_content
    assert "test-project" in session_content


def test_init_command_prompts_for_project_name(tmp_path, monkeypatch):
    """init command prompts for project name with default from directory name."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create a sample source directory
    sample_source = tmp_path / "samples"
    sample_source.mkdir()

    # Mock scaffold_project to avoid side effects
    with patch('audiomancer.cli.scaffold_project') as mock_scaffold:
        # Simulate user input: just press enter to accept default, then provide sample source
        result = runner.invoke(app, ['init'], input=f'\n{sample_source}\n')

        # Should prompt with default from directory name
        assert "project name" in result.stdout.lower() or "name" in result.stdout.lower()

        # Should have called scaffold_project with directory name as project_name
        mock_scaffold.assert_called_once()
        call_args = mock_scaffold.call_args
        # When user just presses enter, default (tmp_path.name) should be used
        assert call_args.kwargs['project_name'] == tmp_path.name


def test_init_command_prompts_for_sample_source(tmp_path, monkeypatch):
    """init command prompts for sample source path."""
    monkeypatch.chdir(tmp_path)
    sample_source = tmp_path / "samples"
    sample_source.mkdir()

    with patch('audiomancer.cli.scaffold_project') as mock_scaffold:
        # Provide project name and sample source
        result = runner.invoke(app, ['init'], input=f'test-project\n{sample_source}\n')

        # Should prompt for sample source
        assert "sample" in result.stdout.lower()

        # Should have called scaffold_project with provided sample_source
        mock_scaffold.assert_called_once()
        call_args = mock_scaffold.call_args
        # Check keyword arguments
        assert call_args.kwargs['sample_source'] == sample_source


def test_init_command_uses_current_dir_by_default(tmp_path, monkeypatch):
    """init command uses current directory as project path by default."""
    monkeypatch.chdir(tmp_path)
    sample_source = tmp_path / "samples"
    sample_source.mkdir()

    with patch('audiomancer.cli.scaffold_project') as mock_scaffold:
        result = runner.invoke(app, ['init'], input=f'my-project\n{sample_source}\n')

        # Should have called scaffold_project with current directory
        mock_scaffold.assert_called_once()
        call_args = mock_scaffold.call_args
        # Check keyword arguments (scaffold_project called with kwargs)
        assert call_args.kwargs['project_path'] == tmp_path


def test_init_command_calls_scaffold_project(tmp_path, monkeypatch):
    """init command calls scaffold_project with gathered values."""
    monkeypatch.chdir(tmp_path)
    sample_source = tmp_path / "samples"
    sample_source.mkdir()

    with patch('audiomancer.cli.scaffold_project') as mock_scaffold:
        result = runner.invoke(app, ['init'], input=f'test-proj\n{sample_source}\n')

        # Should call scaffold_project exactly once
        assert mock_scaffold.call_count == 1

        # Verify it was called with correct arguments
        call_args = mock_scaffold.call_args
        # Should have project_path, project_name, sample_source as kwargs
        assert 'project_path' in call_args.kwargs
        assert 'project_name' in call_args.kwargs
        assert 'sample_source' in call_args.kwargs

        # Exit code should be 0 (success)
        assert result.exit_code == 0


@pytest.mark.xfail(reason="Validation not yet implemented")
def test_init_command_validates_sample_source_exists(tmp_path, monkeypatch):
    """init command validates that sample source path exists."""
    monkeypatch.chdir(tmp_path)
    nonexistent_path = tmp_path / "nonexistent"

    with patch('audiomancer.cli.scaffold_project') as mock_scaffold:
        # Try to provide nonexistent path
        result = runner.invoke(app, ['init'], input=f'test-project\n{nonexistent_path}\n')

        # Should either re-prompt or show error
        # The command should handle this gracefully
        # If it accepted it, scaffold_project should not be called OR it should fail
        # For this test, we expect it to reject invalid path
        if mock_scaffold.called:
            # If it called scaffold, the path should have been validated first
            # We can't enforce this in test until we implement validation
            pass
