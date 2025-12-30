"""Tests for CLI functions."""

from pathlib import Path
import subprocess
import pytest

from audiomancer.cli import scaffold_project


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
