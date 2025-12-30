"""Template management for project scaffolding."""

from pathlib import Path
from typing import Dict
import re


def get_template_dir() -> Path:
    """Get path to templates directory.

    Returns:
        Path to src/audiomancer/templates/
    """
    return Path(__file__).parent


def render_template(template_path: Path, variables: Dict[str, str]) -> str:
    """Render a template file with variable substitution.

    Uses simple regex-based substitution: {{ variable_name }}
    Safe - no code execution like Jinja2.

    Args:
        template_path: Path to template file
        variables: Dict of variable_name -> value

    Returns:
        Rendered template string
    """
    template_content = template_path.read_text(encoding='utf-8')

    # Simple regex-based substitution (safe, no code execution)
    def replace_var(match):
        var_name = match.group(1).strip()
        return str(variables.get(var_name, match.group(0)))

    rendered = re.sub(r'\{\{\s*(\w+)\s*\}\}', replace_var, template_content)
    return rendered


def get_template_variables(
    project_name: str,
    project_root: Path,
    sample_source: Path,
) -> Dict[str, str]:
    """Get variables for template rendering.

    Args:
        project_name: Project name
        project_root: Absolute path to project directory
        sample_source: Absolute path to sample source directory

    Returns:
        Dict of variable names to values
    """
    from datetime import datetime
    from audiomancer import __version__

    return {
        "project_name": project_name,
        "project_root": str(project_root.absolute()),
        "sample_source": str(sample_source.absolute()),
        "timestamp": datetime.now().isoformat(),
        "audiomancer_version": __version__,
    }
