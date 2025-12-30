"""Tests for templates package."""

from pathlib import Path
from datetime import datetime
import pytest

from audiomancer.templates import (
    get_template_dir,
    render_template,
    get_template_variables,
)


def test_get_template_dir():
    """get_template_dir returns the templates directory path."""
    template_dir = get_template_dir()

    assert template_dir.exists()
    assert template_dir.is_dir()
    assert template_dir.name == "templates"
    assert (template_dir.parent.name == "audiomancer")


def test_render_template_basic_substitution(tmp_path):
    """render_template performs basic variable substitution."""
    template_file = tmp_path / "test.txt"
    template_file.write_text("Hello {{ name }}!")

    result = render_template(template_file, {"name": "World"})

    assert result == "Hello World!"


def test_render_template_multiple_variables(tmp_path):
    """render_template handles multiple variables."""
    template_file = tmp_path / "test.txt"
    template_file.write_text("{{ greeting }} {{ name }}! Today is {{ day }}.")

    result = render_template(
        template_file,
        {"greeting": "Hello", "name": "Alice", "day": "Monday"}
    )

    assert result == "Hello Alice! Today is Monday."


def test_render_template_whitespace_handling(tmp_path):
    """render_template handles whitespace in variable references."""
    template_file = tmp_path / "test.txt"
    template_file.write_text("{{name}} and {{  spaced  }}")

    result = render_template(
        template_file,
        {"name": "Alice", "spaced": "Bob"}
    )

    assert result == "Alice and Bob"


def test_render_template_missing_variable_unchanged(tmp_path):
    """render_template leaves undefined variables unchanged."""
    template_file = tmp_path / "test.txt"
    template_file.write_text("Hello {{ name }}, {{ missing }} here.")

    result = render_template(template_file, {"name": "World"})

    assert result == "Hello World, {{ missing }} here."


def test_render_template_numeric_values(tmp_path):
    """render_template converts numeric values to strings."""
    template_file = tmp_path / "test.txt"
    template_file.write_text("Port: {{ port }}")

    result = render_template(template_file, {"port": "8080"})

    assert result == "Port: 8080"


def test_get_template_variables():
    """get_template_variables returns standard template variable dict."""
    project_name = "my-project"
    project_root = Path("/tmp/my-project")
    sample_source = Path("/tmp/samples")

    variables = get_template_variables(project_name, project_root, sample_source)

    assert variables["project_name"] == "my-project"
    assert variables["project_root"] == str(project_root.absolute())
    assert variables["sample_source"] == str(sample_source.absolute())
    assert "timestamp" in variables
    assert "audiomancer_version" in variables

    # Validate timestamp format (ISO 8601)
    datetime.fromisoformat(variables["timestamp"])


def test_render_template_special_chars(tmp_path):
    """render_template handles paths with spaces and special characters."""
    # Create a template with path-like content
    template_file = tmp_path / "test.txt"
    template_file.write_text("Path: {{ project_path }}\nFile: {{ file_name }}")

    result = render_template(
        template_file,
        {
            "project_path": "/tmp/my project/with spaces",
            "file_name": "file-with-special_chars.txt"
        }
    )

    assert result == "Path: /tmp/my project/with spaces\nFile: file-with-special_chars.txt"


def test_render_template_multiline(tmp_path):
    """render_template handles multi-line templates correctly."""
    template_file = tmp_path / "test.txt"
    template_content = """# {{ project_name }}

Welcome to {{ project_name }}!

This project was created on {{ date }}.
Version: {{ version }}"""
    template_file.write_text(template_content)

    result = render_template(
        template_file,
        {
            "project_name": "MyProject",
            "date": "2025-12-30",
            "version": "1.0.0"
        }
    )

    expected = """# MyProject

Welcome to MyProject!

This project was created on 2025-12-30.
Version: 1.0.0"""
    assert result == expected


def test_get_template_variables_paths_resolved():
    """get_template_variables returns absolute paths."""
    project_name = "test-project"
    # Use relative paths as input
    project_root = Path("relative/path/project")
    sample_source = Path("relative/samples")

    variables = get_template_variables(project_name, project_root, sample_source)

    # Verify paths are absolute
    assert Path(variables["project_root"]).is_absolute()
    assert Path(variables["sample_source"]).is_absolute()

    # Verify they match the absolute versions
    assert variables["project_root"] == str(project_root.absolute())
    assert variables["sample_source"] == str(sample_source.absolute())


def test_template_subdirectories_exist():
    """Template subdirectories exist."""
    template_dir = get_template_dir()

    project_dir = template_dir / "project"
    synths_dir = template_dir / "synths"

    assert project_dir.exists()
    assert project_dir.is_dir()
    assert synths_dir.exists()
    assert synths_dir.is_dir()


def test_audiomancer_yaml_template_exists():
    """.audiomancer.yaml template file exists."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / ".audiomancer.yaml.template"

    assert template_file.exists()
    assert template_file.is_file()


def test_audiomancer_yaml_template_renders():
    """.audiomancer.yaml template renders with project variables."""
    import yaml

    template_dir = get_template_dir()
    template_file = template_dir / "project" / ".audiomancer.yaml.template"

    variables = {
        "project_name": "test-project",
        "sample_source": "/tmp/samples",
        "project_root": "/tmp/test-project",
        "timestamp": "2025-12-30T00:00:00",
    }

    result = render_template(template_file, variables)

    # Parse as YAML to verify structure is valid
    parsed = yaml.safe_load(result)

    # Verify it's a valid dict with expected keys
    assert isinstance(parsed, dict)
    assert "project_name" in parsed
    assert parsed["project_name"] == "test-project"

    # Verify sample_sources structure
    assert "sample_sources" in parsed
    assert isinstance(parsed["sample_sources"], list)
    assert len(parsed["sample_sources"]) > 0
    assert "/tmp/samples" in parsed["sample_sources"][0]

    # Verify library configuration contains project_root
    assert "library" in parsed
    assert "project_root" in parsed["library"]
    assert parsed["library"]["project_root"] == "/tmp/test-project"


def test_session_tidal_template_exists():
    """session.tidal template file exists."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / "session.tidal.template"

    assert template_file.exists()
    assert template_file.is_file()


def test_session_tidal_template_renders():
    """session.tidal template renders with project variables."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / "session.tidal.template"

    variables = {
        "project_name": "acid-project",
    }

    result = render_template(template_file, variables)

    # Should contain project name in header
    assert "acid-project" in result
    # Should have basic TidalCycles structure
    assert "hush" in result
    # Should have channel comments (d1-d4)
    assert "d1" in result
    assert "d2" in result
    # Should have sound patterns
    assert "sound" in result or "$" in result


def test_start_superdirt_template_exists():
    """start_superdirt.scd template file exists."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / "start_superdirt.scd.template"

    assert template_file.exists()
    assert template_file.is_file()


def test_start_superdirt_template_renders():
    """start_superdirt.scd template renders with project variables."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / "start_superdirt.scd.template"

    variables = {
        "project_root": "/tmp/test-project",
    }

    result = render_template(template_file, variables)

    # Should contain project root path
    assert "/tmp/test-project" in result
    # Should have SuperDirt startup code
    assert "SuperDirt" in result
    assert "loadSoundFiles" in result
    # Should reference library and synths directories
    assert "library" in result.lower()
    assert "synth" in result.lower()


def test_claude_md_template_exists():
    """CLAUDE.md template file exists."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / "CLAUDE.md.template"

    assert template_file.exists()
    assert template_file.is_file()


def test_claude_md_template_renders():
    """CLAUDE.md template renders with project variables."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / "CLAUDE.md.template"

    variables = {
        "project_name": "my-beats",
    }

    result = render_template(template_file, variables)

    # Should contain project name
    assert "my-beats" in result
    # Should have TidalCycles reference content
    assert "TidalCycles" in result
    # Should have basic usage info
    assert "session.tidal" in result or "hush" in result


def test_mcp_json_template_exists():
    """.mcp.json template file exists."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / ".mcp.json.template"

    assert template_file.exists()
    assert template_file.is_file()


def test_mcp_json_template_renders():
    """.mcp.json template renders with project variables."""
    import json

    template_dir = get_template_dir()
    template_file = template_dir / "project" / ".mcp.json.template"

    variables = {
        "project_root": "/home/user/project",
    }

    result = render_template(template_file, variables)

    # Parse as JSON to verify structure is valid
    parsed = json.loads(result)

    # Verify it's a valid dict
    assert isinstance(parsed, dict)

    # Verify mcpServers structure exists
    assert "mcpServers" in parsed
    assert isinstance(parsed["mcpServers"], dict)

    # Verify project root is used in configuration
    result_str = json.dumps(parsed)
    assert "/home/user/project" in result_str


def test_gitignore_template_exists():
    """.gitignore template file exists."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / ".gitignore.template"

    assert template_file.exists()
    assert template_file.is_file()


def test_gitignore_template_renders():
    """.gitignore template renders."""
    template_dir = get_template_dir()
    template_file = template_dir / "project" / ".gitignore.template"

    result = render_template(template_file, {})

    # Should have standard ignore patterns
    assert ".DS_Store" in result
    # Should ignore sample directories
    assert "samples" in result.lower() or "library" in result.lower()
    # Should ignore Python cache
    assert "__pycache__" in result or "*.pyc" in result
