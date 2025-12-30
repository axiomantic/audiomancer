# Project Scaffolding System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Transform audiomancer from a global tool into a project-aware system with three-tier configuration inheritance and TidalCycles project scaffolding.

**Source Design Doc:** /Users/elijahrutschman/Development/audiomancer/docs/plans/2025-12-30-project-scaffolding-design.md

**Architecture:** Three-tier config inheritance (builtin → global → project) with upward directory search for .audiomancer.yaml. Template-based project generation using Jinja2-style substitution. MCP server auto-detects project context from environment or CWD.

**Tech Stack:** Pydantic v2 (config validation), PyYAML (config files), regex (template rendering), typer (CLI), subprocess (git integration)

---

## Phase 1: Configuration System Foundation

### Task 0: Verify Pydantic v2 dependencies and API availability

**Files:**
- Read: `/Users/elijahrutschman/Development/audiomancer/pyproject.toml`
- Test: Python environment verification

**Step 1: Verify Pydantic v2 is installed**

Run: `python -c "import pydantic; print(f'Pydantic version: {pydantic.__version__}')"`
Expected: Version 2.x.x

**Step 2: Verify PrivateAttr is available**

Run: `python -c "from pydantic import PrivateAttr; print('PrivateAttr available')"`
Expected: "PrivateAttr available"

**Step 3: Verify model_validate and model_dump API**

Run:
```bash
python -c "from pydantic import BaseModel; m = BaseModel(); print(hasattr(m, 'model_validate')); print(hasattr(m, 'model_dump'))"
```
Expected: True True

**Step 4: Check pyproject.toml dependencies**

Run: `grep -A5 'dependencies' /Users/elijahrutschman/Development/audiomancer/pyproject.toml`
Expected: Should show pydantic>=2.0.0

**Step 5: Document Pydantic v2 requirement**

If pydantic<2.0.0, add note to implementation plan about required upgrade.
If pydantic>=2.0.0, proceed with confidence.

---

### Task 1: Add config helper utilities to config.py

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/config.py`
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_config.py`

**Step 1: Write test for get_config_dir with XDG_CONFIG_HOME**

Add to `tests/unit/test_config.py`:

```python
import os
import pytest
from pathlib import Path
from audiomancer.config import get_config_dir, get_data_dir


def test_get_config_dir_respects_xdg_config_home(monkeypatch, tmp_path):
    """Test that get_config_dir respects XDG_CONFIG_HOME."""
    custom_config = tmp_path / "custom_config"
    custom_config.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config))

    config_dir = get_config_dir()
    assert config_dir == custom_config / "audiomancer"


def test_get_config_dir_defaults_to_home_config(monkeypatch, tmp_path):
    """Test that get_config_dir defaults to ~/.config/audiomancer."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    config_dir = get_config_dir()
    assert config_dir == Path.home() / ".config" / "audiomancer"


def test_get_data_dir_returns_share_subdirectory(monkeypatch):
    """Test that get_data_dir returns XDG data directory."""
    data_dir = get_data_dir()
    assert data_dir == Path.home() / ".local" / "share" / "audiomancer"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py::test_get_config_dir_respects_xdg_config_home -xvs`
Expected: FAIL with "get_config_dir not found" or assertion error

**Step 3: Implement get_config_dir and get_data_dir in config.py**

Add after line 107 in `src/audiomancer/config.py`:

```python
def get_config_dir() -> Path:
    """Get the audiomancer config directory.

    Respects XDG_CONFIG_HOME environment variable.
    Falls back to ~/.config/audiomancer if not set.

    Returns:
        Path to config directory
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    return Path(xdg_config).expanduser() / "audiomancer"


def get_data_dir() -> Path:
    """Get the audiomancer data directory.

    Returns:
        Path to data directory (~/.local/share/audiomancer)
    """
    return Path.home() / ".local" / "share" / "audiomancer"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py::test_get_config_dir_respects_xdg_config_home tests/unit/test_config.py::test_get_config_dir_defaults_to_home_config tests/unit/test_config.py::test_get_data_dir_returns_share_subdirectory -xvs`
Expected: All PASS

**Step 5: Update get_config_path to use get_config_dir**

Replace lines 174-177 in `src/audiomancer/config.py`:

```python
def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.yaml"
```

**Step 6: Run all config tests**

Run: `pytest tests/unit/test_config.py -xvs`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/audiomancer/config.py tests/unit/test_config.py
git commit -m "feat(config): add XDG-compliant config and data directory helpers"
```

---

### Task 2: Add deep_merge_dicts utility

**Worktree:** `feature/deep-merge-dicts` (parallel with Task 3)
**Merge Strategy:** Use smart-merge skill to combine Tasks 2 and 3 changes to config.py

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/config.py`
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_config.py`

**Note:** This task modifies config.py in parallel with Task 3. Both branches will be merged using the smart-merge skill before Task 4.

**Step 1: Write test for deep_merge_dicts**

Add to `tests/unit/test_config.py`:

```python
from audiomancer.config import deep_merge_dicts


def test_deep_merge_dicts_basic():
    """Test basic dictionary merging."""
    base = {"a": 1, "b": 2}
    overrides = {"b": 3, "c": 4}
    result = deep_merge_dicts(base, overrides)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_dicts_nested():
    """Test deep merging of nested dictionaries."""
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    overrides = {"a": {"c": 99}, "e": 4}
    result = deep_merge_dicts(base, overrides)
    assert result == {"a": {"b": 1, "c": 99}, "d": 3, "e": 4}


def test_deep_merge_dicts_list_replacement():
    """Test that lists are replaced, not merged."""
    base = {"items": [1, 2, 3]}
    overrides = {"items": [4, 5]}
    result = deep_merge_dicts(base, overrides)
    assert result == {"items": [4, 5]}


def test_deep_merge_dicts_type_conflict():
    """Test that override type wins on conflicts."""
    base = {"value": "string"}
    overrides = {"value": {"nested": "dict"}}
    result = deep_merge_dicts(base, overrides)
    assert result == {"value": {"nested": "dict"}}


def test_deep_merge_dicts_none_value():
    """Test that None is a valid override."""
    base = {"value": 42}
    overrides = {"value": None}
    result = deep_merge_dicts(base, overrides)
    assert result == {"value": None}


def test_deep_merge_dicts_max_depth():
    """Test that recursion depth is limited."""
    # Create deeply nested structure
    base = {"a": {}}
    current = base["a"]
    for i in range(15):
        current[f"level{i}"] = {}
        current = current[f"level{i}"]

    overrides = {"a": {"level0": {"level1": {"level2": "deep"}}}}

    with pytest.raises(RecursionError, match="exceeded maximum recursion depth"):
        deep_merge_dicts(base, overrides)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py::test_deep_merge_dicts_basic -xvs`
Expected: FAIL with "deep_merge_dicts not found"

**Step 3: Implement deep_merge_dicts**

Add after `get_data_dir()` in `src/audiomancer/config.py`:

```python
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

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -k deep_merge -xvs`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/audiomancer/config.py tests/unit/test_config.py
git commit -m "feat(config): add deep_merge_dicts for config inheritance"
```

---

### Task 3: Add find_project_config function

**Worktree:** `feature/find-project-config` (parallel with Task 2)
**Merge Strategy:** Use smart-merge skill to combine Tasks 2 and 3 changes to config.py

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/config.py`
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_config.py`

**Note:** This task modifies config.py in parallel with Task 2. Both branches will be merged using the smart-merge skill before Task 4.

**Step 1: Write tests for find_project_config**

Add to `tests/unit/test_config.py`:

```python
from audiomancer.config import find_project_config


def test_find_project_config_in_cwd(tmp_path, monkeypatch):
    """Test finding .audiomancer.yaml in current directory."""
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    config_file = project_dir / ".audiomancer.yaml"
    config_file.write_text("library:\n  project_root: .", encoding='utf-8')

    monkeypatch.chdir(project_dir)

    found = find_project_config()
    assert found == config_file


def test_find_project_config_upward_search(tmp_path, monkeypatch):
    """Test upward search for .audiomancer.yaml."""
    project_dir = tmp_path / "myproject"
    subdir = project_dir / "subdir" / "deep"
    subdir.mkdir(parents=True)

    config_file = project_dir / ".audiomancer.yaml"
    config_file.write_text("library:\n  project_root: .", encoding='utf-8')

    monkeypatch.chdir(subdir)

    found = find_project_config()
    assert found == config_file


def test_find_project_config_stops_at_home(tmp_path, monkeypatch):
    """Test that search stops at home directory."""
    # Create structure above home
    fake_home = tmp_path / "home" / "user"
    fake_home.mkdir(parents=True)

    # Place config above home
    (tmp_path / ".audiomancer.yaml").write_text("library:\n  project_root: .", encoding='utf-8')

    # Mock home directory
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(fake_home)

    found = find_project_config()
    assert found is None


def test_find_project_config_none_when_not_found(tmp_path, monkeypatch):
    """Test returns None when no config found."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    found = find_project_config()
    assert found is None


def test_find_project_config_with_explicit_start_path(tmp_path):
    """Test finding config with explicit start path."""
    project_dir = tmp_path / "myproject"
    subdir = project_dir / "subdir"
    subdir.mkdir(parents=True)

    config_file = project_dir / ".audiomancer.yaml"
    config_file.write_text("library:\n  project_root: .", encoding='utf-8')

    found = find_project_config(start_path=subdir)
    assert found == config_file
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py::test_find_project_config_in_cwd -xvs`
Expected: FAIL with "find_project_config not found"

**Step 3: Implement find_project_config**

Add after `deep_merge_dicts()` in `src/audiomancer/config.py`:

```python
def find_project_config(start_path: Optional[Path] = None) -> Optional[Path]:
    """Search upward from start_path for .audiomancer.yaml.

    Stops at filesystem root or home directory.
    Similar to git's .git directory search.

    Args:
        start_path: Directory to start search from (default: CWD)

    Returns:
        Path to .audiomancer.yaml if found, else None
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -k find_project_config -xvs`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/audiomancer/config.py tests/unit/test_config.py
git commit -m "feat(config): add find_project_config for upward directory search"
```

---

### Task 4: Add _project_root private attribute to AudiomancerConfig

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/config.py`
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_config.py`

**Step 1: Write tests for _project_root attribute**

Add to `tests/unit/test_config.py`:

```python
from pydantic import PrivateAttr


def test_audiomancer_config_has_private_project_root():
    """Test that AudiomancerConfig has _project_root attribute."""
    config = AudiomancerConfig()
    assert hasattr(config, "_project_root")
    assert config._project_root is None


def test_audiomancer_config_project_root_property():
    """Test project_root property returns _project_root value."""
    config = AudiomancerConfig()
    assert config.project_root is None

    config._project_root = Path("/tmp/test-project")
    assert config.project_root == Path("/tmp/test-project")


def test_audiomancer_config_is_project_config_property():
    """Test is_project_config returns True when _project_root is set."""
    config = AudiomancerConfig()
    assert config.is_project_config is False

    config._project_root = Path("/tmp/test-project")
    assert config.is_project_config is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py::test_audiomancer_config_has_private_project_root -xvs`
Expected: FAIL with "object has no attribute '_project_root'"

**Step 3: Add _project_root attribute and properties to AudiomancerConfig**

Modify `AudiomancerConfig` class around line 163 in `src/audiomancer/config.py`:

```python
from pydantic import BaseModel, Field, field_validator, PrivateAttr


class AudiomancerConfig(BaseModel):
    """Root configuration for audiomancer."""
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    supercollider: SuperColliderConfig = Field(default_factory=SuperColliderConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    library: LibraryConfig = Field(default_factory=LibraryConfig)

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

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -k "project_root or is_project_config" -xvs`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/audiomancer/config.py tests/unit/test_config.py
git commit -m "feat(config): add _project_root private attribute to AudiomancerConfig"
```

---

### Task 5: Implement 3-tier config loading with merge_config

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/config.py`
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_config.py`

**Step 1: Write tests for merge_config**

Add to `tests/unit/test_config.py`:

```python
def test_merge_config_with_overrides():
    """Test merge_config merges overrides into base config."""
    base = AudiomancerConfig()
    overrides = {
        "library": {
            "max_file_size_mb": 20
        },
        "analysis": {
            "embedding_dim": 256
        }
    }

    merged = merge_config(base, overrides)

    assert merged.library.max_file_size_mb == 20
    assert merged.analysis.embedding_dim == 256
    # Check that unmodified fields remain from base
    assert merged.library.copy_workers == 16


def test_merge_config_preserves_base_when_no_overrides():
    """Test merge_config preserves base when overrides is empty."""
    base = AudiomancerConfig()
    base.library.max_file_size_mb = 99

    merged = merge_config(base, {})

    assert merged.library.max_file_size_mb == 99
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py::test_merge_config_with_overrides -xvs`
Expected: FAIL with "merge_config not found"

**Step 3: Implement merge_config function**

Add after `find_project_config()` in `src/audiomancer/config.py`:

```python
def merge_config(base: AudiomancerConfig, overrides: dict) -> AudiomancerConfig:
    """Deep merge overrides into base config.

    Uses pydantic v2's model_dump() and model_validate() for type safety.

    Args:
        base: Base configuration
        overrides: Override dictionary (takes precedence)

    Returns:
        Merged AudiomancerConfig instance
    """
    base_dict = base.model_dump()
    merged = deep_merge_dicts(base_dict, overrides)
    return AudiomancerConfig.model_validate(merged)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -k merge_config -xvs`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/audiomancer/config.py tests/unit/test_config.py
git commit -m "feat(config): add merge_config for 3-tier inheritance"
```

---

### Task 6: Rewrite load_config for 3-tier inheritance

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/config.py`
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/errors.py` (if ConfigError missing)
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_config.py`

**Step 0a: Verify ConfigError exists in errors.py**

Run: `grep -n "class ConfigError" /Users/elijahrutschman/Development/audiomancer/src/audiomancer/errors.py`
Expected: Shows ConfigError class definition

If not found, add to errors.py:
```python
class ConfigError(AudiomancerError):
    """Configuration file or validation error."""
    pass
```

**Step 0b: Document breaking change in load_config() signature**

Run: `grep -rn "load_config(" /Users/elijahrutschman/Development/audiomancer/src/ --include="*.py" | grep -v test | grep -v "def load_config"`
Expected: Shows all usages of load_config()

Document migration for each usage:
- OLD: `load_config()` - loads global config only
- NEW: `load_config(project_path=None)` - loads with 3-tier inheritance

Add backwards compatibility note to docstring:
```python
def load_config(project_path: Optional[Path] = None) -> AudiomancerConfig:
    """Load config with 3-tier inheritance.

    BREAKING CHANGE (v0.2.0):
    - Signature changed from load_config() to load_config(project_path=None)
    - Behavior changed: Now searches for project config by default
    - Migration: Existing code calling load_config() will now search for .audiomancer.yaml
    - To force global-only: Explicitly pass project_path=Path("/nonexistent")

    Args:
        project_path: Optional project directory. If None, searches upward
                     from CWD for .audiomancer.yaml

    Returns:
        Merged configuration (builtin → global → project)
    """
```

**Step 1: Write comprehensive tests for 3-tier load_config**

Add to `tests/unit/test_config.py`:

```python
def test_load_config_builtin_defaults_only(tmp_path, monkeypatch):
    """Test load_config returns builtin defaults when no config files exist."""
    # Use temporary non-existent paths
    fake_config_dir = tmp_path / "nonexistent"
    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: fake_config_dir)
    monkeypatch.chdir(tmp_path)

    config = load_config()

    assert config.analysis.max_file_size_mb == 50  # Builtin default
    assert config.library.copy_workers == 16  # Builtin default
    assert config._project_root is None


def test_load_config_global_overrides_builtin(tmp_path, monkeypatch):
    """Test global config overrides builtin defaults."""
    global_config_dir = tmp_path / "config" / "audiomancer"
    global_config_dir.mkdir(parents=True)
    global_config_file = global_config_dir / "config.yaml"
    global_config_file.write_text("""
library:
  max_file_size_mb: 5
analysis:
  embedding_dim: 256
""", encoding='utf-8')

    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: global_config_dir)
    monkeypatch.chdir(tmp_path)

    config = load_config()

    assert config.library.max_file_size_mb == 5  # Global override
    assert config.analysis.embedding_dim == 256  # Global override
    assert config.library.copy_workers == 16  # Builtin default
    assert config._project_root is None


def test_load_config_project_overrides_all(tmp_path, monkeypatch):
    """Test project config overrides both global and builtin."""
    # Create global config
    global_config_dir = tmp_path / "config" / "audiomancer"
    global_config_dir.mkdir(parents=True)
    global_config_file = global_config_dir / "config.yaml"
    global_config_file.write_text("""
library:
  max_file_size_mb: 5
analysis:
  embedding_dim: 256
""", encoding='utf-8')

    # Create project config
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    project_config_file = project_dir / ".audiomancer.yaml"
    project_config_file.write_text("""
library:
  max_file_size_mb: 20
  copy_workers: 32
""", encoding='utf-8')

    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: global_config_dir)

    config = load_config(project_path=project_dir)

    # Project overrides
    assert config.library.max_file_size_mb == 20
    assert config.library.copy_workers == 32
    # Global config (not overridden by project)
    assert config.analysis.embedding_dim == 256
    # Project root set
    assert config._project_root == project_dir
    assert config.is_project_config is True


def test_load_config_searches_upward_from_cwd(tmp_path, monkeypatch):
    """Test load_config searches upward for .audiomancer.yaml from CWD."""
    project_dir = tmp_path / "myproject"
    subdir = project_dir / "subdir" / "deep"
    subdir.mkdir(parents=True)

    project_config = project_dir / ".audiomancer.yaml"
    project_config.write_text("""
library:
  max_file_size_mb: 99
""", encoding='utf-8')

    # No global config
    fake_config_dir = tmp_path / "nonexistent"
    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: fake_config_dir)

    monkeypatch.chdir(subdir)

    config = load_config()

    assert config.library.max_file_size_mb == 99
    assert config._project_root == project_dir
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py::test_load_config_builtin_defaults_only -xvs`
Expected: FAIL (current implementation doesn't support 3-tier)

**Step 3: Rewrite load_config function**

Replace the existing `load_config()` function (lines 180-213) in `src/audiomancer/config.py`:

```python
def load_config(project_path: Optional[Path] = None) -> AudiomancerConfig:
    """Load config with 3-tier inheritance.

    Tier 1: Builtin defaults (AudiomancerConfig())
    Tier 2: Global config (~/.config/audiomancer/config.yaml)
    Tier 3: Project config (.audiomancer.yaml)

    Args:
        project_path: Optional project directory. If None, searches upward
                     from CWD for .audiomancer.yaml

    Returns:
        Merged configuration (builtin → global → project)

    Note:
        Uses Pydantic v2 API (model_validate, model_dump).
        Requires pydantic>=2.0.0.

    Raises:
        ConfigError: If config file exists but is invalid
    """
    from audiomancer.errors import ConfigError

    # 1. Start with builtin defaults
    config = AudiomancerConfig()

    # 2. Override with global config (~/.config/audiomancer/config.yaml)
    global_config_path = get_config_path()
    if global_config_path.exists():
        try:
            with open(global_config_path, 'r', encoding='utf-8') as f:
                global_data = yaml.safe_load(f) or {}
            config = merge_config(config, global_data)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in global config: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load global config: {e}")

    # 3. Override with project config (.audiomancer.yaml)
    project_config_path = find_project_config(project_path)
    if project_config_path:
        try:
            with open(project_config_path, 'r', encoding='utf-8') as f:
                project_data = yaml.safe_load(f) or {}
            config = merge_config(config, project_data)
            # Store project root for relative path resolution
            config._project_root = project_config_path.parent
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in project config: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load project config: {e}")

    return config
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -k load_config -xvs`
Expected: All PASS

**Step 5: Run all config tests**

Run: `pytest tests/unit/test_config.py -xvs`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/audiomancer/config.py tests/unit/test_config.py
git commit -m "feat(config): implement 3-tier config inheritance (builtin→global→project)"
```

---

## Phase 2: Template System

### Task 7: Create templates package structure

**Files:**
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/__init__.py`
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/`
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/`

**Step 1: Create templates directory structure**

Run:
```bash
mkdir -p /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project
mkdir -p /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths
```

**Step 2: Create templates/__init__.py with utility functions**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/__init__.py`:

```python
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


def create_from_template(
    template_path: Path,
    output_path: Path,
    variables: Dict[str, str],
    force: bool = False,
) -> bool:
    """Create a file from template with variable substitution.

    Args:
        template_path: Path to template file
        output_path: Path to create output file
        variables: Dict of variable_name -> value
        force: If True, overwrite existing file

    Returns:
        True if file was created/updated, False if skipped
    """
    if output_path.exists() and not force:
        return False

    rendered = render_template(template_path, variables)
    output_path.write_text(rendered, encoding='utf-8')
    return True
```

**Step 3: Verify templates package is importable**

Run: `python -c "from audiomancer.templates import get_template_dir; print(get_template_dir())"`
Expected: Prints path to templates directory

**Step 4: Commit**

```bash
git add src/audiomancer/templates/
git commit -m "feat(templates): create template system package structure"
```

---

### Task 8: Add template rendering tests

**Files:**
- Create: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_templates.py`

**Step 1: Write tests for template rendering**

Create `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_templates.py`:

```python
"""Tests for template system."""

import pytest
from pathlib import Path
from audiomancer.templates import (
    get_template_dir,
    render_template,
    get_template_variables,
    create_from_template,
)


def test_get_template_dir_exists():
    """Test template directory exists."""
    template_dir = get_template_dir()
    assert template_dir.exists()
    assert template_dir.is_dir()
    assert template_dir.name == "templates"


def test_render_template_basic_substitution(tmp_path):
    """Test basic template variable substitution."""
    template_file = tmp_path / "test.template"
    template_file.write_text("Project: {{ project_name }}\nPath: {{ project_root }}", encoding='utf-8')

    variables = {
        "project_name": "test-project",
        "project_root": "/tmp/test"
    }

    rendered = render_template(template_file, variables)

    assert "Project: test-project" in rendered
    assert "Path: /tmp/test" in rendered


def test_render_template_missing_variable_unchanged(tmp_path):
    """Test that missing variables are left unchanged."""
    template_file = tmp_path / "test.template"
    template_file.write_text("{{ existing }} and {{ missing }}", encoding='utf-8')

    variables = {"existing": "value"}

    rendered = render_template(template_file, variables)

    assert "value" in rendered
    assert "{{ missing }}" in rendered


def test_render_template_whitespace_in_braces(tmp_path):
    """Test that whitespace in {{ }} is handled."""
    template_file = tmp_path / "test.template"
    template_file.write_text("{{project_name}} vs {{  project_name  }}", encoding='utf-8')

    variables = {"project_name": "test"}

    rendered = render_template(template_file, variables)

    assert rendered == "test vs test"


def test_get_template_variables_includes_all_fields(tmp_path):
    """Test that get_template_variables returns all required fields."""
    variables = get_template_variables(
        project_name="my-project",
        project_root=tmp_path / "project",
        sample_source=tmp_path / "samples",
    )

    assert "project_name" in variables
    assert "project_root" in variables
    assert "sample_source" in variables
    assert "timestamp" in variables
    assert "audiomancer_version" in variables

    assert variables["project_name"] == "my-project"
    assert str(tmp_path / "project") in variables["project_root"]
    assert str(tmp_path / "samples") in variables["sample_source"]


def test_create_from_template_creates_file(tmp_path):
    """Test create_from_template creates output file."""
    template_file = tmp_path / "test.template"
    template_file.write_text("Name: {{ name }}", encoding='utf-8')

    output_file = tmp_path / "output.txt"
    variables = {"name": "test"}

    created = create_from_template(template_file, output_file, variables)

    assert created is True
    assert output_file.exists()
    assert output_file.read_text(encoding='utf-8') == "Name: test"


def test_create_from_template_skips_existing_without_force(tmp_path):
    """Test create_from_template skips existing files without force."""
    template_file = tmp_path / "test.template"
    template_file.write_text("New content", encoding='utf-8')

    output_file = tmp_path / "output.txt"
    output_file.write_text("Existing content", encoding='utf-8')

    created = create_from_template(template_file, output_file, {})

    assert created is False
    assert output_file.read_text(encoding='utf-8') == "Existing content"


def test_create_from_template_overwrites_with_force(tmp_path):
    """Test create_from_template overwrites existing with force=True."""
    template_file = tmp_path / "test.template"
    template_file.write_text("New content", encoding='utf-8')

    output_file = tmp_path / "output.txt"
    output_file.write_text("Existing content", encoding='utf-8')

    created = create_from_template(template_file, output_file, {}, force=True)

    assert created is True
    assert output_file.read_text(encoding='utf-8') == "New content"
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_templates.py -xvs`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/unit/test_templates.py
git commit -m "test(templates): add comprehensive template rendering tests"
```

---

### Task 9: Create project template files

**Files:**
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/.audiomancer.yaml.template`
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/.gitignore.template`
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/.mcp.json.template`
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/session.tidal.template`
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/start_superdirt.scd.template`

**Step 1: Create .audiomancer.yaml.template**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/.audiomancer.yaml.template`:

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

**Step 2: Create .gitignore.template**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/.gitignore.template`:

```gitignore
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

**Step 3: Create .mcp.json.template**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/.mcp.json.template`:

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

**Step 4: Create session.tidal.template**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/session.tidal.template`:

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

**Step 5: Create start_superdirt.scd.template**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/start_superdirt.scd.template`:

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

**Step 6: Verify templates exist**

Run: `ls -la /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/`
Expected: All 5 template files listed

**Step 7: Commit**

```bash
git add src/audiomancer/templates/project/
git commit -m "feat(templates): add project configuration templates"
```

---

### Task 10: Copy CLAUDE.md from my-music project as template

**Files:**
- Create: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/CLAUDE.md.template`

**Step 1: Copy CLAUDE.md from my-music**

Run:
```bash
cp /Users/elijahrutschman/Development/my-music/CLAUDE.md /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/CLAUDE.md.template
```

**Step 2: Add template header to CLAUDE.md.template**

Prepend to `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/CLAUDE.md.template`:

```markdown
# {{ project_name }} - TidalCycles Live Coding Project

**Created:** {{ timestamp }}
**audiomancer version:** {{ audiomancer_version }}

```

**Step 3: Replace hardcoded paths in template**

Replace in `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/CLAUDE.md.template`:
- Replace any `~/Development/my-music` with `{{ project_root }}`
- Keep all TidalCycles reference tables and documentation unchanged

Run:
```bash
sed -i '' 's|~/Development/my-music|{{ project_root }}|g' /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/CLAUDE.md.template
```

**Step 4: Verify template is valid**

Run: `wc -l /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/project/CLAUDE.md.template`
Expected: ~400+ lines

**Step 5: Commit**

```bash
git add src/audiomancer/templates/project/CLAUDE.md.template
git commit -m "feat(templates): add CLAUDE.md template from my-music project"
```

---

### Task 11: Copy synth files to templates

**Files:**
- Copy: `/Users/elijahrutschman/Development/my-music/synths/tb303.scd` → `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/tb303.scd`

**Step 1: Copy tb303.scd synth**

Run:
```bash
cp /Users/elijahrutschman/Development/my-music/synths/tb303.scd /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/tb303.scd
```

**Step 2: Create placeholder synth files**

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/pad.scd`:

```supercollider
// Pad synth placeholder
// TODO: Add custom pad synth definition

(
~dirt.addModule('pad', { |dirtEvent|
    dirtEvent.sendSynth('pad' ++ dirtEvent.numChannels,
        [
            out: dirtEvent.out,
            sustain: dirtEvent.sustain,
            freq: dirtEvent.freq,
            amp: dirtEvent.amp,
        ]
    )
}, { ~dirtEvent.value.freq.notNil });
)
```

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/lead.scd`:

```supercollider
// Lead synth placeholder
// TODO: Add custom lead synth definition

(
~dirt.addModule('lead', { |dirtEvent|
    dirtEvent.sendSynth('lead' ++ dirtEvent.numChannels,
        [
            out: dirtEvent.out,
            sustain: dirtEvent.sustain,
            freq: dirtEvent.freq,
            amp: dirtEvent.amp,
        ]
    )
}, { ~dirtEvent.value.freq.notNil });
)
```

Create `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/fm_bass.scd`:

```supercollider
// FM Bass synth placeholder
// TODO: Add custom FM bass synth definition

(
~dirt.addModule('fm_bass', { |dirtEvent|
    dirtEvent.sendSynth('fm_bass' ++ dirtEvent.numChannels,
        [
            out: dirtEvent.out,
            sustain: dirtEvent.sustain,
            freq: dirtEvent.freq,
            amp: dirtEvent.amp,
        ]
    )
}, { ~dirtEvent.value.freq.notNil });
)
```

**Step 3: Verify synth files exist**

Run: `ls -la /Users/elijahrutschman/Development/audiomancer/src/audiomancer/templates/synths/`
Expected: 4 synth files (tb303.scd, pad.scd, lead.scd, fm_bass.scd)

**Step 4: Commit**

```bash
git add src/audiomancer/templates/synths/
git commit -m "feat(templates): add synth templates (tb303 + placeholders)"
```

---

## Phase 3: CLI Init Command

### Task 12: Add project scaffolding functions to cli.py

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/cli.py`
- Test: Create `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_cli_init.py`

**Step 1: Write tests for scaffold_project**

Create `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_cli_init.py`:

```python
"""Tests for CLI init command and project scaffolding."""

import pytest
from pathlib import Path
from audiomancer.cli import scaffold_project, ensure_global_config


def test_scaffold_project_creates_all_files(tmp_path):
    """Test scaffold_project creates complete project structure."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    scaffold_project(
        project_root=project_root,
        project_name="myproject",
        sample_source=tmp_path / "samples",
        include_tidal=True,
        init_git=False,
        force=False,
    )

    # Verify directories
    assert (project_root / "samples").exists()
    assert (project_root / "library").exists()
    assert (project_root / "synths").exists()

    # Verify config files
    assert (project_root / ".audiomancer.yaml").exists()
    assert (project_root / ".gitignore").exists()

    # Verify TidalCycles files
    assert (project_root / "session.tidal").exists()
    assert (project_root / "start_superdirt.scd").exists()
    assert (project_root / "CLAUDE.md").exists()
    assert (project_root / ".mcp.json").exists()

    # Verify synth files
    assert (project_root / "synths" / "tb303.scd").exists()
    assert (project_root / "synths" / "pad.scd").exists()
    assert (project_root / "synths" / "lead.scd").exists()
    assert (project_root / "synths" / "fm_bass.scd").exists()


def test_scaffold_project_without_tidal(tmp_path):
    """Test scaffold_project without TidalCycles files."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    scaffold_project(
        project_root=project_root,
        project_name="myproject",
        sample_source=tmp_path / "samples",
        include_tidal=False,
        init_git=False,
        force=False,
    )

    # Verify config exists
    assert (project_root / ".audiomancer.yaml").exists()

    # Verify TidalCycles files NOT created
    assert not (project_root / "session.tidal").exists()
    assert not (project_root / "start_superdirt.scd").exists()
    assert not (project_root / "CLAUDE.md").exists()


def test_scaffold_project_skips_existing_files(tmp_path):
    """Test scaffold_project skips existing files without force."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    # Create existing file with custom content
    existing_file = project_root / ".audiomancer.yaml"
    existing_file.write_text("# Custom config", encoding='utf-8')

    scaffold_project(
        project_root=project_root,
        project_name="myproject",
        sample_source=tmp_path / "samples",
        include_tidal=False,
        init_git=False,
        force=False,
    )

    # Verify existing file unchanged
    assert existing_file.read_text(encoding='utf-8') == "# Custom config"


def test_scaffold_project_overwrites_with_force(tmp_path):
    """Test scaffold_project overwrites with force=True."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    # Create existing file
    existing_file = project_root / ".audiomancer.yaml"
    existing_file.write_text("# Custom config", encoding='utf-8')

    scaffold_project(
        project_root=project_root,
        project_name="myproject",
        sample_source=tmp_path / "samples",
        include_tidal=False,
        init_git=False,
        force=True,
    )

    # Verify file was overwritten (contains template content)
    content = existing_file.read_text(encoding='utf-8')
    assert "# Custom config" not in content
    assert "Project: myproject" in content


def test_scaffold_project_renders_template_variables(tmp_path):
    """Test that template variables are rendered correctly."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    sample_source = tmp_path / "samples"

    scaffold_project(
        project_root=project_root,
        project_name="test-project",
        sample_source=sample_source,
        include_tidal=True,
        init_git=False,
        force=False,
    )

    # Check .audiomancer.yaml
    config_content = (project_root / ".audiomancer.yaml").read_text(encoding='utf-8')
    assert "Project: test-project" in config_content
    assert str(sample_source) in config_content

    # Check .mcp.json
    mcp_content = (project_root / ".mcp.json").read_text(encoding='utf-8')
    assert str(project_root) in mcp_content

    # Check start_superdirt.scd
    scd_content = (project_root / "start_superdirt.scd").read_text(encoding='utf-8')
    assert str(project_root) in scd_content


def test_ensure_global_config_creates_config(tmp_path, monkeypatch):
    """Test ensure_global_config creates global config if missing."""
    fake_config_dir = tmp_path / "config" / "audiomancer"
    monkeypatch.setattr("audiomancer.cli.get_config_dir", lambda: fake_config_dir)

    fake_data_dir = tmp_path / "data" / "audiomancer"
    monkeypatch.setattr("audiomancer.cli.get_data_dir", lambda: fake_data_dir)

    ensure_global_config()

    assert fake_config_dir.exists()
    assert fake_data_dir.exists()
    assert (fake_config_dir / "config.yaml").exists()

    # Verify config content
    config_content = (fake_config_dir / "config.yaml").read_text(encoding='utf-8')
    assert "audiomancer global configuration" in config_content


def test_ensure_global_config_preserves_existing(tmp_path, monkeypatch):
    """Test ensure_global_config preserves existing config."""
    fake_config_dir = tmp_path / "config" / "audiomancer"
    fake_config_dir.mkdir(parents=True)

    config_file = fake_config_dir / "config.yaml"
    config_file.write_text("# Custom global config", encoding='utf-8')

    monkeypatch.setattr("audiomancer.cli.get_config_dir", lambda: fake_config_dir)
    monkeypatch.setattr("audiomancer.cli.get_data_dir", lambda: tmp_path / "data")

    ensure_global_config()

    # Verify existing config unchanged
    assert config_file.read_text(encoding='utf-8') == "# Custom global config"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_cli_init.py::test_scaffold_project_creates_all_files -xvs`
Expected: FAIL with "scaffold_project not found"

**Step 3: Implement scaffold_project in cli.py**

Add after the `get_data_dir()` function in `src/audiomancer/cli.py`:

```python
def ensure_global_config() -> None:
    """Ensure ~/.config/audiomancer/config.yaml exists.

    Creates directories and default config if needed.
    Does not overwrite existing config.
    """
    from audiomancer.config import get_config_dir, get_data_dir

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


def scaffold_project(
    project_root: Path,
    project_name: str,
    sample_source: Path,
    include_tidal: bool = True,
    init_git: bool = True,
    force: bool = False,
) -> None:
    """Create complete project structure from templates.

    Args:
        project_root: Directory to create project in
        project_name: Project name
        sample_source: Path to sample library source
        include_tidal: Create TidalCycles starter files
        init_git: Initialize git repository
        force: Overwrite existing files
    """
    from audiomancer.templates import (
        get_template_dir,
        get_template_variables,
        create_from_template,
    )

    template_dir = get_template_dir()
    variables = get_template_variables(project_name, project_root, sample_source)

    console.print("\n[bold]Creating project structure...[/bold]\n")

    # 1. Create directories
    (project_root / "samples").mkdir(exist_ok=True)
    (project_root / "library").mkdir(exist_ok=True)
    (project_root / "synths").mkdir(exist_ok=True)

    # 2. Create .audiomancer.yaml
    if create_from_template(
        template_dir / "project" / ".audiomancer.yaml.template",
        project_root / ".audiomancer.yaml",
        variables,
        force,
    ):
        console.print("  [green]✓[/green] .audiomancer.yaml")
    else:
        console.print("  [yellow]![/yellow] .audiomancer.yaml (already exists, skipping)")

    if include_tidal:
        # 3. Create TidalCycles files
        tidal_files = [
            ("session.tidal.template", "session.tidal"),
            ("start_superdirt.scd.template", "start_superdirt.scd"),
            ("CLAUDE.md.template", "CLAUDE.md"),
            (".mcp.json.template", ".mcp.json"),
        ]

        for template_name, output_name in tidal_files:
            if create_from_template(
                template_dir / "project" / template_name,
                project_root / output_name,
                variables,
                force,
            ):
                console.print(f"  [green]✓[/green] {output_name}")
            else:
                console.print(f"  [yellow]![/yellow] {output_name} (already exists, skipping)")

        # 4. Copy synths (no variable substitution needed)
        synth_files = ["tb303.scd", "pad.scd", "lead.scd", "fm_bass.scd"]
        for synth_file in synth_files:
            src = template_dir / "synths" / synth_file
            if src.exists():
                dest = project_root / "synths" / synth_file
                if force or not dest.exists():
                    dest.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
                    console.print(f"  [green]✓[/green] synths/{synth_file}")
                else:
                    console.print(f"  [yellow]![/yellow] synths/{synth_file} (already exists, skipping)")

    # 5. Create .gitignore
    if create_from_template(
        template_dir / "project" / ".gitignore.template",
        project_root / ".gitignore",
        variables,
        force,
    ):
        console.print("  [green]✓[/green] .gitignore")
    else:
        console.print("  [yellow]![/yellow] .gitignore (already exists, skipping)")

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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_cli_init.py -xvs`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/audiomancer/cli.py tests/unit/test_cli_init.py
git commit -m "feat(cli): add scaffold_project and ensure_global_config functions"
```

---

### Task 13: Rewrite init command for interactive project creation

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/cli.py`

**Step 1: Replace existing init command**

Replace the `init()` command (lines 33-86) in `src/audiomancer/cli.py`:

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
    import os
    from audiomancer.config import load_config

    # 1. Ensure global config exists
    ensure_global_config()

    # 2. Detect if we're in a project context
    cwd = Path.cwd()
    project_config_path = cwd / ".audiomancer.yaml"
    is_existing_project = project_config_path.exists()

    # 3. Interactive project creation prompt (unless --non-interactive)
    if not is_existing_project and not non_interactive:
        console.print("\n[bold]audiomancer initialization[/bold]")
        console.print("=" * 26 + "\n")

        create_project = typer.confirm(
            "No .audiomancer.yaml found. Create new project?",
            default=True
        )
        if not create_project:
            console.print("\n[yellow]Global config ready. Run 'audiomancer init' in a project directory to scaffold.[/yellow]\n")
            return
    elif is_existing_project and not force:
        console.print("\n[yellow]Project already initialized.[/yellow]")
        console.print(f"Config: {project_config_path}")
        console.print("\nUse --force to recreate project files.\n")
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
        if sample_source is None:
            sample_source_env = os.getenv("AUDIOMANCER_SAMPLE_SOURCE")
            if sample_source_env:
                sample_source = Path(sample_source_env).expanduser()
            else:
                # Use global config default
                global_config = load_config()
                sample_source = global_config.library.source_dir

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
    console.print(f"\n[bold green]Project '{name}' created successfully![/bold green]\n")
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Start SuperCollider: [cyan]open -a SuperCollider start_superdirt.scd[/cyan]")
    console.print("  2. Open session.tidal in VS Code with TidalCycles extension")
    console.print("  3. Enable sample packs: [cyan]audiomancer enable-pack \"808 Drum Kit\"[/cyan]")
    console.print("  4. Start MCP server: [cyan]audiomancer serve[/cyan]\n")
```

**Step 2: Update get_config_dir and get_data_dir references**

Update lines 22-29 in `src/audiomancer/cli.py` to import from config module:

```python
def get_config_dir() -> Path:
    """Get the audiomancer config directory."""
    from audiomancer.config import get_config_dir as _get_config_dir
    return _get_config_dir()


def get_data_dir() -> Path:
    """Get the audiomancer data directory."""
    from audiomancer.config import get_data_dir as _get_data_dir
    return _get_data_dir()
```

**Step 3: Test init command manually**

Run: `cd /tmp && mkdir test-project && cd test-project && audiomancer init --non-interactive --name "test" --sample-source "/tmp/samples"`
Expected: Creates project structure

**Step 4: Clean up test**

Run: `rm -rf /tmp/test-project`

**Step 5: Commit**

```bash
git add src/audiomancer/cli.py
git commit -m "feat(cli): rewrite init command for interactive project scaffolding"
```

---

## Phase 4: MCP Server Integration

### Task 14: Add detect_project_root to server.py

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/server.py`
- Test: `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_server.py`

**Step 1: Write tests for detect_project_root**

Create `/Users/elijahrutschman/Development/audiomancer/tests/unit/test_server.py`:

```python
"""Tests for MCP server project detection."""

import pytest
import os
from pathlib import Path
from audiomancer.server import detect_project_root


def test_detect_project_root_from_env_variable(tmp_path, monkeypatch):
    """Test AUDIOMANCER_PROJECT_ROOT environment variable."""
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    (project_dir / ".audiomancer.yaml").write_text("library:\n  project_root: .", encoding='utf-8')

    monkeypatch.setenv("AUDIOMANCER_PROJECT_ROOT", str(project_dir))

    detected = detect_project_root()
    assert detected == project_dir


def test_detect_project_root_from_cwd(tmp_path, monkeypatch):
    """Test upward search from CWD when no env variable."""
    project_dir = tmp_path / "myproject"
    subdir = project_dir / "subdir" / "deep"
    subdir.mkdir(parents=True)
    (project_dir / ".audiomancer.yaml").write_text("library:\n  project_root: .", encoding='utf-8')

    monkeypatch.delenv("AUDIOMANCER_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(subdir)

    detected = detect_project_root()
    assert detected == project_dir


def test_detect_project_root_returns_none_when_not_found(tmp_path, monkeypatch):
    """Test returns None when no project found."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    monkeypatch.delenv("AUDIOMANCER_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(work_dir)

    detected = detect_project_root()
    assert detected is None


def test_detect_project_root_env_takes_precedence(tmp_path, monkeypatch):
    """Test env variable takes precedence over CWD search."""
    env_project = tmp_path / "env_project"
    env_project.mkdir()
    (env_project / ".audiomancer.yaml").write_text("library:\n  project_root: .", encoding='utf-8')

    cwd_project = tmp_path / "cwd_project"
    cwd_project.mkdir()
    (cwd_project / ".audiomancer.yaml").write_text("library:\n  project_root: .", encoding='utf-8')

    monkeypatch.setenv("AUDIOMANCER_PROJECT_ROOT", str(env_project))
    monkeypatch.chdir(cwd_project)

    detected = detect_project_root()
    assert detected == env_project
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_server.py::test_detect_project_root_from_env_variable -xvs`
Expected: FAIL with "detect_project_root not found"

**Step 3: Implement detect_project_root in server.py**

Add after imports in `src/audiomancer/server.py`:

```python
def detect_project_root() -> Optional[Path]:
    """Detect project root from environment or CWD.

    Priority:
    1. AUDIOMANCER_PROJECT_ROOT environment variable
    2. Search upward from CWD for .audiomancer.yaml
    3. None (use global config only)

    Returns:
        Project root Path if found, else None
    """
    import os
    from audiomancer.config import find_project_config

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

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_server.py -xvs`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/audiomancer/server.py tests/unit/test_server.py
git commit -m "feat(server): add detect_project_root for project-aware MCP server"
```

---

### Task 15: Update server main() to use project-aware config

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/src/audiomancer/server.py`

**Step 1: Find main() function in server.py**

Run: `grep -n "async def main" /Users/elijahrutschman/Development/audiomancer/src/audiomancer/server.py`
Expected: Shows line number of main() function

**Step 2: Update main() to detect project and load config**

Modify the beginning of `main()` function in `src/audiomancer/server.py`:

```python
async def main():
    """Run the MCP server."""
    global storage, synth_store, library_manager
    import logging

    # 1. Detect project context
    project_root = detect_project_root()

    # 2. Load config with project awareness
    config = load_config(project_path=project_root)
    ensure_directories(config)

    # 3. Log project context
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

    # ... rest of main() continues unchanged
```

**Step 3: Add necessary imports to server.py**

Add to imports in `src/audiomancer/server.py`:

```python
from audiomancer.config import load_config, ensure_directories
```

**Step 4: Test server starts without errors**

Run: `audiomancer serve` (then Ctrl+C after a few seconds)
Expected: Server starts, logs show config loading

**Step 5: Commit**

```bash
git add src/audiomancer/server.py
git commit -m "feat(server): use project-aware config loading in main()"
```

---

## Phase 5: Integration Testing

### Task 16: Add end-to-end project workflow test

**Files:**
- Create: `/Users/elijahrutschman/Development/audiomancer/tests/integration/test_project_workflow.py`

**Step 1: Create integration test directory**

Run: `mkdir -p /Users/elijahrutschman/Development/audiomancer/tests/integration`

**Step 2: Write full workflow integration test**

Create `/Users/elijahrutschman/Development/audiomancer/tests/integration/test_project_workflow.py`:

```python
"""Integration tests for full project creation workflow."""

import pytest
from pathlib import Path
from audiomancer.cli import scaffold_project, ensure_global_config
from audiomancer.config import load_config


def test_full_project_creation_workflow(tmp_path, monkeypatch):
    """End-to-end test of project creation and config loading."""
    # Setup fake global config
    fake_config_dir = tmp_path / "config" / "audiomancer"
    fake_data_dir = tmp_path / "data" / "audiomancer"
    monkeypatch.setattr("audiomancer.cli.get_config_dir", lambda: fake_config_dir)
    monkeypatch.setattr("audiomancer.cli.get_data_dir", lambda: fake_data_dir)
    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: fake_config_dir)

    # 1. Ensure global config
    ensure_global_config()
    assert (fake_config_dir / "config.yaml").exists()

    # 2. Create project
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    sample_source = tmp_path / "samples"
    sample_source.mkdir()

    scaffold_project(
        project_root=project_dir,
        project_name="test-project",
        sample_source=sample_source,
        include_tidal=True,
        init_git=True,
        force=False,
    )

    # 3. Verify files created
    assert (project_dir / ".audiomancer.yaml").exists()
    assert (project_dir / "session.tidal").exists()
    assert (project_dir / "start_superdirt.scd").exists()
    assert (project_dir / "CLAUDE.md").exists()
    assert (project_dir / ".mcp.json").exists()
    assert (project_dir / ".gitignore").exists()
    assert (project_dir / "synths" / "tb303.scd").exists()

    # 4. Verify git initialized
    assert (project_dir / ".git").exists()

    # 5. Load config and verify 3-tier inheritance
    config = load_config(project_path=project_dir)

    # Project-specific override
    assert config.library.project_root == Path(".")
    assert str(sample_source) in str(config.library.source_dir)

    # Global config value (not overridden by project)
    assert config.analysis.embedding_dim == 128  # From global default

    # Project root tracking
    assert config.is_project_config is True
    assert config.project_root == project_dir


def test_project_config_inheritance_chain(tmp_path, monkeypatch):
    """Test that config inheritance works: builtin → global → project."""
    # Create global config with custom values
    global_config_dir = tmp_path / "config" / "audiomancer"
    global_config_dir.mkdir(parents=True)
    (global_config_dir / "config.yaml").write_text("""
library:
  max_file_size_mb: 5
  copy_workers: 8
analysis:
  embedding_dim: 256
""", encoding='utf-8')

    # Create project config
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".audiomancer.yaml").write_text("""
library:
  max_file_size_mb: 20
  project_root: .
""", encoding='utf-8')

    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: global_config_dir)

    # Load project config
    config = load_config(project_path=project_dir)

    # Verify inheritance chain:
    # 1. Project override beats all
    assert config.library.max_file_size_mb == 20

    # 2. Global config beats builtin
    assert config.library.copy_workers == 8
    assert config.analysis.embedding_dim == 256

    # 3. Builtin defaults for unspecified values
    assert config.supercollider.timeout_seconds == 5.0

    # 4. Project root set
    assert config.is_project_config is True
    assert config.project_root == project_dir


def test_upward_search_from_subdirectory(tmp_path, monkeypatch):
    """Test that config loading works from project subdirectories."""
    # Create project with nested structure
    project_dir = tmp_path / "myproject"
    deep_subdir = project_dir / "src" / "analyzers" / "deep"
    deep_subdir.mkdir(parents=True)

    (project_dir / ".audiomancer.yaml").write_text("""
library:
  max_file_size_mb: 99
""", encoding='utf-8')

    # No global config
    fake_config_dir = tmp_path / "nonexistent"
    monkeypatch.setattr("audiomancer.config.get_config_dir", lambda: fake_config_dir)

    # Change to deep subdirectory
    monkeypatch.chdir(deep_subdir)

    # Load config (should find project config by searching upward)
    config = load_config()

    assert config.library.max_file_size_mb == 99
    assert config.project_root == project_dir
    assert config.is_project_config is True
```

**Step 3: Run integration tests**

Run: `pytest tests/integration/test_project_workflow.py -xvs`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test(integration): add end-to-end project workflow tests"
```

---

## Phase 6: Documentation and Final Testing

### Task 17: Run full test suite

**Files:**
- None (verification step)

**Step 1: Run all unit tests**

Run: `pytest tests/unit/ -xvs`
Expected: All PASS

If tests FAIL:
- REQUIRED: Use systematic-debugging skill before making fixes
- Do NOT guess at fixes - investigate root cause
- Document failure reason and fix in commit message

**Step 2: Run all integration tests**

Run: `pytest tests/integration/ -xvs`
Expected: All PASS

If tests FAIL:
- REQUIRED: Use systematic-debugging skill before making fixes
- Check for environment-specific issues
- Verify test assumptions are valid

**Step 3: Run full test suite with coverage**

Run: `pytest tests/ -xvs --cov=audiomancer --cov-report=term-missing`
Expected: All tests PASS, coverage report shows new code covered

**Step 4: Verify no regressions in existing tests**

Run:
```bash
# Test existing config loading (pre-project-scaffolding)
pytest tests/unit/test_config.py -k "not project" -xvs

# Test existing CLI commands
pytest tests/unit/ -k "cli" -xvs

# Test existing server functionality
pytest tests/unit/ -k "server" -xvs
```

Expected: All existing tests still PASS
If FAIL: CRITICAL REGRESSION - must fix before proceeding

**Step 5: Fix any failing tests using systematic-debugging**

If any tests fail:
1. STOP - do not proceed with fixes immediately
2. Use systematic-debugging skill to investigate
3. Document hypothesis about failure cause
4. Verify hypothesis with targeted tests
5. Implement fix with verification
6. Re-run full test suite

**Step 6: Green Mirage Audit (Test Quality Verification)**

REQUIRED: Use green-mirage-audit skill to verify test quality

Run: Invoke green-mirage-audit skill with focus on:
- Config inheritance tests (verify 3-tier merge actually works)
- Template rendering tests (verify variables are actually substituted)
- Project detection tests (verify upward search actually finds config)
- Init command tests (verify files are actually created with correct content)

The audit should answer:
- Do tests actually validate correctness, or just check for "no crash"?
- Are assertions specific enough to catch bugs?
- Do mocks properly simulate real behavior?
- Are edge cases actually tested?

If audit finds "green mirages" (passing tests that don't validate correctness):
- REQUIRED: Fix tests before proceeding
- Add specific assertions
- Add negative test cases
- Verify actual behavior, not just absence of errors

**Step 7: Final verification**

Run: `pytest tests/ -x`
Expected: All PASS with high confidence in test quality

---

### Task 18: Manual testing checklist

**Files:**
- None (manual verification)

**Step 1: Test interactive init in empty directory**

Run:
```bash
cd /tmp
mkdir test-interactive
cd test-interactive
audiomancer init
# Answer prompts: name=test-interactive, source=~/samples, tidal=y, git=y
```

Verify:
- All files created
- .git directory exists
- Variables rendered correctly in templates

**Step 2: Test non-interactive init**

Run:
```bash
cd /tmp
mkdir test-noninteractive
cd test-noninteractive
audiomancer init --non-interactive --name "automated" --sample-source "/tmp/samples"
```

Verify:
- Project created without prompts
- All files exist

**Step 3: Test config inheritance**

Run:
```bash
cd /tmp/test-interactive
python -c "from audiomancer.config import load_config; c = load_config(); print(f'Project root: {c.project_root}'); print(f'Is project: {c.is_project_config}')"
```

Expected output shows project root and is_project_config=True

**Step 4: Test upward search**

Run:
```bash
cd /tmp/test-interactive
mkdir -p deep/nested/dir
cd deep/nested/dir
python -c "from audiomancer.config import load_config; c = load_config(); print(f'Found project: {c.project_root}')"
```

Expected output shows correct project root

**Step 5: Test server with project**

Run:
```bash
cd /tmp/test-interactive
audiomancer serve
# Ctrl+C after server starts
```

Verify server logs show "Running in project: /tmp/test-interactive"

**Step 6: Clean up**

Run:
```bash
rm -rf /tmp/test-interactive /tmp/test-noninteractive
```

**Step 7: Document manual test results**

Create checklist file with results (all should be ✓).

---

### Task 19: Final commit and verification

**Files:**
- All modified files

**Step 1: Check git status**

Run: `git status`
Expected: All changes committed, working tree clean

**Step 2: Review commit history**

Run: `git log --oneline -20`
Expected: Clear, descriptive commit messages

**Step 3: Verify all tests pass one final time**

Run: `pytest tests/ -x`
Expected: All PASS

**Step 4: Create final summary commit if needed**

If any documentation or minor fixes needed:
```bash
git add .
git commit -m "docs: final cleanup and documentation for project scaffolding"
```

**Step 5: Tag the completion**

Run:
```bash
git tag -a "project-scaffolding-complete" -m "Project scaffolding system implementation complete"
```

---

### Task 20: Update documentation (README, CHANGELOG, migration guide)

**Files:**
- Modify: `/Users/elijahrutschman/Development/audiomancer/README.md`
- Create: `/Users/elijahrutschman/Development/audiomancer/docs/MIGRATION-v0.2.0.md`
- Modify: `/Users/elijahrutschman/Development/audiomancer/CHANGELOG.md`

**Step 1: Update README.md with project scaffolding examples**

Add to README.md after installation section:

```markdown
## Quick Start

### Create a new TidalCycles project

```bash
# Interactive mode (recommended)
mkdir my-acid-jams && cd my-acid-jams
audiomancer init

# Non-interactive mode
audiomancer init --name "my-project" --sample-source "~/Samples" --tidal --git --non-interactive
```

### Project structure

```
my-acid-jams/
├── .audiomancer.yaml    # Project configuration
├── .gitignore           # Git ignore rules
├── .mcp.json            # Claude Code MCP server config
├── CLAUDE.md            # TidalCycles reference for Claude
├── session.tidal        # TidalCycles session file
├── start_superdirt.scd  # SuperCollider startup script
├── samples/             # Sample cache (gitignored)
├── library/             # Enabled samples (gitignored)
└── synths/              # Custom SuperCollider synths
    ├── tb303.scd
    ├── pad.scd
    ├── lead.scd
    └── fm_bass.scd
```

### Configuration inheritance

audiomancer uses three-tier config inheritance:

1. **Builtin defaults** - Sensible defaults for all settings
2. **Global config** (`~/.config/audiomancer/config.yaml`) - Your personal defaults
3. **Project config** (`.audiomancer.yaml`) - Project-specific overrides

Example:
```yaml
# .audiomancer.yaml (project config)
library:
  source_dir: ~/Google Drive/Samples  # Override global default
  max_file_size_mb: 20                # Override for this project

sources:
  samples:
    paths:
      - ./samples
      - ./library
```

### MCP server project detection

The MCP server automatically detects project context:

1. `AUDIOMANCER_PROJECT_ROOT` environment variable (highest priority)
2. Searches upward from CWD for `.audiomancer.yaml`
3. Falls back to global config

When running in Claude Code, `.mcp.json` sets `AUDIOMANCER_PROJECT_ROOT` automatically.
```

**Step 2: Create migration guide for v0.2.0**

Create `/Users/elijahrutschman/Development/audiomancer/docs/MIGRATION-v0.2.0.md`:

```markdown
# Migration Guide: v0.1.x → v0.2.0

## Breaking Changes

### `load_config()` signature and behavior changed

**OLD (v0.1.x):**
```python
from audiomancer.config import load_config

config = load_config()  # Always loads global config only
```

**NEW (v0.2.0):**
```python
from audiomancer.config import load_config

config = load_config()  # Searches for project config, then global
# OR explicitly:
config = load_config(project_path=None)  # Search for project
config = load_config(project_path=Path("/path/to/project"))  # Specific project
```

**Impact:**
- Existing code calling `load_config()` will now search for `.audiomancer.yaml`
- If you have a `.audiomancer.yaml` in your CWD or parent directories, it will be loaded
- This is usually desired behavior (project-aware config)

**Migration:**
- **For most code:** No changes needed - project detection is beneficial
- **To force global-only:** Not recommended, but you can bypass project search by passing a non-existent path

### New configuration fields

**AudiomancerConfig now has:**
- `_project_root: Optional[Path]` (private field, not in YAML)
- `is_project_config` property (True if loaded from project)
- `project_root` property (project root directory if available)

**Example usage:**
```python
config = load_config()
if config.is_project_config:
    print(f"Running in project: {config.project_root}")
else:
    print("Running with global config only")
```

## New Features

### 1. Project scaffolding with `audiomancer init`

Create complete TidalCycles projects with a single command:

```bash
mkdir my-project && cd my-project
audiomancer init  # Interactive prompts
```

### 2. Three-tier config inheritance

Configuration files are now merged in this order:
1. Builtin defaults
2. Global config (`~/.config/audiomancer/config.yaml`)
3. Project config (`.audiomancer.yaml`)

### 3. MCP server project detection

The MCP server automatically detects project context from:
- `AUDIOMANCER_PROJECT_ROOT` environment variable
- Upward search for `.audiomancer.yaml`

### 4. Template system for project files

New templates for:
- `.audiomancer.yaml` - Project configuration
- `session.tidal` - TidalCycles session
- `start_superdirt.scd` - SuperCollider startup
- `CLAUDE.md` - Reference documentation
- `.mcp.json` - Claude Code integration
- `.gitignore` - Git ignore rules
- Custom synths (tb303, pad, lead, fm_bass)

## Upgrade Steps

1. **Update audiomancer:**
   ```bash
   pip install --upgrade audiomancer
   ```

2. **Verify Pydantic v2:**
   ```bash
   python -c "import pydantic; print(pydantic.__version__)"
   ```
   Expected: 2.x.x (if not, upgrade: `pip install --upgrade pydantic`)

3. **Test existing code:**
   ```bash
   # Run your existing audiomancer code
   # Verify it works as expected
   ```

4. **Create project configs (optional but recommended):**
   ```bash
   cd ~/your-existing-project
   audiomancer init  # Creates .audiomancer.yaml and project files
   ```

5. **Update MCP server configs:**
   If using Claude Code, update `.mcp.json` to set `AUDIOMANCER_PROJECT_ROOT`:
   ```json
   {
     "mcpServers": {
       "audiomancer": {
         "command": "audiomancer",
         "args": ["serve"],
         "env": {
           "AUDIOMANCER_PROJECT_ROOT": "/path/to/project"
         }
       }
     }
   }
   ```

## Compatibility

- **Python:** No change (still Python 3.11+)
- **Dependencies:** Pydantic upgraded to v2.x (from v1.x)
- **Existing global configs:** Fully compatible, no changes needed
- **Existing code:** Compatible, but benefits from new project detection

## Rollback

If you encounter issues, you can rollback:

```bash
pip install audiomancer==0.1.x  # Replace x with your previous version
```

## Questions?

Open an issue: https://github.com/elijahr/audiomancer/issues
```

**Step 3: Update CHANGELOG.md**

Add to `/Users/elijahrutschman/Development/audiomancer/CHANGELOG.md`:

```markdown
## [0.2.0] - 2025-12-30

### Added
- **Project scaffolding system** - Create complete TidalCycles projects with `audiomancer init`
- **Three-tier config inheritance** - Builtin → global → project config merging
- **Template system** - Project files generated from templates with variable substitution
- **MCP server project detection** - Auto-detect project from `AUDIOMANCER_PROJECT_ROOT` or upward search
- **New config functions**:
  - `find_project_config()` - Search upward for `.audiomancer.yaml`
  - `merge_config()` - Deep merge config dictionaries
  - `deep_merge_dicts()` - Recursive dict merging with type safety
  - `get_config_dir()` - XDG-compliant config directory
  - `get_data_dir()` - XDG-compliant data directory
- **AudiomancerConfig enhancements**:
  - `_project_root` private field (tracks project directory)
  - `is_project_config` property (True if loaded from project)
  - `project_root` property (project root directory)
- **Project templates**:
  - `.audiomancer.yaml` - Project configuration
  - `session.tidal` - TidalCycles starter session
  - `start_superdirt.scd` - SuperCollider startup script
  - `CLAUDE.md` - Complete TidalCycles reference for Claude
  - `.mcp.json` - Claude Code MCP server configuration
  - `.gitignore` - Sensible defaults for TidalCycles projects
  - Custom synths: tb303 (acid bass), pad, lead, fm_bass

### Changed
- **BREAKING:** `load_config()` signature changed from `load_config()` to `load_config(project_path=None)`
  - Now searches for project config by default
  - See MIGRATION-v0.2.0.md for details
- **BREAKING:** Upgraded to Pydantic v2.x (from v1.x)
  - Uses `model_validate()` and `model_dump()` instead of `parse_obj()` and `dict()`
  - Uses `PrivateAttr()` for internal fields
- `init` command completely rewritten:
  - Interactive prompts for project creation
  - Non-interactive mode with flags and environment variables
  - Git initialization support
  - Template-based file generation

### Fixed
- XDG Base Directory Specification compliance for config paths
- UTF-8 encoding explicitly set for all file I/O operations

### Migration
See [docs/MIGRATION-v0.2.0.md](docs/MIGRATION-v0.2.0.md) for detailed upgrade instructions.

## [0.1.0] - 2025-12-XX

### Added
- Initial release
- MCP server with sample library tools
- SuperCollider integration
- Sample analysis and embedding
```

**Step 4: Commit documentation**

```bash
git add README.md CHANGELOG.md docs/MIGRATION-v0.2.0.md
git commit -m "docs: add v0.2.0 documentation (README, CHANGELOG, migration guide)"
```

---

## Code Style Guidelines

### Import Order

All Python files MUST follow this import order:

1. **Standard library imports** (sorted alphabetically)
2. **Blank line**
3. **Third-party imports** (sorted alphabetically)
4. **Blank line**
5. **Local application imports** (sorted alphabetically)

**Example:**
```python
# Standard library
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Third-party
import yaml
from pydantic import BaseModel, Field, PrivateAttr

# Local application
from audiomancer.config import load_config, merge_config
from audiomancer.errors import ConfigError
from audiomancer.templates import get_template_dir, render_template
```

### Test Fixture Consistency

ALL tests MUST use `tmp_path` fixture (NOT `temp_dir` or other variants):

```python
# ✅ CORRECT
def test_example(tmp_path, monkeypatch):
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    ...

# ❌ WRONG
def test_example(temp_dir, monkeypatch):  # temp_dir doesn't exist
    ...
```

### UTF-8 Encoding

ALL file I/O operations MUST explicitly specify UTF-8 encoding:

```python
# ✅ CORRECT
content = path.read_text(encoding='utf-8')
path.write_text(content, encoding='utf-8')

with open(path, 'r', encoding='utf-8') as f:
    data = f.read()

# ❌ WRONG
content = path.read_text()  # Platform-dependent encoding
path.write_text(content)    # Platform-dependent encoding
```

## Completion Checklist

After executing all tasks, verify:

### Critical Requirements (Must Pass)
- [ ] Task 0: Pydantic v2 verified (PrivateAttr, model_validate, model_dump)
- [ ] Tasks 2 & 3: Worktrees merged successfully using smart-merge skill
- [ ] Task 6: ConfigError exists or was added to errors.py
- [ ] Task 6: load_config() breaking changes documented in docstring
- [ ] Task 17: All unit tests pass (`pytest tests/unit/`)
- [ ] Task 17: All integration tests pass (`pytest tests/integration/`)
- [ ] Task 17: No regressions in existing tests (config, CLI, server)
- [ ] Task 17: Green-mirage-audit completed with no issues
- [ ] Task 20: README.md updated with project scaffolding examples
- [ ] Task 20: MIGRATION-v0.2.0.md created with breaking changes
- [ ] Task 20: CHANGELOG.md updated with v0.2.0 changes

### Functional Requirements
- [ ] Config system supports 3-tier inheritance (builtin → global → project)
- [ ] Template rendering works correctly (variables substituted)
- [ ] Init command creates complete projects (interactive and non-interactive)
- [ ] MCP server detects projects automatically (env var + upward search)
- [ ] Git integration works (git init + .gitignore)
- [ ] All template files created with correct content

### Quality Requirements
- [ ] All commits have clear, descriptive messages
- [ ] No regressions in existing functionality
- [ ] Test fixture usage is consistent (tmp_path only)
- [ ] Import order follows style guidelines
- [ ] UTF-8 encoding explicitly specified for all file I/O
- [ ] systematic-debugging used for any test failures
- [ ] Green-mirage-audit passed (tests actually validate correctness)

### Documentation Requirements
- [ ] Manual testing checklist complete (Task 18)
- [ ] README has quick start guide
- [ ] Migration guide complete and accurate
- [ ] CHANGELOG entries detailed and helpful
- [ ] Breaking changes clearly documented

## Parallel Execution Groups

**Group 0 (Prerequisites - must run first):**
- Task 0: Verify Pydantic v2 dependencies

**Group 1 (Independent - can run in parallel after Group 0):**
- Task 1: Config helper utilities
- Task 7: Create templates package structure

**Group 2 (Depends on Group 1):**
- Task 2: deep_merge_dicts (worktree: feature/deep-merge-dicts)
- Task 3: find_project_config (worktree: feature/find-project-config)
- Task 8: Template rendering tests
- **MERGE POINT:** Use smart-merge skill to combine Tasks 2 & 3 worktrees

**Group 3 (Depends on Group 2 merge):**
- Task 4: _project_root attribute
- Task 5: merge_config
- Task 9: Project template files
- Task 10: CLAUDE.md template
- Task 11: Synth files

**Group 4 (Depends on Group 3):**
- Task 6: Rewrite load_config (includes ConfigError verification and breaking change docs)
- Task 12: Scaffolding functions

**Group 5 (Depends on Group 4):**
- Task 13: Rewrite init command
- Task 14: detect_project_root

**Group 6 (Depends on Group 5):**
- Task 15: Update server main()
- Task 16: Integration tests

**Group 7 (Final - sequential with quality gates):**
- Task 17: Full test suite (includes regression tests and green-mirage-audit)
- Task 18: Manual testing
- Task 19: Final verification
- Task 20: Documentation (README, CHANGELOG, migration guide)

**Critical Quality Gates:**
1. After Task 0: Verify Pydantic v2 available before proceeding
2. After Tasks 2 & 3: Use smart-merge skill (do NOT manually merge)
3. After Task 6: Verify ConfigError exists and breaking changes documented
4. After Task 17 Step 6: Green-mirage-audit must pass
5. After Task 17: No regressions allowed
6. After Task 20: All documentation must be complete

Total estimated time: 12-18 hours (including quality verification)
