#!/usr/bin/env python3
"""Regression detection for audiomancer benchmarks.

Compares current benchmark results against baseline.json and fails if
performance has regressed by more than the allowed threshold.

Usage:
    python check_regression.py <current_results.json> [--threshold 20]

Exit codes:
    0: No regression detected
    1: Regression detected (fails CI)
    2: Error (missing files, invalid data, etc.)
"""

import json
import sys
from pathlib import Path
from typing import Optional
import argparse


class RegressionChecker:
    """Checks for performance regressions against baseline."""

    def __init__(self, threshold_percent: float = 20.0):
        """Initialize checker.

        Args:
            threshold_percent: Maximum allowed performance regression (%)
        """
        self.threshold_percent = threshold_percent
        self.regressions: list[dict] = []
        self.improvements: list[dict] = []

    def load_results(self, filepath: Path) -> dict:
        """Load benchmark results from JSON file.

        Args:
            filepath: Path to results JSON

        Returns:
            Parsed results dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If invalid JSON
        """
        with open(filepath) as f:
            return json.load(f)

    def find_benchmark(self, results: dict, operation: str, n: int) -> Optional[dict]:
        """Find matching benchmark in results.

        Args:
            results: Benchmark results dictionary
            operation: Operation name
            n: Number of items

        Returns:
            Benchmark dict if found, None otherwise
        """
        for benchmark in results.get("benchmarks", []):
            if benchmark["operation"] == operation and benchmark["n"] == n:
                return benchmark
        return None

    def calculate_regression(
        self,
        baseline_ms: float,
        current_ms: float
    ) -> float:
        """Calculate regression percentage.

        Args:
            baseline_ms: Baseline time in milliseconds
            current_ms: Current time in milliseconds

        Returns:
            Regression percentage (positive = slower, negative = faster)
        """
        if baseline_ms == 0:
            return 0.0
        return ((current_ms - baseline_ms) / baseline_ms) * 100

    def check_results(
        self,
        baseline: dict,
        current: dict
    ) -> bool:
        """Check for regressions between baseline and current results.

        Args:
            baseline: Baseline benchmark results
            current: Current benchmark results

        Returns:
            True if no regressions detected, False otherwise
        """
        self.regressions = []
        self.improvements = []

        baseline_benchmarks = baseline.get("benchmarks", [])
        current_benchmarks = current.get("benchmarks", [])

        print("\nComparing benchmarks against baseline:")
        print("=" * 100)
        print(
            f"{'Operation':<35} {'n':>7} {'Baseline':>12} {'Current':>12} "
            f"{'Change':>10} {'Status':>10}"
        )
        print("=" * 100)

        for baseline_bench in baseline_benchmarks:
            operation = baseline_bench["operation"]
            n = baseline_bench["n"]

            current_bench = self.find_benchmark(current, operation, n)

            if current_bench is None:
                print(
                    f"{operation:<35} {n:>7} {'':>12} {'MISSING':>12} "
                    f"{'':>10} {'SKIP':>10}"
                )
                continue

            # Compare p95 latency (more stable than mean)
            baseline_p95 = baseline_bench["p95_ms"]
            current_p95 = current_bench["p95_ms"]

            regression_pct = self.calculate_regression(baseline_p95, current_p95)

            # Determine status
            if abs(regression_pct) < 5.0:
                status = "✓ OK"
                symbol = "~"
            elif regression_pct > self.threshold_percent:
                status = "✗ REGRESS"
                symbol = "▲"
                self.regressions.append({
                    "operation": operation,
                    "n": n,
                    "baseline_p95_ms": baseline_p95,
                    "current_p95_ms": current_p95,
                    "regression_percent": regression_pct,
                })
            elif regression_pct > 0:
                status = "⚠ SLOWER"
                symbol = "△"
            else:
                status = "✓ FASTER"
                symbol = "▼"
                self.improvements.append({
                    "operation": operation,
                    "n": n,
                    "baseline_p95_ms": baseline_p95,
                    "current_p95_ms": current_p95,
                    "improvement_percent": abs(regression_pct),
                })

            # Format change string
            if regression_pct > 0:
                change_str = f"{symbol}{regression_pct:+.1f}%"
            else:
                change_str = f"{symbol}{regression_pct:.1f}%"

            print(
                f"{operation:<35} {n:>7} {baseline_p95:>10.2f}ms {current_p95:>10.2f}ms "
                f"{change_str:>10} {status:>10}"
            )

        print("=" * 100)

        return len(self.regressions) == 0

    def print_summary(self) -> None:
        """Print regression check summary."""
        print("\nRegression Check Summary:")
        print("-" * 100)

        if self.regressions:
            print(f"\n✗ {len(self.regressions)} REGRESSION(S) DETECTED (threshold: {self.threshold_percent}%):")
            for reg in self.regressions:
                print(
                    f"  - {reg['operation']} (n={reg['n']}): "
                    f"{reg['baseline_p95_ms']:.2f}ms → {reg['current_p95_ms']:.2f}ms "
                    f"({reg['regression_percent']:+.1f}%)"
                )
        else:
            print(f"✓ No regressions detected (threshold: {self.threshold_percent}%)")

        if self.improvements:
            print(f"\n✓ {len(self.improvements)} IMPROVEMENT(S):")
            for imp in self.improvements:
                print(
                    f"  - {imp['operation']} (n={imp['n']}): "
                    f"{imp['baseline_p95_ms']:.2f}ms → {imp['current_p95_ms']:.2f}ms "
                    f"(-{imp['improvement_percent']:.1f}%)"
                )

        print("-" * 100)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0=pass, 1=fail, 2=error)
    """
    parser = argparse.ArgumentParser(
        description="Check for performance regressions against baseline"
    )
    parser.add_argument(
        "current",
        type=Path,
        help="Path to current benchmark results JSON"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).parent / "baseline.json",
        help="Path to baseline results JSON (default: baseline.json)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Regression threshold percentage (default: 20%%)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any slowdown (threshold=0%%)"
    )

    args = parser.parse_args()

    # Strict mode overrides threshold
    if args.strict:
        args.threshold = 0.0

    # Validate files exist
    if not args.baseline.exists():
        print(f"Error: Baseline file not found: {args.baseline}", file=sys.stderr)
        print("\nRun 'python benchmarks/run_benchmarks.py' to create baseline.", file=sys.stderr)
        return 2

    if not args.current.exists():
        print(f"Error: Current results file not found: {args.current}", file=sys.stderr)
        return 2

    # Load results
    try:
        checker = RegressionChecker(threshold_percent=args.threshold)
        baseline = checker.load_results(args.baseline)
        current = checker.load_results(args.current)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error loading results: {e}", file=sys.stderr)
        return 2

    # Check for regressions
    passed = checker.check_results(baseline, current)
    checker.print_summary()

    if passed:
        print("\n✓ All benchmarks passed!")
        return 0
    else:
        print(f"\n✗ Performance regressions detected (threshold: {args.threshold}%)")
        print("Consider investigating and optimizing before committing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
