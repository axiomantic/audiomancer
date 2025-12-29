#!/usr/bin/env python3
"""Quick benchmark test to verify functionality."""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audiomancer.storage.db import SampleStore

def main():
    print("=" * 80)
    print("Quick Benchmark Test")
    print("=" * 80)

    # Test SQLite insert
    print("\nTesting SQLite insert...")
    store = SampleStore(":memory:")

    times = []
    for i in range(10):
        sample = {
            "id": f"smpl_test{i:04d}",
            "file_path": f"/test/sample_{i}.wav",
            "file_hash": f"hash{i:016d}",
            "duration_ms": 250.5,
            "sample_rate": 44100,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 44100,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        start = time.perf_counter()
        store.add(sample)
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)

    mean_ms = sum(times) / len(times)
    print(f"Mean insert time: {mean_ms:.2f}ms")
    print(f"Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")

    # Test batch insert
    print("\nTesting batch insert...")
    store2 = SampleStore(":memory:")

    samples = []
    for i in range(100):
        sample = {
            "id": f"smpl_batch{i:04d}",
            "file_path": f"/test/batch_{i}.wav",
            "file_hash": f"hashbatch{i:016d}",
            "duration_ms": 250.5,
            "sample_rate": 44100,
            "channels": 1,
            "bit_depth": 16,
            "file_size_bytes": 44100,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        samples.append(sample)

    start = time.perf_counter()
    store2.add_batch(samples)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"Batch insert (n=100): {elapsed_ms:.2f}ms")
    print(f"Per-item: {elapsed_ms/100:.2f}ms")

    print("\n" + "=" * 80)
    print("✓ Quick test completed successfully")
    print("=" * 80)

if __name__ == "__main__":
    main()
