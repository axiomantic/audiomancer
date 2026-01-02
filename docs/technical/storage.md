# Storage Implementation

This document describes the unified storage architecture combining SQLite and LanceDB.

## Overview

Audiomancer uses a hybrid storage approach:

- **SQLite**: Structured metadata, configuration, lineage
- **LanceDB**: Vector embeddings for similarity search

## Architecture

```
UnifiedSampleStorage
        |
        ├──> SQLite (metadata)
        │    ├── samples table
        │    ├── synths table
        │    └── lineage table
        │
        └──> LanceDB (embeddings)
             └── similarity search index
```

## SQLite Schema

### Samples Table

```sql
CREATE TABLE samples (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_hash TEXT,
    duration_ms REAL,
    sample_rate INTEGER,
    channels INTEGER,
    instrument_type TEXT,
    category TEXT,
    bpm REAL,
    key TEXT,
    spectral_centroid REAL,
    spectral_bandwidth REAL,
    rms_energy REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Synths Table

```sql
CREATE TABLE synths (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    source_code TEXT,
    parameters JSON,
    created_at TIMESTAMP
);
```

## LanceDB Integration

### Embedding Storage

LanceDB stores 128-dimensional audio embeddings for fast similarity search:

```python
from audiomancer.storage import UnifiedSampleStorage

storage = UnifiedSampleStorage("samples.db", "embeddings/")

# Add sample with embedding
sample_id = storage.add_sample_with_embedding(metadata, embedding)

# Find similar samples
results = storage.find_similar(sample_id, limit=10)
```

### Similarity Search

FAISS-powered similarity search:

```python
# Search by sample ID
similar = storage.find_similar("808dk_bd_0", limit=5)

# Results include distance metric
for sample, distance in similar:
    print(f"{sample['file_path']}: similarity={1-distance:.3f}")
```

## Implementation Details

See the following files for more information:

- Original unified storage design: See docs/unified_storage.md (legacy)
- Vector store implementation: See docs/vector_store_implementation.md (legacy)

## API Reference

For Python API documentation, see [Storage API Reference](../api/storage.md).
