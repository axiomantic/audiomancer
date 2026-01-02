<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [audiomancer Templates](#audiomancer-templates)
  - [Template Variables](#template-variables)
  - [Variable Syntax](#variable-syntax)
  - [Validation](#validation)
  - [Type Checking Configuration](#type-checking-configuration)
  - [Usage](#usage)
  - [Template Files](#template-files)
    - [Project Templates (`project/`)](#project-templates-project)
    - [Synth Templates (`synths/`)](#synth-templates-synths)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# audiomancer Templates

Templates for generating TidalCycles projects with type checking configured by default.

## Template Variables

All templates support these variables (managed by `get_template_variables()`):

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `project_name` | str | Project name (alphanumeric, hyphens, underscores) | `my-music` |
| `project_root` | str | Absolute path to project directory | `/Users/user/my-music` |
| `sample_source` | str | Absolute path to sample source directory | `/Users/user/samples` |
| `timestamp` | str | ISO 8601 timestamp | `2026-01-01T12:00:00` |
| `audiomancer_version` | str | audiomancer version | `0.2.0` |
| `python_version` | str | Python version (major.minor) | `3.12` |
| `pyright_version` | str | Pinned pyright version | `1.1.390` |

## Variable Syntax

Variables use double curly braces: `{{ variable_name }}`

Example:

```toml
name = "{{ project_name }}"
pythonVersion = "{{ python_version }}"
```

## Validation

`get_template_variables()` validates:

- `project_name`: Must match `^[a-zA-Z0-9_-]+$`
- `project_root`: Must be absolute path
- `sample_source`: Must be absolute path

## Type Checking Configuration

Generated projects include:

- `pyproject.toml` with pyright strict mode
- `.pre-commit-config.yaml` with pyright hook
- Type stub packages in requirements.txt

All generated projects pass `pyright` with strict mode by default.

## Usage

```python
from audiomancer.templates import get_template_variables, render_template
from pathlib import Path

# Get variables
vars = get_template_variables(
    project_name="my-project",
    project_root=Path("/path/to/project"),
    sample_source=Path("/path/to/samples"),
)

# Render template
template_path = Path("templates/project/pyproject.toml.template")
rendered = render_template(template_path, vars)

# Write to file
output_path = Path("/path/to/project/pyproject.toml")
output_path.write_text(rendered)
```

## Template Files

### Project Templates (`project/`)

| File | Purpose |
|------|---------|
| `pyproject.toml.template` | Project metadata and pyright config |
| `.pre-commit-config.yaml.template` | Pre-commit hooks including pyright |
| `requirements.txt.template` | Python dependencies |
| `CLAUDE.md.template` | Claude Code instructions |
| `README.md.template` | Project README |
| `session.tidal.template` | TidalCycles session file |
| `start_superdirt.scd.template` | SuperDirt startup script |
| `.audiomancer.yaml.template` | audiomancer config |
| `.gitignore.template` | Git ignore patterns |
| `.mcp.json.template` | MCP server config |

### Synth Templates (`synths/`)

SuperCollider SynthDef templates for custom instruments.
