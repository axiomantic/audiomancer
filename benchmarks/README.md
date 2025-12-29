# Audiomancer Performance Benchmarks

Comprehensive performance baseline benchmarks for the audiomancer storage layer.

## Overview

This benchmark suite measures the performance of:

1. **SQLite Operations** (db.py)
   - Single insert latency
   - Batch insert throughput (10, 100, 1000 items)
   - Search operations with various filters
   - Query performance at scale

2. **LanceDB Vector Operations** (vectors.py)
   - Embedding insertion (single and batch)
   - Vector similarity search
   - Performance at different scales (100, 1K, 10K vectors)

3. **Unified Storage** (unified.py)
   - Atomic add operations (sample + embedding)
   - Batch atomic operations
   - Combined similarity search

## Quick Start

### Create Baseline

Run benchmarks once to establish performance baseline:

```bash
# Using CLI (recommended)
audiomancer benchmark --baseline

# Or directly
python benchmarks/run_benchmarks.py
```

This creates `benchmarks/baseline.json` with current performance metrics.

### Run and Check for Regressions

Compare current performance against baseline:

```bash
# Using CLI (recommended)
audiomancer benchmark --check

# Or directly
python benchmarks/run_benchmarks.py
python benchmarks/check_regression.py baseline.json
```

Fails if performance regresses by >20% (configurable).

### Custom Threshold

```bash
# Fail on any regression
audiomancer benchmark --check --threshold 0

# Allow up to 30% regression
audiomancer benchmark --check --threshold 30
```

## Benchmark Operations

### SQLite Benchmarks

| Operation | n | Description |
|-----------|---|-------------|
| `sqlite_insert` | 1 | Single sample insert latency |
| `sqlite_batch_insert` | 10 | Batch insert of 10 samples |
| `sqlite_batch_insert` | 100 | Batch insert of 100 samples |
| `sqlite_batch_insert` | 1000 | Batch insert of 1000 samples |
| `sqlite_search_by_instrument` | 1000 | Filter by instrument type |
| `sqlite_search_by_bpm_range` | 1000 | Filter by BPM range |
| `sqlite_search_by_key` | 1000 | Filter by musical key |
| `sqlite_search_combined` | 1000 | Multiple filters combined |

### LanceDB Benchmarks

| Operation | n | Description |
|-----------|---|-------------|
| `lancedb_add_batch` | 100 | Batch add 100 embeddings |
| `lancedb_add_batch` | 1000 | Batch add 1000 embeddings |
| `lancedb_search` | 1000 | Similarity search in 1K index |
| `lancedb_search_scale` | 100 | Search in 100 vector index |
| `lancedb_search_scale` | 1000 | Search in 1K vector index |
| `lancedb_search_scale` | 10000 | Search in 10K vector index |

### Unified Storage Benchmarks

| Operation | n | Description |
|-----------|---|-------------|
| `unified_add_single` | 1 | Atomic add (sample + embedding) |
| `unified_add_batch` | 10 | Atomic batch add 10 items |
| `unified_add_batch` | 100 | Atomic batch add 100 items |
| `unified_find_similar` | 1000 | Similarity search in 1K database |

## Metrics Collected

For each operation, we record:

- **mean_ms**: Average execution time
- **median_ms**: Median execution time (more stable)
- **std_ms**: Standard deviation
- **min_ms**: Fastest execution
- **max_ms**: Slowest execution
- **p95_ms**: 95th percentile latency
- **p99_ms**: 99th percentile latency

Regression detection uses **p95_ms** (more stable than mean, captures tail latency).

## Performance Targets

Based on initial benchmarking (MacBook Pro M1, 16GB RAM):

| Operation | Target p95 | Good | Acceptable |
|-----------|-----------|------|-----------|
| SQLite single insert | <5ms | <3ms | <10ms |
| SQLite batch insert (100) | <50ms | <30ms | <100ms |
| SQLite search | <5ms | <2ms | <10ms |
| LanceDB add (100) | <100ms | <50ms | <200ms |
| LanceDB search (1K index) | <10ms | <5ms | <20ms |
| LanceDB search (10K index) | <50ms | <20ms | <100ms |
| Unified atomic add | <10ms | <5ms | <20ms |
| Unified similarity search | <20ms | <10ms | <40ms |

## Benchmark Duration

Full suite completes in approximately 45-60 seconds:

- SQLite benchmarks: ~10 seconds
- LanceDB benchmarks: ~30 seconds
- Unified storage: ~15 seconds

## Understanding Results

### Good Performance

```
sqlite_insert (n=1): 2.34ms mean, 2.51ms p95
lancedb_search_scale (n=10000): 15.23ms mean, 18.45ms p95
unified_add_single (n=1): 4.56ms mean, 5.12ms p95
```

All operations complete quickly with low variance.

### Performance Issues

```
sqlite_insert (n=1): 15.23ms mean, 45.67ms p95  ⚠ High p95 = inconsistent
lancedb_search_scale (n=10000): 150.45ms mean   ⚠ 3x slower than target
```

High p95 relative to mean indicates:
- Garbage collection pauses
- Disk I/O contention
- Lock contention in SQLite

Large absolute times indicate:
- Inefficient queries (missing indexes)
- Hardware limitations
- System resource contention

## Regression Detection

The `check_regression.py` script compares current results against baseline:

```bash
python benchmarks/check_regression.py <current.json> --threshold 20
```

Exit codes:
- `0`: No regression (CI passes)
- `1`: Regression detected (CI fails)
- `2`: Error (missing files, invalid data)

Example output:

```
Comparing benchmarks against baseline:
================================================================================
Operation                           n   Baseline      Current      Change     Status
================================================================================
sqlite_insert                       1      2.34ms      2.45ms     △+4.7%     ⚠ SLOWER
sqlite_batch_insert               100     28.12ms     27.89ms     ▼-0.8%     ✓ FASTER
lancedb_search_scale            10000     15.23ms     35.67ms    ▲+134.1%    ✗ REGRESS
unified_add_single                  1      4.56ms      4.52ms     ▼-0.9%     ✓ OK
================================================================================

Regression Check Summary:
--------------------------------------------------------------------------------
✗ 1 REGRESSION(S) DETECTED (threshold: 20%):
  - lancedb_search_scale (n=10000): 15.23ms → 35.67ms (+134.1%)
--------------------------------------------------------------------------------

✗ Performance regressions detected (threshold: 20%)
```

Symbols:
- `✓` Green: No regression
- `△` Yellow: Slower but within threshold
- `▲` Red: Regression exceeds threshold
- `▼` Green: Performance improved
- `~` Gray: Change <5% (noise)

## Baseline Management

### When to Update Baseline

Update baseline after:

1. **Intentional optimizations**: Performance improved, lock it in
2. **Hardware changes**: New machine, different specs
3. **Major dependency updates**: SQLAlchemy, LanceDB version bumps
4. **Architectural changes**: Changed indexes, storage format

Don't update after:

1. Random fluctuations: Run multiple times, ensure consistent
2. Temporary regressions: Fix the issue first
3. System load: Close other apps, try again

### How to Update

```bash
# Review current performance
audiomancer benchmark --check

# If acceptable, update baseline
audiomancer benchmark --baseline
git add benchmarks/baseline.json
git commit -m "Update performance baseline after optimization"
```

## CI Integration

Add to GitHub Actions workflow:

```yaml
- name: Performance Regression Check
  run: |
    pip install -e .
    audiomancer benchmark --check --threshold 20
```

Fails the build if performance regresses >20%.

## Troubleshooting

### Benchmarks are slow/flaky

- Close other applications
- Disable background indexing (Spotlight, etc.)
- Run multiple times and compare
- Check system temperature (thermal throttling)

### Inconsistent results

High standard deviation indicates:

- System under load
- Garbage collection interference
- Disk I/O variability
- Try running on dedicated hardware

### Missing baseline.json

```bash
audiomancer benchmark --baseline
```

### Import errors

Ensure audiomancer is installed:

```bash
pip install -e .
```

## Advanced Usage

### Direct Script Usage

```bash
# Run benchmarks
cd benchmarks
python run_benchmarks.py

# Check regressions
python check_regression.py baseline.json --threshold 20

# Strict mode (fail on any slowdown)
python check_regression.py baseline.json --strict
```

### Custom Benchmark Iterations

Edit `run_benchmarks.py` and modify iteration counts:

```python
suite.benchmark_sqlite_insert(iterations=200)  # More samples
suite.benchmark_lancedb_search_at_scale(iterations=50)  # Better stats
```

Higher iterations = better statistical significance, longer runtime.

## Performance Optimization Tips

If benchmarks reveal issues:

1. **SQLite slow inserts**: Check for missing indexes
2. **Batch operations slow**: Increase batch size
3. **Search operations slow**: Add indexes on filter columns
4. **LanceDB search slow at scale**: Consider dimensionality reduction
5. **High variance**: Check for GC pauses, disk I/O bottlenecks

## Maintenance

### Regular Tasks

- Run benchmarks before major releases
- Update baseline after proven optimizations
- Review trends over time (keep historical baselines)
- Add new benchmarks for new features

### Archiving Baselines

Keep historical baselines for trend analysis:

```bash
cp benchmarks/baseline.json benchmarks/baseline_v0.1.0.json
git add benchmarks/baseline_v0.1.0.json
```

## Contributing

When adding new storage operations:

1. Add benchmark to `run_benchmarks.py`
2. Set reasonable performance target
3. Document in this README
4. Update baseline after review
