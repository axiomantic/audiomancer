# Implementation Checklist for Audiomancer

This checklist tracks which modules need to be implemented to make the test suite pass.

## ✅ Test Infrastructure (COMPLETE)

- [x] pytest.ini configuration
- [x] conftest.py with fixtures
- [x] Test directory structure (unit/, integration/, fixtures/, golden/)
- [x] Test utilities (utils.py)
- [x] Comprehensive documentation
- [x] 58 test cases written

## ❌ Core Modules (TO BE IMPLEMENTED)

### High Priority - Required for Unit Tests

#### 1. audiomancer/config.py
**Required for**: 20 tests in `test_config.py`

Classes to implement:
- [ ] `AudiomancerConfig` - Main configuration class
  - [ ] `analysis: AnalysisConfig` - Analysis settings
  - [ ] `generation: GenerationConfig` - Generation settings
  - [ ] `storage: StorageConfig` - Storage paths
  - [ ] `logging: LoggingConfig` - Logging configuration

- [ ] `AnalysisConfig` - Analysis configuration
  - [ ] `max_file_size_mb: int = 50`
  - [ ] `sample_rate: int = 44100`
  - [ ] `hop_length: int = 512`
  - [ ] `n_fft: int = 2048`

- [ ] `GenerationConfig` - Generation configuration
  - [ ] `default_bpm: float = 120.0` (range: 60-240)
  - [ ] `max_pattern_length: int = 64`
  - [ ] `default_target: str = "tidal"`

- [ ] `StorageConfig` - Storage configuration
  - [ ] `db_path: Path = Path("~/.audiomancer/db.sqlite")`
  - [ ] `embeddings_path: Path = Path("~/.audiomancer/embeddings")`
  - [ ] `models_path: Path = Path("~/.audiomancer/models")`
  - [ ] Validate paths are expanded (~) and absolute

- [ ] `LoggingConfig` - Logging configuration
  - [ ] `level: str = "INFO"` (must be DEBUG/INFO/WARNING/ERROR)
  - [ ] `format: str = "%(asctime)s [%(levelname)s] %(message)s"`

Functions to implement:
- [ ] `load_config(path: Path) -> AudiomancerConfig`
  - Load from YAML file
  - Return defaults if file doesn't exist
  - Handle partial configs (fill missing with defaults)
  - Parse comments in YAML

- [ ] `save_config(config: AudiomancerConfig, path: Path) -> None`
  - Save to YAML file
  - Create parent directories if needed
  - Preserve readability

Dependencies:
- `pydantic` for validation
- `PyYAML` for config file parsing
- `pathlib` for path handling

#### 2. audiomancer/errors.py
**Required for**: 30 tests in `test_errors.py`

Classes to implement:
- [ ] `AudiomancerError(Exception)` - Base error class
  - [ ] `__init__(self, message: str, details: dict = None)`
  - [ ] `details: dict` - Additional error information
  - [ ] `to_dict(self) -> dict` - Serialize to dict with type, message, details

- [ ] `ConfigError(AudiomancerError)` - Configuration errors
  - Inherits all base functionality

- [ ] `StorageError(AudiomancerError)` - Storage/database errors
  - Inherits all base functionality

- [ ] `SampleNotFoundError(StorageError)` - Sample lookup failures
  - [ ] `__init__(self, sample_id: str, details: dict = None)`
  - [ ] `sample_id: str` - ID of missing sample
  - [ ] Include sample_id in details dict

- [ ] `DuplicateSampleError(StorageError)` - Duplicate sample imports
  - [ ] `__init__(self, existing_id: str, file_path: str, details: dict = None)`
  - [ ] `existing_id: str` - ID of existing sample
  - [ ] `file_path: str` - Path to duplicate file
  - [ ] Include both in details dict

Dependencies:
- None (pure Python)

### Medium Priority - Required for Integration Tests

#### 3. audiomancer/storage.py (or database.py)
**Required for**: Integration tests in `test_sample_workflow.py`

- [ ] `Database` class
  - [ ] `__init__(self, config: AudiomancerConfig)`
  - [ ] `initialize(self) -> None` - Create tables
  - [ ] `store_sample(self, metadata: dict) -> str` - Store sample, return ID
  - [ ] `get_sample(self, sample_id: str) -> dict` - Retrieve by ID
  - [ ] `search_samples(self, **filters) -> list[dict]` - Search with filters
  - [ ] Handle `SampleNotFoundError` when sample doesn't exist
  - [ ] Handle `DuplicateSampleError` when duplicate detected

Dependencies:
- `sqlalchemy` for database ORM
- `audiomancer.config` for configuration
- `audiomancer.errors` for exceptions

#### 4. audiomancer/importers.py
**Required for**: Integration tests in `test_sample_workflow.py`

- [ ] `SampleImporter` class
  - [ ] `__init__(self, config: AudiomancerConfig)`
  - [ ] `import_sample(self, path: Path, metadata: dict = None) -> dict`
    - Analyze audio file
    - Extract metadata (duration, sample rate, etc.)
    - Generate semantic ID
    - Store in database
    - Return complete metadata
  - [ ] Handle file validation
  - [ ] Handle max file size checks

Dependencies:
- `librosa` or `soundfile` for audio I/O
- `audiomancer.analysis` for audio analysis
- `audiomancer.storage` for database
- `audiomancer.errors` for exceptions

#### 5. audiomancer/analysis.py
**Required for**: Sample analysis functionality

- [ ] Audio analysis functions
  - [ ] `analyze_sample(path: Path) -> dict` - Full analysis
  - [ ] `detect_tempo(audio: np.ndarray, sr: int) -> float`
  - [ ] `detect_key(audio: np.ndarray, sr: int) -> str`
  - [ ] `calculate_spectral_centroid(audio: np.ndarray, sr: int) -> float`
  - [ ] `calculate_rms_energy(audio: np.ndarray) -> float`
  - [ ] `detect_onsets(audio: np.ndarray, sr: int) -> np.ndarray`

Dependencies:
- `librosa` for audio analysis
- `numpy` for array operations

#### 6. audiomancer/embeddings.py
**Required for**: Semantic search functionality

- [ ] `EmbeddingEngine` class
  - [ ] `__init__(self, config: AudiomancerConfig)`
  - [ ] `generate_embedding(self, audio: np.ndarray) -> np.ndarray`
  - [ ] `index_sample(self, sample_id: str, embedding: np.ndarray) -> None`
  - [ ] `search_similar(self, query_embedding: np.ndarray, top_k: int) -> list[dict]`

Dependencies:
- `torch` and pre-trained model (e.g., CLAP, AudioCLIP)
- `faiss` or `hnswlib` for vector search
- `numpy` for array operations

#### 7. audiomancer/generators.py
**Required for**: Pattern generation functionality

- [ ] `PatternGenerator` class
  - [ ] `__init__(self, config: AudiomancerConfig)`
  - [ ] `generate_tidal_pattern(self, samples: list[str], bpm: float, bars: int) -> str`
    - Generate valid TidalCycles pattern syntax
    - Use provided sample IDs
    - Respect BPM and bar count
  - [ ] `generate_supercollider_pbind(self, samples: list[str], bpm: float) -> str`
    - Generate valid SuperCollider Pbind code
    - Use provided sample IDs
    - Respect BPM

Dependencies:
- Pattern generation logic (possibly LLM-based)
- `audiomancer.config` for configuration

## 📋 Implementation Order

### Phase 1: Core Infrastructure (1-2 days)
1. ✅ Test infrastructure (DONE)
2. Implement `audiomancer/errors.py` (30 tests)
3. Implement `audiomancer/config.py` (20 tests)
4. Run unit tests - should all pass

### Phase 2: Storage Layer (2-3 days)
5. Implement `audiomancer/storage.py` (Database)
6. Create database schema
7. Test with integration tests

### Phase 3: Audio Analysis (3-4 days)
8. Implement `audiomancer/analysis.py`
9. Implement `audiomancer/importers.py`
10. Test sample import workflow

### Phase 4: ML Features (4-5 days)
11. Implement `audiomancer/embeddings.py`
12. Download/setup embedding model
13. Test semantic search

### Phase 5: Pattern Generation (3-4 days)
14. Implement `audiomancer/generators.py`
15. Create pattern templates
16. Test pattern generation

## 🧪 Running Tests During Development

### After implementing errors.py and config.py:
```bash
# Should pass all unit tests
pytest tests/unit/ -v
```

### After implementing storage.py:
```bash
# Un-skip database tests in test_sample_workflow.py
pytest tests/integration/test_sample_workflow.py::TestDatabaseWorkflow -v
```

### After implementing importers.py:
```bash
# Un-skip import tests
pytest tests/integration/test_sample_workflow.py::TestSampleImportWorkflow -v
```

### After implementing embeddings.py:
```bash
# Un-skip embedding tests
pytest tests/integration/test_sample_workflow.py::TestEmbeddingWorkflow -v
```

### After implementing generators.py:
```bash
# Un-skip pattern generation tests
pytest tests/integration/test_sample_workflow.py::TestPatternGenerationWorkflow -v
```

## 📝 Notes

### Test-Driven Development
- Tests are already written and waiting
- Each module implementation should make tests pass
- Tests serve as specification and documentation

### Un-skipping Tests
Remove `@pytest.mark.skip(reason="...")` decorator from integration tests as you implement corresponding modules.

### Adding More Tests
As you implement, you'll discover edge cases not covered by current tests. Add them to the test suite to prevent regressions.

### Dependencies
Install required packages:
```bash
pip install pydantic pyyaml sqlalchemy librosa soundfile numpy torch faiss-cpu
```

### Golden Files
After implementation, generate golden files:
```python
from tests.utils import save_golden_file

# After verifying output is correct
save_golden_file(golden_dir / "kick_808_analysis.json", analysis_result)
```

## ✨ Success Criteria

Project is complete when:
- [ ] All 50 unit tests pass
- [ ] All 8 integration tests pass (un-skipped)
- [ ] Code coverage >80%
- [ ] All core functionality documented
- [ ] Example workflows work end-to-end
