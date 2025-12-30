# Project Scaffolding System Design

**Date:** 2025-12-30
**Status:** Design
**Author:** Claude (Autonomous Mode)

## Overview

Transform audiomancer from a global tool into a project-aware system with three-tier configuration inheritance and TidalCycles project scaffolding. Users can initialize new TidalCycles projects with a single `audiomancer init` command that creates all necessary files, synths, and configurations.

## Goals

1. **Three-tier config inheritance**: builtin defaults → global config → project config
2. **Single-command project creation**: `audiomancer init` with interactive prompts
3. **Complete TidalCycles starter kit**: synths, session.tidal, start_superdirt.scd, CLAUDE.md
4. **MCP server project detection**: Auto-detect project from CWD
5. **Git integration**: Optional git init with sensible .gitignore

## Architecture

### 1. Three-Tier Configuration Inheritance

```
┌─────────────────────────────────────────────────────────────┐
│ Level 1: Builtin Defaults (in code)                         │
│ - Default paths, analysis settings, model configs           │
│ - Fallback values for all settings                          │
└─────────────────────────────────────────────────────────────┘
                          ↓ (override)
┌─────────────────────────────────────────────────────────────┐
│ Level 2: User Global (~/.config/audiomancer/config.yaml)    │
│ - User's default sample source path                         │
│ - Preferred analysis settings                               │
│ - Global SuperCollider paths                                │
└─────────────────────────────────────────────────────────────┘
                          ↓ (override)
┌─────────────────────────────────────────────────────────────┐
│ Level 3: Project Local (.audiomancer.yaml)                  │
│ - Project-specific sample source                            │
│ - Project root path (samples/, library/, synths/)           │
│ - TidalCycles-specific settings                             │
└─────────────────────────────────────────────────────────────┘
```

**Dependencies:**

- **Pydantic version**: `pydantic>=2.0.0` (required in pyproject.toml)
- **Pydantic v2 API changes**:
  - Use `model_validate()` instead of `parse_obj()`
  - Use `model_dump()` instead of `dict()`
  - Use `PrivateAttr()` for internal fields like `_project_root`

**Config Loading Strategy:**

```python
def load_config(project_path: Optional[Path] = None) -> AudiomancerConfig:
    """Load config with 3-tier inheritance.

    Args:
        project_path: Optional project directory. If None, searches upward
                     from CWD for .audiomancer.yaml

    Returns:
        Merged configuration (builtin → global → project)

    Note:
        Uses Pydantic v2 API (model_validate, model_dump).
        Requires pydantic>=2.0.0.
    """
    # 1. Start with builtin defaults
    config = AudiomancerConfig()

    # 2. Override with global config (~/.config/audiomancer/config.yaml)
    global_config_path = get_config_path()
    if global_config_path.exists():
        config = merge_config(config, load_yaml(global_config_path))

    # 3. Override with project config (.audiomancer.yaml)
    project_config_path = find_project_config(project_path)
    if project_config_path:
        config = merge_config(config, load_yaml(project_config_path))
        # Store project root for relative path resolution
        config._project_root = project_config_path.parent

    return config

def find_project_config(start_path: Optional[Path] = None) -> Optional[Path]:
    """Search upward from start_path for .audiomancer.yaml.

    Stops at filesystem root or home directory.
    Similar to git's .git directory search.
    """
    current = (start_path or Path.cwd()).resolve()
    home = Path.home()

    while current != current.parent:  # Not at root
        candidate = current / ".audiomancer.yaml"
        if candidate.exists():
            return candidate
        if current == home:  # Don't search above home
            break
        current = current.parent

    return None

def merge_config(base: AudiomancerConfig, overrides: dict) -> AudiomancerConfig:
    """Deep merge overrides into base config.

    Uses pydantic v2's model_dump() and model_validate() for type safety.
    """
    base_dict = base.model_dump()
    merged = deep_merge_dicts(base_dict, overrides)
    return AudiomancerConfig.model_validate(merged)

def deep_merge_dicts(base: dict, overrides: dict, _depth: int = 0) -> dict:
    """Recursively merge two dicts, with overrides taking precedence.

    Merge Behavior:
    - Lists: REPLACED (not concatenated). Override list replaces base list entirely.
    - Type conflicts: Override value used (e.g., override dict replaces base string).
    - None values: Valid override. None in override replaces base value.
    - Max recursion depth: 10 levels (prevents infinite recursion).

    Args:
        base: Base dictionary
        overrides: Override dictionary (takes precedence)
        _depth: Internal recursion depth counter

    Returns:
        Merged dictionary

    Raises:
        RecursionError: If merge depth exceeds 10 levels
    """
    if _depth > 10:
        raise RecursionError("deep_merge_dicts exceeded maximum recursion depth of 10")

    result = base.copy()
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts: recurse
            result[key] = deep_merge_dicts(result[key], value, _depth=_depth + 1)
        else:
            # Override wins (lists replaced, type conflicts use override, None is valid)
            result[key] = value
    return result
```

**Key Design Decisions:**

1. **Search upward for project config**: Like git, allows running commands from subdirectories
2. **Stop at home directory**: Prevents accidental global project configs
3. **Explicit project root**: Stored in config for resolving relative paths
4. **Type-safe merging**: Use pydantic validation after merge
5. **Minimal project configs**: Only override what differs from global defaults

**Example Project Config (.audiomancer.yaml):**

```yaml
# Project: my-acid-tracks
# Created: 2025-12-30

# Sample library source (override global default)
library:
  source_dir: ~/Google Drive/Samples
  project_root: .  # Current directory
  max_file_size_mb: 20

# Project-specific sources
sources:
  samples:
    paths:
      - ./samples
      - ./library
  synths:
    paths:
      - ./synths

# SuperCollider integration
supercollider:
  boot_server: false
  timeout_seconds: 5.0
```

### 2. Init Command Flow

**Command Behavior:**

- **Without .audiomancer.yaml**: Create new project (interactive prompts)
- **With .audiomancer.yaml**: Update existing project (skip if files exist)
- **Force flag**: `--force` to recreate all files

**Interactive Mode (default):**

```bash
$ cd ~/my-new-project
$ audiomancer init

audiomancer initialization
==========================

No .audiomancer.yaml found. Create new project? [Y/n]: y

Project name [my-new-project]: acid-jams
Sample source path [~/Library/CloudStorage/GoogleDrive-elijahr@gmail.com/My Drive/Manual Library/Music Production/Samples]:
Create TidalCycles starter project? [Y/n]: y
Initialize git repository? [Y/n]: y

Creating project structure...
  ✓ .audiomancer.yaml
  ✓ synths/tb303.scd
  ✓ session.tidal
  ✓ start_superdirt.scd
  ✓ CLAUDE.md
  ✓ .mcp.json
  ✓ .gitignore
  ✓ samples/ (directory)
  ✓ library/ (directory)
  ✓ git repository initialized

Project 'acid-jams' created successfully!

Next steps:
  1. Start SuperCollider: open -a SuperCollider start_superdirt.scd
  2. Open session.tidal in VS Code with TidalCycles extension
  3. Enable sample packs: audiomancer enable-pack "808 Drum Kit"
  4. Start MCP server: audiomancer serve
```

**Non-Interactive Mode (CI/automation):**

```bash
$ audiomancer init \
    --name "my-project" \
    --sample-source "~/Google Drive/Samples" \
    --tidal \
    --git \
    --non-interactive

# OR use environment variables:
$ AUDIOMANCER_PROJECT_NAME="my-project" \
  AUDIOMANCER_SAMPLE_SOURCE="~/Samples" \
  audiomancer init --non-interactive
```

**Implementation:**

```python
@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", help="Project name"),
    sample_source: Optional[Path] = typer.Option(None, "--sample-source", help="Sample source directory"),
    tidal: bool = typer.Option(True, "--tidal/--no-tidal", help="Create TidalCycles starter project"),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialize git repository"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Skip prompts, use defaults/flags"),
):
    """Initialize audiomancer (global config + optional project scaffold)."""

    # 1. Ensure global config exists
    ensure_global_config()

    # 2. Detect if we're in a project context
    cwd = Path.cwd()
    project_config_path = cwd / ".audiomancer.yaml"
    is_existing_project = project_config_path.exists()

    # 3. Interactive project creation prompt (unless --non-interactive)
    if not is_existing_project and not non_interactive:
        create_project = typer.confirm(
            "\nNo .audiomancer.yaml found. Create new project?",
            default=True
        )
        if not create_project:
            console.print("[yellow]Global config ready. Run 'audiomancer init' in a project directory to scaffold.[/yellow]")
            return

    # 4. Gather project settings
    if not non_interactive:
        name = name or typer.prompt("Project name", default=cwd.name)

        # Get default from global config
        global_config = load_config()
        default_source = str(global_config.library.source_dir)
        sample_source_str = typer.prompt("Sample source path", default=default_source)
        sample_source = Path(sample_source_str).expanduser().resolve()

        tidal = typer.confirm("Create TidalCycles starter project?", default=tidal)
        git = typer.confirm("Initialize git repository?", default=git)
    else:
        # Non-interactive: use flags or environment variables
        name = name or os.getenv("AUDIOMANCER_PROJECT_NAME") or cwd.name
        sample_source = sample_source or Path(os.getenv("AUDIOMANCER_SAMPLE_SOURCE", "~/Samples")).expanduser()

    # 5. Create project structure
    scaffold_project(
        project_root=cwd,
        project_name=name,
        sample_source=sample_source,
        include_tidal=tidal,
        init_git=git,
        force=force,
    )

    # 6. Success message
    show_success_message(project_name=name, project_root=cwd)

def ensure_global_config():
    """Ensure ~/.config/audiomancer/config.yaml exists.

    Note:
        get_config_dir() MUST be imported from config.py (single source of truth).
        XDG_CONFIG_HOME environment variable MUST be respected per XDG Base Directory spec.
        Falls back to ~/.config/audiomancer if XDG_CONFIG_HOME not set.

    Implementation:
        from audiomancer.config import get_config_dir  # Consolidation point
    """
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.yaml"
    if not config_path.exists():
        # Create default global config
        default_config = """# audiomancer global configuration
# This file is used as defaults for all projects

# Audio analysis settings
analysis:
  max_file_size_mb: 50
  skip_patterns:
    - "*.asd"
    - "*.pkf"
  embedding_dim: 128

# Sample library management
library:
  source_dir: ~/Library/CloudStorage/GoogleDrive-elijahr@gmail.com/My Drive/Manual Library/Music Production/Samples
  max_file_size_mb: 10
  copy_workers: 16

# SuperCollider integration
supercollider:
  boot_server: false
  timeout_seconds: 5.0

# Storage paths
storage:
  db_path: ~/.local/share/audiomancer/audiomancer.db
  embeddings_path: ~/.local/share/audiomancer/embeddings
  models_path: ~/.local/share/audiomancer/models

# Logging
logging:
  level: WARNING
  file_level: DEBUG
  log_dir: ~/.local/share/audiomancer/logs
  max_days: 7
"""
        config_path.write_text(default_config, encoding='utf-8')
        console.print(f"[green]✓[/green] Created global config: {config_path}")
```

### 3. Template System

**UTF-8 Encoding Standard:**

ALL file I/O operations in this project MUST use explicit UTF-8 encoding:

```python
# Reading files
content = path.read_text(encoding='utf-8')
with open(path, 'r', encoding='utf-8') as f:
    data = f.read()

# Writing files
path.write_text(content, encoding='utf-8')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
```

**Rationale:**
- Cross-platform compatibility (Windows default is cp1252, not UTF-8)
- Prevents UnicodeDecodeError on non-ASCII characters
- Explicit is better than implicit (Python 3 default may vary)
- Ensures template variables with special characters work correctly

**Files requiring UTF-8:**
- All templates (.template files)
- All synth files (.scd)
- Config files (.yaml)
- Generated files (session.tidal, CLAUDE.md, etc.)
- Any text file with potential non-ASCII content

**Template Directory Structure:**

```
src/audiomancer/templates/
├── __init__.py
├── project/
│   ├── .audiomancer.yaml.template
│   ├── .gitignore.template
│   ├── .mcp.json.template
│   ├── CLAUDE.md.template
│   ├── session.tidal.template
│   └── start_superdirt.scd.template
└── synths/
    ├── tb303.scd
    ├── pad.scd
    ├── lead.scd
    └── fm_bass.scd
```

**Template Variables:**

Templates use Python string substitution (`{{ variable }}`):

- `{{ project_name }}` - Project name from init prompt
- `{{ project_root }}` - Absolute path to project directory
- `{{ sample_source }}` - Sample source directory path
- `{{ timestamp }}` - Creation timestamp (ISO format)
- `{{ audiomancer_version }}` - audiomancer package version

**Example Template (.audiomancer.yaml.template):**

```yaml
# Project: {{ project_name }}
# Created: {{ timestamp }}
# audiomancer version: {{ audiomancer_version }}

library:
  source_dir: {{ sample_source }}
  project_root: .
  max_file_size_mb: 10
  copy_workers: 16

sources:
  samples:
    paths:
      - ./samples
      - ./library
  synths:
    paths:
      - ./synths

supercollider:
  boot_server: false
  timeout_seconds: 5.0
```

**Template Rendering:**

```python
from datetime import datetime
from pathlib import Path
import re

def render_template(template_path: Path, variables: dict[str, str]) -> str:
    """Render a template file with variable substitution.

    Args:
        template_path: Path to template file
        variables: Dict of variable_name -> value

    Returns:
        Rendered template string
    """
    template_content = template_path.read_text()

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
) -> dict[str, str]:
    """Get variables for template rendering."""
    from audiomancer import __version__

    return {
        "project_name": project_name,
        "project_root": str(project_root.absolute()),
        "sample_source": str(sample_source.absolute()),
        "timestamp": datetime.now().isoformat(),
        "audiomancer_version": __version__,
    }

def scaffold_project(
    project_root: Path,
    project_name: str,
    sample_source: Path,
    include_tidal: bool = True,
    init_git: bool = True,
    force: bool = False,
):
    """Create complete project structure from templates.

    Args:
        project_root: Directory to create project in
        project_name: Project name
        sample_source: Path to sample library source
        include_tidal: Create TidalCycles starter files
        init_git: Initialize git repository
        force: Overwrite existing files
    """
    from audiomancer.templates import get_template_dir

    template_dir = get_template_dir()
    variables = get_template_variables(project_name, project_root, sample_source)

    console.print("\n[bold]Creating project structure...[/bold]\n")

    # 1. Create directories
    (project_root / "samples").mkdir(exist_ok=True)
    (project_root / "library").mkdir(exist_ok=True)
    (project_root / "synths").mkdir(exist_ok=True)

    # 2. Create .audiomancer.yaml
    create_from_template(
        template_dir / "project" / ".audiomancer.yaml.template",
        project_root / ".audiomancer.yaml",
        variables,
        force,
    )

    if include_tidal:
        # 3. Create TidalCycles files
        tidal_files = [
            ("session.tidal.template", "session.tidal"),
            ("start_superdirt.scd.template", "start_superdirt.scd"),
            ("CLAUDE.md.template", "CLAUDE.md"),
            (".mcp.json.template", ".mcp.json"),
        ]

        for template_name, output_name in tidal_files:
            create_from_template(
                template_dir / "project" / template_name,
                project_root / output_name,
                variables,
                force,
            )

        # 4. Copy synths (no variable substitution needed)
        synth_files = ["tb303.scd", "pad.scd", "lead.scd", "fm_bass.scd"]
        for synth_file in synth_files:
            src = template_dir / "synths" / synth_file
            if src.exists():
                dest = project_root / "synths" / synth_file
                if force or not dest.exists():
                    dest.write_text(src.read_text())
                    console.print(f"  [green]✓[/green] synths/{synth_file}")

    # 5. Create .gitignore
    create_from_template(
        template_dir / "project" / ".gitignore.template",
        project_root / ".gitignore",
        variables,
        force,
    )

    # 6. Initialize git repository
    if init_git and not (project_root / ".git").exists():
        import subprocess
        result = subprocess.run(
            ["git", "init"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("  [green]✓[/green] git repository initialized")
        else:
            console.print(f"  [yellow]![/yellow] git init failed: {result.stderr}")

def create_from_template(
    template_path: Path,
    output_path: Path,
    variables: dict[str, str],
    force: bool = False,
):
    """Create a file from template with variable substitution."""
    if output_path.exists() and not force:
        console.print(f"  [yellow]![/yellow] {output_path.name} (already exists, skipping)")
        return

    rendered = render_template(template_path, variables)
    output_path.write_text(rendered)
    console.print(f"  [green]✓[/green] {output_path.name}")
```

**Template Files Content:**

**1. .gitignore.template:**

```gitignore
# audiomancer project
.audiomancer.yaml

# Sample cache (large files, don't commit)
samples/
library/

# Database and embeddings (generated locally)
*.db
*.db-journal
embeddings/

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# Virtual environments
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# SuperCollider
*.sc~
```

**2. .mcp.json.template:**

```json
{
  "mcpServers": {
    "audiomancer": {
      "command": "audiomancer",
      "args": ["serve"],
      "env": {
        "AUDIOMANCER_PROJECT_ROOT": "{{ project_root }}"
      }
    }
  }
}
```

**3. session.tidal.template:**

```haskell
-- {{ project_name }} - TidalCycles Session
-- Created: {{ timestamp }}

-- Stop all
hush

-- Basic patterns to get started
d1 $ sound "bd bd bd bd"
d2 $ sound "~ cp ~ cp"
d3 $ sound "hh*8"

-- Stop a channel
d1 $ silence

-- TB-303 acid bass (restart SuperDirt first to load synth)
d1 $ n "0 3 7 12" # s "tb303"
   # cutoff 1200
   # resonance 0.7
   # envmod 0.6

-- Classic acid with slides
d1 $ n "0 ~ 12 0 ~ 7 3 ~" # s "tb303"
   # cutoff (range 400 2000 $ slow 4 sine)
   # resonance 0.8
   # envmod 0.6
   # slide "<0 0 1 0>"
   # accent "<0 0 0 1>"

-- See CLAUDE.md for complete sample reference and synth parameters
```

**4. start_superdirt.scd.template:**

```supercollider
// {{ project_name }} - SuperDirt Startup
// Created: {{ timestamp }}

SuperDirt.stop();

(
// Increase memory for sample libraries
s.options.memSize = 8192 * 256; // 2 GB
s.options.numBuffers = 1024 * 1024;
s.options.maxNodes = 1024 * 64;

s.waitForBoot {
    ~dirt = SuperDirt(2, s);
    ~dirt.loadSoundFiles;
    // Load enabled samples from library folder
    ~dirt.loadSoundFiles("{{ project_root }}/library/*");
    s.sync;
    ~dirt.start(57120, 0 ! 12);

    // Load custom synths
    "{{ project_root }}/synths/tb303.scd".load;
    "{{ project_root }}/synths/pad.scd".load;
    "{{ project_root }}/synths/lead.scd".load;
    "{{ project_root }}/synths/fm_bass.scd".load;

    "SuperDirt started on port 57120".postln;
    "Samples loaded from: {{ project_root }}/library/".postln;
};
)
```

**5. CLAUDE.md.template:**

Copy the entire CLAUDE.md from my-music project (399 lines) with these substitutions:

- Replace project-specific paths with `{{ project_root }}`
- Keep all TidalCycles reference tables and documentation
- Add project name in header

### 4. MCP Server Project Detection

**Auto-Detection Strategy:**

When the MCP server starts, it should:

1. Check for `AUDIOMANCER_PROJECT_ROOT` environment variable (highest priority)
2. Search upward from CWD for `.audiomancer.yaml` using `find_project_config()`
3. Fall back to global config if no project found

**Implementation in server.py:**

```python
async def main():
    """Run the MCP server."""
    global storage, synth_store, library_manager

    # 1. Detect project context
    project_root = detect_project_root()

    # 2. Load config with project awareness
    config = load_config(project_path=project_root)
    ensure_directories(config)

    # 3. Log project context
    import logging
    logger = logging.getLogger(__name__)
    if project_root:
        logger.info(f"Running in project: {project_root}")
        logger.info(f"Project config: {project_root / '.audiomancer.yaml'}")
    else:
        logger.info("Running with global config only")

    # 4. Initialize storage (paths now project-aware if config has project_root)
    storage = UnifiedSampleStorage(
        db_path=config.storage.db_path,
        embeddings_path=config.storage.embeddings_path
    )

    synth_store = SynthStore(str(config.storage.db_path))

    # 5. Initialize library manager with project-specific paths
    library_manager = LibraryManager(
        source_dir=config.library.source_dir,
        samples_dir=config.library.samples_dir,
        library_dir=config.library.library_dir,
    )

    # 6. Run server
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="audiomancer",
                server_version="0.1.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(listChanged=False)
                )
            )
        )

def detect_project_root() -> Optional[Path]:
    """Detect project root from environment or CWD.

    Priority:
    1. AUDIOMANCER_PROJECT_ROOT environment variable
    2. Search upward from CWD for .audiomancer.yaml
    3. None (use global config only)
    """
    import os

    # 1. Check environment variable
    env_root = os.getenv("AUDIOMANCER_PROJECT_ROOT")
    if env_root:
        project_root = Path(env_root).expanduser().resolve()
        if (project_root / ".audiomancer.yaml").exists():
            return project_root

    # 2. Search upward from CWD
    project_config = find_project_config()
    if project_config:
        return project_config.parent

    # 3. No project found
    return None
```

**Claude Code Integration (.mcp.json):**

The `.mcp.json` file sets the `AUDIOMANCER_PROJECT_ROOT` environment variable:

```json
{
  "mcpServers": {
    "audiomancer": {
      "command": "audiomancer",
      "args": ["serve"],
      "env": {
        "AUDIOMANCER_PROJECT_ROOT": "/absolute/path/to/project"
      }
    }
  }
}
```

This ensures the MCP server always uses the correct project context when invoked from Claude Code.

### 5. Git Initialization

**Git Setup:**

When `--git` is true (default in interactive mode):

1. Run `git init` in project root
2. Create `.gitignore` from template
3. Do NOT create initial commit (let user do this)

**`.gitignore` Strategy:**

```gitignore
# Large binary files - don't commit
samples/
library/

# Generated data
*.db
*.db-journal
embeddings/

# Project config is NOT ignored
# .audiomancer.yaml should be committed for team sharing
```

**Key Decision: Commit .audiomancer.yaml**

The project config `.audiomancer.yaml` is NOT in `.gitignore` because:

- It's small (YAML text file)
- Contains project-specific settings teams should share
- Users can add to personal `.git/info/exclude` if needed
- Similar to `package.json`, `Cargo.toml`, `pyproject.toml`

**Implementation:**

```python
def init_git_repo(project_root: Path) -> bool:
    """Initialize git repository in project_root.

    Returns:
        True if successful, False otherwise
    """
    import subprocess

    if (project_root / ".git").exists():
        console.print("  [yellow]![/yellow] git repository already exists")
        return False

    result = subprocess.run(
        ["git", "init"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        console.print("  [green]✓[/green] git repository initialized")
        return True
    else:
        console.print(f"  [red]✗[/red] git init failed: {result.stderr}")
        return False
```

### 6. Interface Contracts

**Config Module (config.py):**

```python
# New functions to add:

def find_project_config(start_path: Optional[Path] = None) -> Optional[Path]:
    """Search upward for .audiomancer.yaml.

    Args:
        start_path: Directory to start search from (default: CWD)

    Returns:
        Path to .audiomancer.yaml if found, else None
    """
    ...

def load_config(project_path: Optional[Path] = None) -> AudiomancerConfig:
    """Load config with 3-tier inheritance.

    Args:
        project_path: Optional project directory. If None, searches from CWD.

    Returns:
        Merged configuration
    """
    ...

def merge_config(base: AudiomancerConfig, overrides: dict) -> AudiomancerConfig:
    """Deep merge overrides into base config."""
    ...

# Modified AudiomancerConfig:
class AudiomancerConfig(BaseModel):
    # ... existing fields ...

    # Internal field to track project root (not in YAML)
    # Uses pydantic v2's PrivateAttr() for internal state
    _project_root: Optional[Path] = PrivateAttr(default=None)

    @property
    def is_project_config(self) -> bool:
        """True if loaded from project config."""
        return self._project_root is not None

    @property
    def project_root(self) -> Optional[Path]:
        """Project root directory if in project context."""
        return self._project_root
```

**CLI Module (cli.py):**

```python
# Modified init command signature:

@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", help="Project name"),
    sample_source: Optional[Path] = typer.Option(None, "--sample-source", help="Sample source directory"),
    tidal: bool = typer.Option(True, "--tidal/--no-tidal", help="Create TidalCycles starter project"),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialize git repository"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Skip prompts"),
):
    """Initialize audiomancer global config and/or project scaffold."""
    ...

# New helper functions:

def ensure_global_config() -> None:
    """Ensure ~/.config/audiomancer/config.yaml exists."""
    ...

def scaffold_project(
    project_root: Path,
    project_name: str,
    sample_source: Path,
    include_tidal: bool = True,
    init_git: bool = True,
    force: bool = False,
) -> None:
    """Create complete project structure from templates."""
    ...
```

**Templates Module (templates/__init__.py):**

```python
"""Template management for project scaffolding."""

from pathlib import Path
from typing import Dict

def get_template_dir() -> Path:
    """Get path to templates directory.

    Returns:
        Path to src/audiomancer/templates/
    """
    return Path(__file__).parent

def render_template(template_path: Path, variables: Dict[str, str]) -> str:
    """Render template with variable substitution.

    Args:
        template_path: Path to template file
        variables: Dict of variable_name -> value

    Returns:
        Rendered template string
    """
    ...

def get_template_variables(
    project_name: str,
    project_root: Path,
    sample_source: Path,
) -> Dict[str, str]:
    """Get standard variables for template rendering."""
    ...

def create_from_template(
    template_path: Path,
    output_path: Path,
    variables: Dict[str, str],
    force: bool = False,
) -> None:
    """Create file from template."""
    ...
```

**Server Module (server.py):**

```python
# New function:

def detect_project_root() -> Optional[Path]:
    """Detect project root from environment or CWD.

    Returns:
        Project root Path if found, else None
    """
    ...

# Modified main():

async def main():
    """Run MCP server with project detection."""
    project_root = detect_project_root()
    config = load_config(project_path=project_root)
    # ... rest of initialization with project-aware config
    ...
```

### 7. Error Handling

**Common Error Scenarios:**

1. **No global config + no project config**
   - Action: Prompt user to run `audiomancer init`
   - Error: Graceful message, not crash

2. **Invalid YAML in .audiomancer.yaml**
   - Action: Show YAML parse error with line number
   - Fallback: Continue with global config only

3. **Sample source path doesn't exist**
   - Action: Warn user, but continue (they can fix config later)
   - Don't block project creation

4. **Git not installed**
   - Action: Skip git init, show warning
   - Don't fail entire project creation

5. **Permission denied creating files**
   - Action: Fail gracefully with clear message
   - Show which file/directory caused error

**Error Classes:**

```python
class ProjectConfigError(AudiomancerError):
    """Error loading or parsing project config."""
    pass

class TemplateError(AudiomancerError):
    """Error rendering or creating from template."""
    pass

class ScaffoldError(AudiomancerError):
    """Error creating project structure."""
    pass
```

**Validation:**

```python
def validate_project_config(config_path: Path) -> tuple[bool, Optional[str]]:
    """Validate .audiomancer.yaml file.

    Returns:
        (is_valid, error_message)
    """
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)

        # Try to create config object (validates structure)
        AudiomancerConfig(**data)
        return (True, None)

    except yaml.YAMLError as e:
        return (False, f"Invalid YAML: {e}")
    except ValidationError as e:
        return (False, f"Invalid config structure: {e}")
    except Exception as e:
        return (False, f"Unexpected error: {e}")
```

### 8. Testing Strategy

**Unit Tests:**

```python
# tests/test_config_inheritance.py

def test_builtin_defaults():
    """Test that builtin defaults are loaded when no config files exist."""
    config = load_config()
    assert config.analysis.max_file_size_mb == 50
    assert config.library.copy_workers == 16

def test_global_config_override():
    """Test global config overrides builtin defaults."""
    # Create temporary global config
    # Verify overrides work

def test_project_config_override():
    """Test project config overrides global config."""
    # Create temporary project structure
    # Verify 3-tier inheritance

def test_find_project_config_upward_search():
    """Test upward search for .audiomancer.yaml."""
    # Create nested directory structure
    # Verify search finds config in parent

def test_find_project_config_stops_at_home():
    """Test search stops at home directory."""
    # Verify doesn't search above home

def test_merge_config_deep_merge():
    """Test deep merging of nested dicts."""
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    overrides = {"a": {"c": 99}, "e": 4}
    merged = deep_merge_dicts(base, overrides)
    assert merged == {"a": {"b": 1, "c": 99}, "d": 3, "e": 4}

# tests/test_init_command.py

def test_init_creates_global_config(tmp_path):
    """Test init creates global config when none exists."""
    # Mock config directory
    # Run init
    # Verify config created

def test_init_project_scaffold(tmp_path):
    """Test init creates complete project structure."""
    # Run init in empty directory
    # Verify all files created

def test_init_skip_existing_files(tmp_path):
    """Test init skips existing files without --force."""
    # Create project
    # Run init again
    # Verify files not overwritten

def test_init_force_overwrites(tmp_path):
    """Test --force overwrites existing files."""
    # Create project
    # Modify a file
    # Run init --force
    # Verify file was overwritten

def test_init_non_interactive(tmp_path):
    """Test --non-interactive mode uses flags."""
    # Run init with all flags
    # Verify no prompts, uses flag values

# tests/test_templates.py

def test_render_template_basic():
    """Test template variable substitution."""
    template = "Project: {{ project_name }}\nPath: {{ project_root }}"
    variables = {"project_name": "test", "project_root": "/tmp/test"}
    rendered = render_template_string(template, variables)
    assert "Project: test" in rendered
    assert "Path: /tmp/test" in rendered

def test_render_template_missing_variable():
    """Test template with missing variable (no substitution)."""
    template = "{{ existing }} and {{ missing }}"
    variables = {"existing": "value"}
    rendered = render_template_string(template, variables)
    assert "value" in rendered
    assert "{{ missing }}" in rendered  # Unchanged

def test_get_template_dir():
    """Test template directory exists."""
    template_dir = get_template_dir()
    assert template_dir.exists()
    assert (template_dir / "project").exists()
    assert (template_dir / "synths").exists()

# tests/test_project_detection.py

def test_detect_project_root_from_env(tmp_path, monkeypatch):
    """Test AUDIOMANCER_PROJECT_ROOT environment variable."""
    project = tmp_path / "myproject"
    project.mkdir()
    (project / ".audiomancer.yaml").write_text("library:\n  project_root: .")

    monkeypatch.setenv("AUDIOMANCER_PROJECT_ROOT", str(project))

    detected = detect_project_root()
    assert detected == project

def test_detect_project_root_from_cwd(tmp_path, monkeypatch):
    """Test upward search from CWD."""
    project = tmp_path / "myproject"
    subdir = project / "subdir" / "deep"
    subdir.mkdir(parents=True)
    (project / ".audiomancer.yaml").write_text("library:\n  project_root: .")

    monkeypatch.chdir(subdir)

    detected = detect_project_root()
    assert detected == project

def test_detect_project_root_none(tmp_path, monkeypatch):
    """Test returns None when no project found."""
    monkeypatch.chdir(tmp_path)
    detected = detect_project_root()
    assert detected is None
```

**Integration Tests:**

```python
# tests/integration/test_full_project_workflow.py

def test_full_project_creation_workflow(tmp_path):
    """End-to-end test of project creation."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # 1. Run init
    result = runner.invoke(app, [
        "init",
        "--name", "test-project",
        "--sample-source", str(tmp_path / "samples"),
        "--tidal",
        "--git",
        "--non-interactive",
    ], cwd=project_dir)

    assert result.exit_code == 0

    # 2. Verify files created
    assert (project_dir / ".audiomancer.yaml").exists()
    assert (project_dir / "session.tidal").exists()
    assert (project_dir / "start_superdirt.scd").exists()
    assert (project_dir / "CLAUDE.md").exists()
    assert (project_dir / ".mcp.json").exists()
    assert (project_dir / ".gitignore").exists()
    assert (project_dir / "synths" / "tb303.scd").exists()

    # 3. Verify git initialized
    assert (project_dir / ".git").exists()

    # 4. Verify config is valid
    config = load_config(project_path=project_dir)
    assert config.is_project_config
    assert config.project_root == project_dir

    # 5. Verify MCP server can load project
    # (would need to actually start server, but can mock)

def test_project_config_inheritance(tmp_path):
    """Test 3-tier config inheritance works correctly."""
    # Create global config
    global_config_dir = tmp_path / ".config" / "audiomancer"
    global_config_dir.mkdir(parents=True)
    (global_config_dir / "config.yaml").write_text("""
library:
  max_file_size_mb: 5
analysis:
  embedding_dim: 256
""")

    # Create project config
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".audiomancer.yaml").write_text("""
library:
  max_file_size_mb: 20
  project_root: .
""")

    # Load with mocked global config path
    config = load_config(project_path=project_dir)

    # Verify inheritance:
    # - library.max_file_size_mb: project override (20)
    # - analysis.embedding_dim: global config (256)
    # - other fields: builtin defaults
    assert config.library.max_file_size_mb == 20  # Project override
    assert config.analysis.embedding_dim == 256   # Global config
    assert config.library.copy_workers == 16      # Builtin default
```

**Manual Testing Checklist:**

- [ ] Run `audiomancer init` in empty directory (interactive)
- [ ] Run `audiomancer init --non-interactive` with flags
- [ ] Verify all template files created correctly
- [ ] Start SuperDirt with generated start_superdirt.scd
- [ ] Evaluate session.tidal patterns in VS Code
- [ ] Run `audiomancer serve` and verify MCP tools work
- [ ] Test from subdirectory (upward search)
- [ ] Test with existing .audiomancer.yaml (update mode)
- [ ] Test `--force` flag overwrites
- [ ] Test git initialization
- [ ] Verify CLAUDE.md has correct sample reference
- [ ] Test enabling sample pack in new project

## Implementation Plan

**Phase 1: Config System (2-3 hours)**
- Add `find_project_config()` to config.py
- Implement 3-tier config loading
- Add `merge_config()` deep merge
- Add `_project_root` field to AudiomancerConfig
- Unit tests for config inheritance

**Phase 2: Template System (2-3 hours)**
- Create templates/ directory structure
- Create template files (.audiomancer.yaml, .gitignore, etc.)
- Copy CLAUDE.md from my-music (with substitutions)
- Copy synth files (tb303, pad, lead, fm_bass)
- Implement template rendering functions
- Unit tests for template rendering

**Phase 3: CLI Init Command (2-3 hours)**
- Rewrite `init()` command with project detection
- Add interactive prompts (typer.prompt, typer.confirm)
- Add non-interactive mode (flags + env vars)
- Implement `scaffold_project()` function
- Add success message formatting
- Unit tests for init command

**Phase 4: MCP Server Integration (1-2 hours)**
- Add `detect_project_root()` to server.py
- Modify `main()` to use project-aware config
- Add logging for project context
- Test MCP tools with project config
- Integration tests for server startup

**Phase 5: Git Integration (1 hour)**
- Implement `init_git_repo()` function
- Create .gitignore template
- Test git initialization
- Handle git not installed error

**Phase 6: Documentation & Polish (1-2 hours)**
- Update README with init command examples
- Add project scaffold documentation
- Create migration guide for existing users
- Manual testing checklist
- Final integration tests

**Total Estimated Time:** 10-15 hours

## Migration Path for Existing Users

Existing audiomancer users have only global config. No breaking changes:

1. **Global config still works**: Existing `~/.config/audiomancer/config.yaml` unchanged
2. **Opt-in project configs**: Users create projects with `audiomancer init`
3. **MCP server backwards compatible**: Works with global config if no project found
4. **Gradual adoption**: Users can try project configs without migrating everything

**Migration Guide:**

```bash
# Existing workflow (still works):
audiomancer init  # Creates global config if needed
audiomancer serve  # Uses global config

# New workflow (opt-in):
cd ~/my-tidal-project
audiomancer init  # Now prompts for project creation
# Answer prompts, creates .audiomancer.yaml + TidalCycles files
audiomancer serve  # Auto-detects project, uses project config
```

## Future Enhancements

**Not in initial implementation, but possible later:**

1. **Project templates**: Different templates beyond TidalCycles (Renoise, Bitwig, etc.)
2. **Synth marketplace**: Install synths from community repository
3. **Project presets**: Genres (acid, techno, ambient) with different starter patterns
4. **Multi-project workspaces**: Manage multiple projects in one directory
5. **Cloud sync**: Sync project configs across machines
6. **Team collaboration**: Share project configs in git for team workflows

## Success Criteria

1. ✅ User can run `audiomancer init` and get complete TidalCycles project
2. ✅ Three-tier config inheritance works correctly
3. ✅ MCP server auto-detects project from CWD
4. ✅ Templates render correctly with variable substitution
5. ✅ Git initialization optional but works by default
6. ✅ Non-interactive mode supports CI/automation
7. ✅ Existing users not affected (backwards compatible)
8. ✅ All tests pass (unit + integration)
9. ✅ Documentation complete and accurate

## Conclusion

This design provides a comprehensive project scaffolding system that:

- Uses industry-standard patterns (config inheritance, upward search)
- Minimizes user friction (single command, interactive prompts)
- Supports automation (non-interactive flags)
- Remains backwards compatible (no breaking changes)
- Provides complete TidalCycles starter kit
- Integrates seamlessly with Claude Code via MCP

The three-tier config system is flexible and intuitive, allowing users to set global defaults while overriding per-project as needed. The template system is simple but extensible for future enhancements.
