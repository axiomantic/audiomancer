#!/usr/bin/env python3
"""Performance baseline benchmarks for audiomancer storage layer.

This benchmark suite measures:
1. SQLite single insert performance
2. SQLite batch insert performance (10, 100, 1000 items)
3. SQLite search operations
4. LanceDB vector search (small, medium, large index)
5. Unified storage atomic operations

All benchmarks run multiple iterations for statistical significance.
Results are saved to baseline.json for regression detection.
"""

import time
import json
import statistics
import sys
import platform
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, TypedDict
import tempfile
import shutil

# Add src to path for importing audiomancer
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audiomancer.storage.db import SampleStore
from audiomancer.storage.vectors import LanceDBVectorStore
from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.storage.interfaces import SampleMetadata


class BenchmarkResult(TypedDict):
    """Results from a single benchmark."""
    operation: str
    n: int
    iterations: int
    mean_ms: float
    median_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    p99_ms: float


class BenchmarkSuite:
    """Manages benchmark execution and result collection."""

    def __init__(self, temp_dir: Path):
        """Initialize benchmark suite with temporary storage.

        Args:
            temp_dir: Temporary directory for benchmark databases
        """
        self.temp_dir = temp_dir
        self.results: list[BenchmarkResult] = []

    def create_test_sample(self, index: int) -> SampleMetadata:
        """Create sample metadata for benchmarking.

        Args:
            index: Unique index for this sample

        Returns:
            SampleMetadata with unique ID and hash
        """
        sample_id = f"smpl_bench{index:08d}"
        file_hash = f"hash{index:016d}"

        sample: SampleMetadata = {
            "id": sample_id,
            "file_path": f"/benchmarks/sample_{index}.wav",
            "file_hash": file_hash,
            "duration_ms": 250.5 + (index % 100),
            "sample_rate": 44100,
            "channels": 1 + (index % 2),
            "bit_depth": 16 if index % 2 == 0 else 24,
            "file_size_bytes": 44100 + (index * 100),
            "spectral_centroid": 1500.0 + (index % 1000),
            "spectral_bandwidth": 800.0,
            "spectral_rolloff": 5000.0,
            "zero_crossing_rate": 0.15,
            "rms_energy": 0.7,
            "dynamic_range": 40.0,
            "bpm": 120.0 + (index % 40),
            "bpm_confidence": 0.95,
            "is_loop": index % 3 == 0,
            "key": ["C", "D", "E", "F", "G", "A", "B"][index % 7],
            "key_confidence": 0.88,
            "tuning_frequency": 440.0,
            "pitch_salience": 0.8,
            "instrument_type": ["kick", "snare", "hihat", "clap", "bass"][index % 5],
            "instrument_confidence": 0.92,
            "mood": ["energetic", "dark", "bright"],
            "genre_tags": ["techno", "house", "dnb"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return sample

    def create_test_embedding(self, index: int) -> list[float]:
        """Create 128-dim embedding for benchmarking.

        Args:
            index: Unique index for varying embeddings

        Returns:
            128-dimensional embedding vector
        """
        import math
        # Create deterministic but varied embeddings
        base = index / 1000.0
        return [math.sin(base + i * 0.1) for i in range(128)]

    def time_operation(
        self,
        operation: Callable[[], None],
        iterations: int = 10
    ) -> list[float]:
        """Time an operation multiple times.

        Args:
            operation: Function to benchmark (no arguments)
            iterations: Number of times to run

        Returns:
            List of execution times in milliseconds
        """
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            operation()
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        return times

    def calculate_percentile(self, values: list[float], percentile: float) -> float:
        """Calculate percentile from sorted values.

        Args:
            values: List of values
            percentile: Percentile to calculate (0-100)

        Returns:
            Value at given percentile
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    def record_result(
        self,
        operation: str,
        n: int,
        times: list[float],
        iterations: int
    ) -> None:
        """Record benchmark result.

        Args:
            operation: Name of operation
            n: Number of items processed
            times: List of execution times in ms
            iterations: Number of iterations run
        """
        result: BenchmarkResult = {
            "operation": operation,
            "n": n,
            "iterations": iterations,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "std_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": self.calculate_percentile(times, 95),
            "p99_ms": self.calculate_percentile(times, 99),
        }
        self.results.append(result)

        # Print result
        print(f"\n{operation} (n={n}):")
        print(f"  Mean: {result['mean_ms']:.2f}ms")
        print(f"  Median: {result['median_ms']:.2f}ms")
        print(f"  P95: {result['p95_ms']:.2f}ms")
        print(f"  P99: {result['p99_ms']:.2f}ms")
        print(f"  Std Dev: {result['std_ms']:.2f}ms")

    def benchmark_sqlite_insert(self, iterations: int = 100) -> None:
        """Benchmark single SQLite inserts.

        Args:
            iterations: Number of insert operations to time
        """
        print(f"\n=== SQLite Single Insert ({iterations} iterations) ===")

        store = SampleStore(":memory:")
        times = []

        for i in range(iterations):
            sample = self.create_test_sample(i)
            start = time.perf_counter()
            store.add(sample)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        self.record_result("sqlite_insert", 1, times, iterations)

    def benchmark_sqlite_batch_insert(
        self,
        batch_size: int = 100,
        iterations: int = 10
    ) -> None:
        """Benchmark batch SQLite inserts.

        Args:
            batch_size: Number of samples per batch
            iterations: Number of batch operations to time
        """
        print(f"\n=== SQLite Batch Insert (batch_size={batch_size}, {iterations} iterations) ===")

        times = []

        for iteration in range(iterations):
            store = SampleStore(":memory:")
            samples = [
                self.create_test_sample(iteration * batch_size + i)
                for i in range(batch_size)
            ]

            start = time.perf_counter()
            store.add_batch(samples)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        self.record_result(
            f"sqlite_batch_insert",
            batch_size,
            times,
            iterations
        )

    def benchmark_sqlite_search(
        self,
        db_size: int = 1000,
        iterations: int = 50
    ) -> None:
        """Benchmark SQLite search operations.

        Args:
            db_size: Number of samples in database
            iterations: Number of search operations
        """
        print(f"\n=== SQLite Search (db_size={db_size}, {iterations} iterations) ===")

        # Setup: Create database with samples
        store = SampleStore(":memory:")
        samples = [self.create_test_sample(i) for i in range(db_size)]
        store.add_batch(samples)

        # Benchmark different search types
        search_types = [
            ("search_by_instrument", {"instrument_type": "kick"}),
            ("search_by_bpm_range", {"bpm_min": 120.0, "bpm_max": 140.0}),
            ("search_by_key", {"key": "C"}),
            ("search_combined", {
                "instrument_type": "kick",
                "bpm_min": 120.0,
                "bpm_max": 140.0,
                "key": "C"
            }),
        ]

        for search_name, filters in search_types:
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                results = store.search(**filters, limit=50)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(elapsed_ms)

            self.record_result(
                f"sqlite_{search_name}",
                db_size,
                times,
                iterations
            )

    def benchmark_lancedb_add(
        self,
        n_embeddings: int = 100,
        iterations: int = 10
    ) -> None:
        """Benchmark LanceDB embedding additions.

        Args:
            n_embeddings: Number of embeddings to add
            iterations: Number of runs
        """
        print(f"\n=== LanceDB Add Embeddings (n={n_embeddings}, {iterations} iterations) ===")

        times = []

        for iteration in range(iterations):
            db_path = self.temp_dir / f"lance_add_{iteration}"
            store = LanceDBVectorStore(db_path)

            embeddings = [
                (f"smpl_{iteration}_{i}", self.create_test_embedding(iteration * n_embeddings + i))
                for i in range(n_embeddings)
            ]

            start = time.perf_counter()
            store.add_embeddings_batch(embeddings)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        self.record_result("lancedb_add_batch", n_embeddings, times, iterations)

    def benchmark_lancedb_search(
        self,
        index_size: int = 1000,
        iterations: int = 50
    ) -> None:
        """Benchmark LanceDB similarity search.

        Args:
            index_size: Number of embeddings in index
            iterations: Number of search operations
        """
        print(f"\n=== LanceDB Search (index_size={index_size}, {iterations} iterations) ===")

        # Setup: Create index
        db_path = self.temp_dir / f"lance_search_{index_size}"
        store = LanceDBVectorStore(db_path)

        embeddings = [
            (f"smpl_{i}", self.create_test_embedding(i))
            for i in range(index_size)
        ]
        store.add_embeddings_batch(embeddings)

        # Benchmark search
        query_embedding = self.create_test_embedding(index_size // 2)

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            results = store.search_similar(query_embedding, limit=10)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        self.record_result(
            "lancedb_search",
            index_size,
            times,
            iterations
        )

    def benchmark_lancedb_search_at_scale(
        self,
        iterations: int = 20
    ) -> None:
        """Benchmark LanceDB at different scales.

        Tests search performance with 100, 1K, 10K vectors.

        Args:
            iterations: Number of iterations per scale
        """
        scales = [100, 1000, 10000]

        for scale in scales:
            print(f"\n=== LanceDB Search at {scale:,} vectors ({iterations} iterations) ===")

            db_path = self.temp_dir / f"lance_scale_{scale}"
            store = LanceDBVectorStore(db_path)

            # Add embeddings in batches
            batch_size = 1000
            for batch_start in range(0, scale, batch_size):
                batch_end = min(batch_start + batch_size, scale)
                embeddings = [
                    (f"smpl_{i}", self.create_test_embedding(i))
                    for i in range(batch_start, batch_end)
                ]
                store.add_embeddings_batch(embeddings)

            # Benchmark search
            query_embedding = self.create_test_embedding(scale // 2)

            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                results = store.search_similar(query_embedding, limit=10)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(elapsed_ms)

            self.record_result(
                f"lancedb_search_scale",
                scale,
                times,
                iterations
            )

    def benchmark_unified_storage(self, iterations: int = 20) -> None:
        """Benchmark unified storage atomic operations.

        Args:
            iterations: Number of operations
        """
        print(f"\n=== Unified Storage (atomic operations, {iterations} iterations) ===")

        # Single add with embedding
        times_single = []
        for i in range(iterations):
            db_path = self.temp_dir / f"unified_single_{i}.db"
            emb_path = self.temp_dir / f"unified_single_{i}_emb"

            storage = UnifiedSampleStorage(db_path, emb_path)
            sample = self.create_test_sample(i)
            embedding = self.create_test_embedding(i)

            start = time.perf_counter()
            storage.add_sample_with_embedding(sample, embedding)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_single.append(elapsed_ms)

        self.record_result(
            "unified_add_single",
            1,
            times_single,
            iterations
        )

        # Batch add with embeddings
        batch_sizes = [10, 100]
        for batch_size in batch_sizes:
            times_batch = []

            for iteration in range(iterations):
                db_path = self.temp_dir / f"unified_batch_{batch_size}_{iteration}.db"
                emb_path = self.temp_dir / f"unified_batch_{batch_size}_{iteration}_emb"

                storage = UnifiedSampleStorage(db_path, emb_path)

                items = [
                    (
                        self.create_test_sample(iteration * batch_size + i),
                        self.create_test_embedding(iteration * batch_size + i)
                    )
                    for i in range(batch_size)
                ]

                start = time.perf_counter()
                storage.add_samples_with_embeddings_batch(items)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times_batch.append(elapsed_ms)

            self.record_result(
                f"unified_add_batch",
                batch_size,
                times_batch,
                iterations
            )

        # Similarity search
        print(f"\n=== Unified Storage Similarity Search ({iterations} iterations) ===")

        db_path = self.temp_dir / "unified_search.db"
        emb_path = self.temp_dir / "unified_search_emb"
        storage = UnifiedSampleStorage(db_path, emb_path)

        # Setup: Add 1000 samples
        setup_items = [
            (self.create_test_sample(i), self.create_test_embedding(i))
            for i in range(1000)
        ]
        storage.add_samples_with_embeddings_batch(setup_items)

        # Benchmark search
        times_search = []
        for i in range(iterations):
            sample_id = f"smpl_bench{i % 1000:08d}"

            start = time.perf_counter()
            results = storage.find_similar(sample_id, limit=10)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_search.append(elapsed_ms)

        self.record_result(
            "unified_find_similar",
            1000,
            times_search,
            iterations
        )


def run_all_benchmarks() -> dict[str, Any]:
    """Run complete benchmark suite.

    Returns:
        Dictionary with benchmark results and system info
    """
    print("=" * 80)
    print("Audiomancer Performance Benchmark Suite")
    print("=" * 80)

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="audiomancer_bench_"))

    try:
        suite = BenchmarkSuite(temp_dir)

        # Run benchmarks
        suite.benchmark_sqlite_insert(iterations=100)
        suite.benchmark_sqlite_batch_insert(batch_size=10, iterations=10)
        suite.benchmark_sqlite_batch_insert(batch_size=100, iterations=10)
        suite.benchmark_sqlite_batch_insert(batch_size=1000, iterations=5)
        suite.benchmark_sqlite_search(db_size=1000, iterations=50)

        suite.benchmark_lancedb_add(n_embeddings=100, iterations=10)
        suite.benchmark_lancedb_add(n_embeddings=1000, iterations=5)
        suite.benchmark_lancedb_search(index_size=1000, iterations=50)
        suite.benchmark_lancedb_search_at_scale(iterations=20)

        suite.benchmark_unified_storage(iterations=20)

        # Collect results
        results = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "processor": platform.processor(),
            },
            "benchmarks": suite.results,
        }

        return results

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    """Run benchmarks and save results."""
    results = run_all_benchmarks()

    # Save to baseline.json
    output_file = Path(__file__).parent / "baseline.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Benchmark results saved to: {output_file}")
    print("=" * 80)

    # Print summary
    print("\nPerformance Summary:")
    print("-" * 80)
    for benchmark in results["benchmarks"]:
        op = benchmark["operation"]
        n = benchmark["n"]
        mean = benchmark["mean_ms"]
        p95 = benchmark["p95_ms"]
        print(f"{op:40s} (n={n:6d}): {mean:8.2f}ms mean, {p95:8.2f}ms p95")


if __name__ == "__main__":
    main()
