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


def test_template_subdirectories_exist():
    """Template subdirectories exist."""
    template_dir = get_template_dir()

    project_dir = template_dir / "project"
    synths_dir = template_dir / "synths"

    assert project_dir.exists()
    assert project_dir.is_dir()
    assert synths_dir.exists()
    assert synths_dir.is_dir()
