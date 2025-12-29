# Unified Storage Integration Layer

## Overview

The `UnifiedSampleStorage` class provides atomic operations across SQLite (metadata) and LanceDB (embeddings), ensuring data consistency through automatic rollback on partial failures.

## Architecture

```
UnifiedSampleStorage
    │
    ├─> SampleStore (SQLite)
    │   └─ Metadata: file_path, duration, BPM, key, etc.
    │
    └─> LanceDBVectorStore
        └─ Embeddings: 128-dim audio feature vectors
```

## Key Features

### 1. Atomic Operations

All operations ensure both stores are updated together or neither is updated:

```python
# Add sample + embedding atomically
sample_id = storage.add_sample_with_embedding(sample, embedding)

# If embedding fails, sample is automatically rolled back
# No orphaned records ever
```

### 2. Automatic Rollback

On any failure, changes are automatically rolled back:

```python
try:
    storage.add_sample_with_embedding(sample, invalid_embedding)
except StorageError:
    # Sample was automatically rolled back from database
    # No cleanup needed
    pass
```

### 3. Batch Operations

Batch operations are fully atomic (all succeed or all fail):

```python
items = [
    (sample1, embedding1),
    (sample2, embedding2),
    (sample3, embedding3),
]

# All added or none added (atomic)
sample_ids = storage.add_samples_with_embeddings_batch(items)
```

### 4. Similarity Search

Find similar samples by embedding distance:

```python
# Find samples similar to a given sample
similar = storage.find_similar(
    "smpl_abc123",
    limit=10,
    exclude_self=True,
    distance_metric="cosine"
)

for sample, distance in similar:
    print(f"{sample['id']}: {distance:.4f}")
```

### 5. Combined Search

Combine text search with similarity search:

```python
# Find kicks similar to query embedding with BPM 120-130
results = storage.search_by_text_and_similarity(
    query_embedding=[0.1] * 128,
    text_query="kick",
    filters={"bpm_min": 120.0, "bpm_max": 130.0},
    limit=20
)
```

## Usage Examples

### Basic Setup

```python
from pathlib import Path
from audiomancer.storage.unified import UnifiedSampleStorage

storage = UnifiedSampleStorage(
    db_path=Path("~/.audiomancer/samples.db"),
    embeddings_path=Path("~/.audiomancer/embeddings")
)
```

### Adding Samples

```python
from audiomancer.storage.interfaces import SampleMetadata
from datetime import datetime

sample = SampleMetadata(
    id="smpl_abc123",
    file_path="/samples/kick.wav",
    file_hash="abc123",
    duration_ms=250.5,
    sample_rate=44100,
    channels=1,
    bit_depth=16,
    file_size_bytes=44100,
    bpm=125.0,
    instrument_type="kick",
    created_at=datetime.now(),
    updated_at=datetime.now(),
)

embedding = [0.1] * 128  # 128-dimensional vector

# Add atomically
sample_id = storage.add_sample_with_embedding(sample, embedding)
```

### Finding Similar Samples

```python
# Find samples similar to a kick drum
similar = storage.find_similar("smpl_kick_808", limit=5)

for sample, distance in similar:
    print(f"{sample['file_path']}: distance={distance:.4f}")
```

### Combined Search

```python
# Find samples that are:
# 1. Similar to query embedding
# 2. Match "kick" in file path
# 3. Have BPM between 120-130
results = storage.search_by_text_and_similarity(
    query_embedding=query_vector,
    text_query="kick",
    filters={
        "bpm_min": 120.0,
        "bpm_max": 130.0,
        "instrument_type": "kick"
    },
    limit=20
)
```

### Batch Operations

```python
items = []
for sample_data, embedding_data in zip(samples, embeddings):
    sample = SampleMetadata(**sample_data)
    items.append((sample, embedding_data))

# Add all atomically (all succeed or all fail)
sample_ids = storage.add_samples_with_embeddings_batch(items)
```

### Deleting Samples

```python
# Delete from both stores
success = storage.delete_sample("smpl_abc123")

# Sample and embedding both removed
assert storage.get_sample("smpl_abc123") is None
assert storage.get_embedding("smpl_abc123") is None
```

## Error Handling

### Duplicate Samples

```python
from audiomancer.errors import DuplicateSampleError

try:
    storage.add_sample_with_embedding(sample, embedding)
except DuplicateSampleError as e:
    print(f"Sample already exists: {e.existing_id}")
```

### Invalid Embeddings

```python
from audiomancer.errors import StorageError

try:
    # Wrong dimension (should be 128)
    storage.add_sample_with_embedding(sample, [0.1] * 127)
except StorageError as e:
    print(f"Invalid embedding: {e}")
    # Sample was automatically rolled back
```

### Missing Embeddings

```python
from audiomancer.errors import SampleNotFoundError

try:
    storage.find_similar("smpl_nonexistent", limit=10)
except SampleNotFoundError as e:
    print(f"No embedding found: {e}")
```

## Implementation Details

### Atomicity Guarantees

1. **Single Add**: If embedding fails, sample is deleted from metadata store
2. **Batch Add**: If any operation fails, all samples are deleted (no partial state)
3. **Delete**: Best-effort deletion from both stores (orphaned embeddings cleaned up)

### Rollback Mechanism

```python
def add_sample_with_embedding(self, sample, embedding):
    sample_id = None
    try:
        # Step 1: Add to metadata store
        sample_id = self.sample_store.add(sample)

        # Step 2: Add to vector store
        self.vector_store.add_embedding(sample_id, embedding)

        return sample_id
    except Exception:
        # Rollback: delete from metadata if added
        if sample_id:
            self.sample_store.delete(sample_id)
        raise
```

### Float Precision

Embeddings are stored as `float32` in LanceDB, so minor precision differences are expected:

```python
# Input
embedding = [0.1] * 128

# Retrieved (float32 precision)
retrieved = storage.get_embedding("smpl_abc123")
# [0.10000000149011612, ...]

# Use approximate comparison
assert abs(retrieved[0] - 0.1) < 1e-6
```

## Testing

Comprehensive integration tests verify:

- Atomic add (both stores updated together)
- Rollback on embedding failure (sample not persisted)
- Rollback on sample failure (no orphaned embeddings)
- Delete removes from both stores
- find_similar returns correct samples with distances
- Batch operations are truly atomic
- Combined search intersects results correctly

Run tests:

```bash
pytest tests/integration/test_unified_storage.py -v
```

## Performance Considerations

### Batch Operations

Use batch operations for better performance:

```python
# Slow (N database transactions)
for sample, emb in items:
    storage.add_sample_with_embedding(sample, emb)

# Fast (1 transaction)
storage.add_samples_with_embeddings_batch(items)
```

### Search Optimization

For large result sets, use pagination:

```python
# Get first page
results = storage.search_by_text_and_similarity(
    query_embedding=emb,
    limit=20,
    offset=0
)

# Get second page
results = storage.search_by_text_and_similarity(
    query_embedding=emb,
    limit=20,
    offset=20
)
```

### Distance Metrics

Choose appropriate distance metric:

- `"cosine"`: Direction similarity (0 = identical, 2 = opposite)
- `"l2"`: Euclidean distance (lower = more similar)

```python
# For normalized embeddings, cosine is usually better
similar = storage.find_similar(
    sample_id,
    limit=10,
    distance_metric="cosine"
)
```

## Future Enhancements

Potential improvements:

1. **Transaction logging**: Record all operations for debugging
2. **Soft deletes**: Mark samples as deleted instead of removing
3. **Embedding versioning**: Store multiple embedding versions per sample
4. **Async operations**: Non-blocking batch operations
5. **Backup/restore**: Atomic backup of both stores together
