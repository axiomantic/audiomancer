# Audiomancer Test Suite

Comprehensive test infrastructure for the audiomancer project.

## Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── utils.py                 # Test utilities and helpers
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_config.py       # Configuration system tests
│   ├── test_errors.py       # Error class tests
│   └── ...
├── integration/             # Integration tests (slower)
│   ├── test_sample_workflow.py
│   └── ...
├── fixtures/                # Test data files
│   ├── samples/            # Audio samples
│   ├── synths/             # SuperCollider SynthDefs
│   └── midi/               # MIDI files
└── golden/                  # Expected outputs for regression testing
    └── README.md
```

## Running Tests

### All tests
```bash
pytest
```

### Unit tests only (fast)
```bash
pytest tests/unit/
pytest -m unit
```

### Integration tests
```bash
pytest tests/integration/
pytest -m integration
```

### Specific test file
```bash
pytest tests/unit/test_config.py
```

### Specific test
```bash
pytest tests/unit/test_config.py::TestAudiomancerConfig::test_default_config
```

### With coverage
```bash
pytest --cov=audiomancer --cov-report=html
```

### Verbose output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Show print statements
```bash
pytest -s
```

## Test Markers

Tests are organized with markers for selective execution:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with dependencies
- `@pytest.mark.slow` - Tests that take several seconds
- `@pytest.mark.audio` - Tests that process audio files
- `@pytest.mark.db` - Tests that use database
- `@pytest.mark.embeddings` - Tests that use ML embeddings
- `@pytest.mark.requires_sc` - Tests requiring SuperCollider
- `@pytest.mark.requires_tidal` - Tests requiring TidalCycles

### Run specific marker
```bash
pytest -m unit           # Only unit tests
pytest -m "not slow"     # Skip slow tests
pytest -m "audio and unit"  # Audio unit tests
```

## Fixtures

### Directories
- `temp_dir` - Temporary directory (cleaned up after test)
- `fixtures_dir` - Path to test fixtures
- `sample_fixtures` - Path to sample audio files
- `synth_fixtures` - Path to SuperCollider files
- `midi_fixtures` - Path to MIDI files
- `golden_dir` - Path to golden files

### Configuration
- `mock_config` - Test configuration with temp paths
- `in_memory_db` - SQLite in-memory database

### Test Data
- `sample_audio_data` - Generated audio signals (sine, impulse, etc.)
- `mock_sample_metadata` - Sample metadata dict
- `mock_pattern_data` - TidalCycles pattern examples
- `mock_synthdef_data` - SuperCollider SynthDef examples

### Example Usage
```python
def test_with_fixtures(temp_dir, mock_config, sample_audio_data):
    """Test using multiple fixtures."""
    audio = sample_audio_data["sine_440"]
    output_path = temp_dir / "output.wav"

    # Test code here
    assert output_path.exists()
```

## Test Utilities

The `tests/utils.py` module provides helper functions:

### Audio Generation
```python
from tests.utils import create_test_audio, create_test_impulse_train

# Create test audio
audio = create_test_audio(duration=1.0, frequency=440.0, waveform="sine")

# Create rhythm pattern
beats = create_test_impulse_train(duration=2.0, bpm=120.0)
```

### Validation Helpers
```python
from tests.utils import (
    assert_valid_sample_metadata,
    assert_valid_tidal_pattern,
    assert_valid_supercollider_code,
)

# Validate sample metadata
assert_valid_sample_metadata(sample_dict)

# Validate TidalCycles pattern
assert_valid_tidal_pattern('d1 $ sound "bd sn"')

# Validate SuperCollider code
assert_valid_supercollider_code('SynthDef(\\test, {...}).add;')
```

### Mock Data
```python
from tests.utils import create_mock_sample

# Create mock sample metadata
sample = create_mock_sample(
    sample_id="test_001",
    semantic_id="kick_808",
    category="bd",
    bpm=120.0,
)
```

### Golden Files
```python
from tests.utils import load_golden_file, save_golden_file

# Load expected output
expected = load_golden_file(golden_dir / "output.json")

# Save new golden file (when updating tests)
save_golden_file(golden_dir / "output.json", result)
```

## Writing Tests

### Unit Test Template
```python
"""Tests for module_name."""
import pytest
from audiomancer.module_name import ClassToTest


class TestClassName:
    """Tests for ClassName."""

    def test_basic_functionality(self):
        """Should perform basic operation."""
        instance = ClassToTest()
        result = instance.method()
        assert result is not None

    def test_edge_case(self):
        """Should handle edge case correctly."""
        instance = ClassToTest()
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

### Integration Test Template
```python
"""Integration tests for workflow_name."""
import pytest


@pytest.mark.integration
class TestWorkflowName:
    """Tests for complete workflow."""

    def test_end_to_end_workflow(self, mock_config, temp_dir):
        """Should complete full workflow successfully."""
        # Arrange
        setup_data()

        # Act
        result = run_workflow()

        # Assert
        assert result["status"] == "success"
```

### Test-Driven Development (TDD)

1. **Write failing test first**
   ```python
   def test_new_feature(self):
       """Should implement new feature."""
       result = new_feature()
       assert result == expected
   ```

2. **Run test (it should fail)**
   ```bash
   pytest tests/unit/test_module.py::test_new_feature
   ```

3. **Implement minimal code to pass**
   ```python
   def new_feature():
       return expected
   ```

4. **Run test (it should pass)**
   ```bash
   pytest tests/unit/test_module.py::test_new_feature
   ```

5. **Refactor and repeat**

## Best Practices

### Test Organization
- One test class per class being tested
- One test method per behavior
- Use descriptive test names that explain what and why

### Test Independence
- Tests should not depend on each other
- Use fixtures for shared setup
- Clean up resources in teardown

### Assertions
- One logical assertion per test (though multiple assert statements OK)
- Use specific assertions (`assert x == y`, not `assert x`)
- Include helpful error messages

### Mock External Dependencies
- Use fixtures for test data
- Mock network calls, file I/O, etc.
- Keep tests fast and deterministic

### Coverage Goals
- Unit tests: >80% line coverage
- Critical paths: 100% coverage
- Edge cases: Comprehensive coverage

## Continuous Integration

Tests run automatically on:
- Every commit (pre-commit hook)
- Pull requests (CI pipeline)
- Scheduled nightly builds

### Pre-commit Hook
```bash
# Install pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
pytest tests/unit/ -q
EOF
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Tests failing locally but passing in CI
- Check Python version matches CI
- Ensure all dependencies installed
- Check for timezone/locale issues

### Slow tests
- Use `-m "not slow"` to skip slow tests during development
- Optimize test data generation
- Mock expensive operations

### Flaky tests
- Identify non-deterministic behavior
- Add proper waits/timeouts
- Use fixed random seeds

### Import errors
- Ensure package installed in development mode: `pip install -e .`
- Check PYTHONPATH includes project root
- Verify all dependencies installed

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest markers](https://docs.pytest.org/en/stable/mark.html)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)
