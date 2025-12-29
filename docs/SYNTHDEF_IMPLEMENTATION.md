# SynthDef Parser and Storage Implementation

## Overview

This document describes the SuperCollider SynthDef parsing and storage implementation for audiomancer.

## Components Implemented

### 1. SynthDef Parser (`src/audiomancer/analyzers/synthdef.py`)

A robust parser for SuperCollider SynthDef files with:

- **Primary parsing**: Uses regex-based extraction (sclang subprocess parsing prepared but not fully implemented)
- **Fallback mechanism**: Graceful degradation when sclang is unavailable
- **Security**: No `shell=True`, always sets subprocess timeouts
- **Comprehensive extraction**:
  - SynthDef name
  - Control parameters with default values
  - UGen usage detection
  - Gate and envelope detection
  - Output channel count
  - Source code preservation
  - File hash for deduplication

#### Key Functions

```python
parse_synthdef(path: Path, timeout: float = 10.0) -> SynthDefInfo
```
Main parsing function with timeout protection.

```python
categorize_synthdef(info: SynthDefInfo) -> str
```
Intelligent categorization based on UGens and controls:
- **bass**: Synths with filters (MoogFF, RLPF)
- **lead**: Pitched synths with envelopes and gate
- **pad**: Long sustained synths (uses ASR envelopes)
- **drum**: Percussive synths without gate
- **fx**: Effect processors, noise generators

#### Data Structures

```python
@dataclass
class SynthControl:
    name: str
    default_value: float
    spec: Optional[str] = None
    description: Optional[str] = None

@dataclass
class SynthDefInfo:
    name: str
    file_path: str
    file_hash: str
    num_channels: int
    has_gate: bool
    has_envelope: bool
    ugens_used: list[str]
    controls: list[SynthControl]
    source_code: str
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
```

### 2. SynthStore (`src/audiomancer/storage/synth_store.py`)

SQLite-based storage for SynthDef metadata following the same patterns as SampleStore:

- **CRUD operations**: add, get, update, delete
- **Retrieval methods**: by ID, name, path, or hash
- **Search & filtering**: by category, name, has_gate
- **Pagination**: limit and offset support
- **Lineage tracking**: parent-child synth relationships
- **JSON serialization**: for complex fields (controls, characteristics, categorization)
- **Atomic operations**: proper transaction handling with rollback

#### Key Methods

```python
add(synth: dict) -> str
get(synth_id: str) -> Optional[dict]
get_by_name(name: str) -> Optional[dict]
get_by_path(file_path: str) -> Optional[dict]
get_by_hash(file_hash: str) -> Optional[dict]
update(synth_id: str, updates: dict) -> bool
delete(synth_id: str) -> bool
search(query, category, has_gate, limit, offset) -> list[dict]
count(query, category, has_gate) -> int
add_lineage(synth_id, parent_synth_id, contribution_weight) -> None
get_lineage(synth_id) -> list[dict]
```

## Database Schema

The implementation uses the existing `Synth` and `SynthLineage` tables from `db.py`:

```sql
CREATE TABLE synths (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    file_path TEXT UNIQUE NOT NULL,
    file_hash TEXT UNIQUE NOT NULL,
    characteristics TEXT,  -- JSON
    categorization TEXT,   -- JSON
    source_code TEXT NOT NULL,
    controls TEXT,         -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE synth_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synth_id TEXT NOT NULL,
    parent_synth_id TEXT NOT NULL,
    contribution_weight REAL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    FOREIGN KEY(synth_id) REFERENCES synths(id) ON DELETE CASCADE,
    FOREIGN KEY(parent_synth_id) REFERENCES synths(id) ON DELETE CASCADE
);
```

## Test Coverage

### Parser Tests (`tests/unit/test_synthdef_parser.py`)

18 tests covering:
- Parsing simple_sine.scd fixture
- Parsing tb303.scd fixture (complex acid bass)
- Error handling (nonexistent file, invalid extension)
- Source code preservation
- Hash consistency
- Regex fallback parser
- Categorization logic (bass, lead, pad, drum, fx)
- Data structure creation

### Storage Tests (`tests/unit/test_synth_store.py`)

28 tests covering:
- Add operations with validation
- Duplicate detection (name and hash)
- Retrieval by ID, name, path, hash
- Updates with timestamp tracking
- Deletion
- Search and filtering
- Pagination
- Count operations
- Lineage tracking (single and multiple parents)

**All 46 tests pass.**

## Usage Examples

### Parsing a SynthDef

```python
from pathlib import Path
from audiomancer.analyzers import parse_synthdef

# Parse SynthDef file
info = parse_synthdef(Path("synths/tb303.scd"))

print(f"Name: {info.name}")
print(f"Category: {info.category}")
print(f"Controls: {[c.name for c in info.controls]}")
print(f"UGens: {info.ugens_used}")
print(f"Has gate: {info.has_gate}")
```

### Storing and Retrieving Synths

```python
from audiomancer.storage import SynthStore

# Initialize store
store = SynthStore("~/.audiomancer/samples.db")

# Prepare synth metadata
synth = {
    "id": f"synth_{info.file_hash[:8]}",
    "name": info.name,
    "file_path": str(info.file_path),
    "file_hash": info.file_hash,
    "source_code": info.source_code,
    "controls": [
        {"name": c.name, "default": c.default_value}
        for c in info.controls
    ],
    "characteristics": {
        "num_channels": info.num_channels,
        "has_gate": info.has_gate,
        "has_envelope": info.has_envelope,
    },
    "categorization": {
        "category": info.category,
        "tags": info.tags,
    },
}

# Add to database
synth_id = store.add(synth)

# Retrieve
retrieved = store.get_by_name("tb303")
print(retrieved["characteristics"])

# Search
bass_synths = store.search(category="bass", limit=10)
for synth in bass_synths:
    print(f"{synth['name']}: {synth['controls']}")
```

### Tracking Synth Evolution

```python
# Track when one synth is derived from another
store.add_lineage(
    synth_id="synth_new_variation",
    parent_synth_id="synth_original",
    contribution_weight=0.8  # 80% based on parent
)

# Get lineage
parents = store.get_lineage("synth_new_variation")
for parent in parents:
    print(f"Parent: {parent['parent_synth_id']}")
    print(f"Contribution: {parent['contribution_weight']}")
```

## Implementation Notes

### Security Considerations

1. **No shell injection**: Never uses `shell=True` in subprocess calls
2. **Timeout protection**: All subprocess calls have timeout limits
3. **Input validation**: File extensions and paths validated before processing
4. **SQL injection prevention**: Uses SQLAlchemy ORM with parameterized queries

### Error Handling

All operations use structured exceptions from `audiomancer.errors`:
- `SynthDefError`: Parsing and validation errors
- `SubprocessTimeoutError`: sclang timeout
- `StorageError`: Database operation errors

All errors include `details` dict for debugging.

### Performance

- **Regex parsing**: Fast, no external dependencies
- **Database indexing**: Indexes on name, file_path, file_hash
- **Batch operations**: Not implemented (single synths typically added)
- **JSON serialization**: Minimal overhead for complex fields

### Future Enhancements

1. **Complete sclang parsing**: Implement full SuperCollider subprocess integration for more accurate metadata extraction
2. **Batch operations**: Add `add_batch()` for importing multiple synths
3. **Vector embeddings**: Generate and store embeddings for similarity search
4. **Parameter range analysis**: Extract min/max ranges from ControlSpecs
5. **UGen graph extraction**: Parse and visualize signal flow
6. **Audio rendering**: Render synth examples for preview

## Test Fixtures

The implementation includes two test SynthDefs:

1. **simple_sine.scd**: Basic sine wave with gate and envelope
2. **tb303.scd**: Complex acid bass with filters, envelopes, and multiple controls

Both are used to verify parser accuracy and categorization logic.

## Integration

The new components are fully integrated:

- Exported from `audiomancer.analyzers` module
- Exported from `audiomancer.storage` module
- Compatible with existing database schema
- Follows existing code patterns and conventions
