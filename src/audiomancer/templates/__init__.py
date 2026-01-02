"""Template management for project scaffolding."""

from pathlib import Path
from typing import Match
import re


def get_template_dir() -> Path:
    """Get path to templates directory.

    Returns:
        Path to src/audiomancer/templates/
    """
    return Path(__file__).parent


def render_template(template_path: Path, variables: dict[str, str]) -> str:
    """Render a template file with variable substitution.

    Uses simple regex-based substitution: {{ variable_name }}
    Safe - no code execution like Jinja2.

    Args:
        template_path: Path to template file (.template extension)
        variables: Dict of variable_name -> value (all strings)

    Returns:
        Rendered template string with variables replaced

    Raises:
        FileNotFoundError: If template_path doesn't exist
        UnicodeDecodeError: If template is not UTF-8
    """
    template_content = template_path.read_text(encoding='utf-8')

    # Simple regex-based substitution (safe, no code execution)
    def replace_var(match: Match[str]) -> str:
        var_name = match.group(1).strip()
        return str(variables.get(var_name, match.group(0)))

    rendered = re.sub(r'\{\{\s*(\w+)\s*\}\}', replace_var, template_content)
    return rendered


def get_template_variables(
    project_name: str,
    project_root: Path,
    sample_source: Path,
) -> dict[str, str]:
    """Get variables for template rendering.

    Args:
        project_name: Project name (alphanumeric, hyphens, underscores)
        project_root: Absolute path to project directory
        sample_source: Absolute path to sample source directory

    Returns:
        Dict of variable names to string values for template substitution

    Raises:
        ValueError: If validation fails
    """
    import sys
    from datetime import datetime
    from audiomancer import __version__

    # Validate project_name
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_name):
        raise ValueError(
            f"Invalid project_name: '{project_name}'. "
            "Must contain only alphanumeric, hyphens, underscores"
        )

    # Validate paths are absolute
    if not project_root.is_absolute():
        raise ValueError(f"project_root must be absolute: {project_root}")
    if not sample_source.is_absolute():
        raise ValueError(f"sample_source must be absolute: {sample_source}")

    # All values must be strings
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    return {
        "project_name": project_name,
        "project_root": str(project_root.absolute()),
        "sample_source": str(sample_source.absolute()),
        "timestamp": datetime.now().isoformat(),
        "audiomancer_version": __version__,
        "python_version": python_version,
        "pyright_version": "1.1.390",
    }
