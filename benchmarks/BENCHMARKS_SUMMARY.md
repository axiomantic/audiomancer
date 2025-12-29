# Audiomancer Benchmarks - Implementation Summary

## What Was Created

A complete performance benchmarking suite for the audiomancer storage layer with:

1. **Benchmark Suite** (`run_benchmarks.py`)
   - Comprehensive performance tests for all storage operations
   - SQLite: insert, batch insert, search operations
   - LanceDB: vector add, similarity search at scale
   - Unified: atomic operations, combined search
   - Statistical analysis with mean, median, std dev, p95, p99
   - Results saved to `baseline.json`

2. **Regression Detection** (`check_regression.py`)
   - Compares current results against baseline
   - Configurable threshold (default: 20% slowdown)
   - Detailed comparison table with visual indicators
   - Exit code 0 (pass) or 1 (fail) for CI integration
   - Strict mode for zero-tolerance regression checks

3. **CLI Integration** (in `src/audiomancer/cli.py`)
   - `audiomancer benchmark` - Run benchmarks
   - `audiomancer benchmark --baseline` - Create baseline
   - `audiomancer benchmark --check` - Check for regressions
   - `audiomancer benchmark --threshold N` - Custom threshold

4. **Documentation**
   - `README.md` - Comprehensive usage guide
   - `baseline.example.json` - Example baseline with targets
   - This summary document

## Files Created

```
benchmarks/
├── __init__.py                  # Package marker
├── run_benchmarks.py            # Main benchmark suite
├── check_regression.py          # Regression detection
├── quick_test.py                # Quick sanity check
├── baseline.example.json        # Example baseline
├── .gitignore                   # Ignore temp files
├── README.md                    # User documentation
└── BENCHMARKS_SUMMARY.md        # This file
```

## Quick Start

### 1. Create Baseline

```bash
cd /path/to/audiomancer
python benchmarks/run_benchmarks.py
```

This creates `benchmarks/baseline.json` with performance metrics.

### 2. Run and Check for Regressions

```bash
# Run benchmarks
python benchmarks/run_benchmarks.py

# Compare against baseline
python benchmarks/check_regression.py baseline.json --threshold 20
```

### 3. Quick Sanity Test

```bash
python benchmarks/quick_test.py
```

Runs a fast 2-second test to verify basic functionality.

## What Gets Benchmarked

### SQLite Operations (db.py)

| Operation | What It Tests | Target p95 |
|-----------|---------------|-----------|
| `sqlite_insert` | Single sample insert | <5ms |
| `sqlite_batch_insert` (n=10) | Small batch performance | <10ms |
| `sqlite_batch_insert` (n=100) | Medium batch performance | <50ms |
| `sqlite_batch_insert` (n=1000) | Large batch performance | <300ms |
| `sqlite_search_by_instrument` | Indexed search | <5ms |
| `sqlite_search_by_bpm_range` | Range query performance | <5ms |
| `sqlite_search_by_key` | Categorical search | <5ms |
| `sqlite_search_combined` | Multiple filters | <5ms |

### LanceDB Operations (vectors.py)

| Operation | What It Tests | Target p95 |
|-----------|---------------|-----------|
| `lancedb_add_batch` (n=100) | Batch vector insert | <100ms |
| `lancedb_add_batch` (n=1000) | Large batch insert | <500ms |
| `lancedb_search` (n=1000) | ANN search in 1K index | <10ms |
| `lancedb_search_scale` (n=100) | Small index performance | <5ms |
| `lancedb_search_scale` (n=1000) | Medium index performance | <10ms |
| `lancedb_search_scale` (n=10000) | Large index performance | <50ms |

### Unified Storage (unified.py)

| Operation | What It Tests | Target p95 |
|-----------|---------------|-----------|
| `unified_add_single` | Atomic add (metadata + embedding) | <10ms |
| `unified_add_batch` (n=10) | Small atomic batch | <20ms |
| `unified_add_batch` (n=100) | Medium atomic batch | <100ms |
| `unified_find_similar` | Combined similarity search | <20ms |

## Metrics Explained

Each benchmark records:

- **mean_ms**: Average execution time (influenced by outliers)
- **median_ms**: Middle value (more stable than mean)
- **std_ms**: Standard deviation (consistency indicator)
- **min_ms**: Fastest execution (best case)
- **max_ms**: Slowest execution (worst case)
- **p95_ms**: 95th percentile (used for regression detection)
- **p99_ms**: 99th percentile (tail latency)

**Why p95?**
- More stable than mean (outliers don't skew it)
- Captures real-world performance (95% of requests)
- Industry standard for SLA/performance targets

## Example Baseline Structure

```json
{
  "timestamp": "2025-12-29T00:00:00.000000",
  "system": {
    "platform": "Darwin",
    "python_version": "3.12.10",
    "processor": "arm"
  },
  "benchmarks": [
    {
      "operation": "sqlite_insert",
      "n": 1,
      "iterations": 100,
      "mean_ms": 2.5,
      "median_ms": 2.3,
      "p95_ms": 3.8,
      "p99_ms": 5.1
    },
    ...
  ]
}
```

## Regression Detection Output

```
Comparing benchmarks against baseline:
================================================================================
Operation                           n   Baseline      Current      Change     Status
================================================================================
sqlite_insert                       1      2.34ms      2.45ms     △+4.7%     ⚠ SLOWER
sqlite_batch_insert               100     28.12ms     27.89ms     ▼-0.8%     ✓ FASTER
lancedb_search_scale            10000     15.23ms     35.67ms    ▲+134.1%    ✗ REGRESS
================================================================================

✗ 1 REGRESSION(S) DETECTED (threshold: 20%):
  - lancedb_search_scale (n=10000): 15.23ms → 35.67ms (+134.1%)
```

Legend:
- `✓` Pass: Within threshold
- `△` Warning: Slower but acceptable
- `▲` Fail: Exceeds threshold
- `▼` Good: Performance improved
- `~` Noise: <5% change

## CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e .

      - name: Run performance benchmarks
        run: python benchmarks/run_benchmarks.py

      - name: Check for regressions
        run: python benchmarks/check_regression.py baseline.json --threshold 20

      - name: Upload benchmark results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: benchmarks/baseline.json
```

## Performance Optimization Tips

If benchmarks reveal issues:

### SQLite Slow

1. **Check indexes**: Ensure filter columns have indexes
2. **Batch operations**: Use `add_batch()` instead of multiple `add()`
3. **Transaction size**: SQLite performs best with 100-1000 item batches
4. **WAL mode**: Consider enabling for concurrent access

### LanceDB Slow

1. **Batch inserts**: Always use `add_embeddings_batch()` for multiple items
2. **Index building**: Search is slow until index is built
3. **Dimensionality**: 128 dims is optimal, higher = slower
4. **Distance metric**: Cosine vs L2 can affect speed

### High Variance (std dev)

Indicates:
- System load (close other apps)
- Garbage collection (increase heap size)
- Disk I/O (check for disk thrashing)
- Thermal throttling (check CPU temperature)

### Regression Debugging

1. **Profile code**: Use `py-spy` or `cProfile`
2. **Check queries**: Use SQLite `EXPLAIN QUERY PLAN`
3. **Monitor resources**: CPU, memory, disk I/O
4. **Compare environments**: Different Python versions, dependencies

## Maintenance Schedule

### Regular Tasks

- **Before PRs**: Run `python benchmarks/quick_test.py` (2 seconds)
- **Before releases**: Full benchmark suite (60 seconds)
- **After optimizations**: Update baseline if improved
- **Monthly**: Review trends, update targets

### When to Update Baseline

✅ Update after:
- Proven performance improvements
- Hardware changes
- Major dependency upgrades

❌ Don't update after:
- Random fluctuations
- Temporary regressions (fix first)
- System load issues

## Troubleshooting

### Benchmarks fail to run

```bash
# Test imports
python -c "
import sys
sys.path.insert(0, 'src')
from audiomancer.storage.db import SampleStore
print('✓ Imports work')
"

# Run quick test
python benchmarks/quick_test.py
```

### Inconsistent results

- Close other applications
- Run multiple times
- Check system temperature
- Try on dedicated hardware

### Missing baseline

```bash
# Create from example
cp benchmarks/baseline.example.json benchmarks/baseline.json

# Or run benchmarks
python benchmarks/run_benchmarks.py
```

## Future Enhancements

Potential improvements:

1. **More operations**: Update, delete, count benchmarks
2. **Concurrency**: Multi-threaded access patterns
3. **Stress tests**: Handle 100K+ samples
4. **Memory profiling**: Track allocation patterns
5. **Custom analyzers**: Benchmark analysis operations
6. **Comparison mode**: Compare multiple baselines
7. **Trend visualization**: Plot performance over time
8. **Auto-tune**: Suggest optimization parameters

## Technical Details

### Why These Benchmarks?

Storage layer is the foundation:
- **Read-heavy**: Search queries dominate usage
- **Write-heavy batches**: Bulk imports common
- **Atomic operations**: Consistency critical
- **Scale testing**: Performance at 10K+ samples

### Statistical Approach

- **10+ iterations**: Statistical significance
- **p95 for regression**: Stable, representative
- **Percentiles**: Capture tail latency
- **Multiple scales**: Catch non-linear scaling

### Design Decisions

1. **In-memory SQLite**: Isolates database performance
2. **Temporary LanceDB**: Clean state each run
3. **Deterministic data**: Consistent test samples
4. **Small suite**: Completes in <60 seconds
5. **P95 threshold**: Balances sensitivity and stability

## Support

For issues or questions:

1. Check `benchmarks/README.md` for detailed documentation
2. Run `python benchmarks/quick_test.py` to verify setup
3. Review system resources (CPU, RAM, disk)
4. Compare against `baseline.example.json` for expected values

## Summary

This benchmark suite provides:

✅ **Comprehensive coverage** of all storage operations
✅ **Statistical rigor** with multiple iterations and percentiles
✅ **Regression detection** with configurable thresholds
✅ **CI integration** ready for GitHub Actions
✅ **Clear documentation** with usage examples
✅ **Fast execution** (60 seconds for full suite)
✅ **Easy maintenance** with example baselines and troubleshooting

Use it to:
- Establish performance baselines
- Detect regressions before they ship
- Guide optimization efforts
- Document performance characteristics
- Ensure consistent performance across changes
