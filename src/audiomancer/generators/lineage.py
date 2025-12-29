"""Lineage tracking and fitness scoring for evolved synths.

This module tracks the evolutionary history of generated synths, including:
- Parent-child relationships
- Mutation history
- User ratings and feedback
- Generation trees

Example:
    >>> from audiomancer.generators.lineage import (
    ...     record_synth,
    ...     get_synth_lineage,
    ...     rate_synth,
    ...     get_top_rated,
    ... )
    >>>
    >>> # Record new synth
    >>> record_synth("tb303_m1", parent_ids=["tb303"], mutation_log=["Saw → Pulse"])
    >>>
    >>> # Rate synth
    >>> rate_synth("tb303_m1", score=5, notes="Perfect acid sound!")
    >>>
    >>> # Get lineage
    >>> lineage = get_synth_lineage("tb303_m1")
    >>> lineage["ancestors"]
    ['tb303']
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class SynthRecord:
    """Record of a synth in the lineage database.

    Attributes:
        id: Unique synth identifier
        name: SynthDef name
        parent_ids: List of parent synth IDs
        generation_method: How synth was created
        mutation_log: List of applied mutations
        user_rating: User rating 1-5 (None if not rated)
        user_notes: User feedback text
        created_at: Timestamp of creation

    Example:
        >>> record = SynthRecord(
        ...     id="synt_abc123",
        ...     name="tb303_evolved_1",
        ...     parent_ids=["tb303"],
        ...     generation_method="mutation",
        ...     mutation_log=["Saw → Pulse"],
        ...     user_rating=5,
        ...     user_notes="Amazing acid sound",
        ...     created_at=datetime.now(),
        ... )
    """
    id: str
    name: str
    parent_ids: List[str]
    generation_method: str
    mutation_log: List[str]
    user_rating: Optional[int] = None
    user_notes: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class LineageTracker:
    """Tracks synth evolution lineage and fitness scores.

    Stores synth records in a JSON file for persistence across sessions.

    Attributes:
        db_path: Path to lineage database file

    Example:
        >>> tracker = LineageTracker()
        >>> tracker.record_synth("tb303_m1", ["tb303"], ["Saw → Pulse"])
        >>> lineage = tracker.get_lineage("tb303_m1")
        >>> lineage["ancestors"]
        ['tb303']
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize lineage tracker.

        Args:
            db_path: Path to lineage database (defaults to ~/.audiomancer/lineage.json)
        """
        if db_path is None:
            home = Path.home()
            db_dir = home / ".audiomancer"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "lineage.json"

        self.db_path = db_path
        self._records: Dict[str, SynthRecord] = {}
        self._load()

    def _load(self):
        """Load lineage database from disk."""
        if not self.db_path.exists():
            return

        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            for synth_id, record_data in data.items():
                # Convert ISO timestamp back to datetime
                if 'created_at' in record_data:
                    record_data['created_at'] = datetime.fromisoformat(record_data['created_at'])

                self._records[synth_id] = SynthRecord(**record_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Could not load lineage database: {e}")

    def _save(self):
        """Save lineage database to disk."""
        data = {}
        for synth_id, record in self._records.items():
            record_dict = asdict(record)
            # Convert datetime to ISO format for JSON
            if record_dict['created_at']:
                record_dict['created_at'] = record_dict['created_at'].isoformat()
            data[synth_id] = record_dict

        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

    def record_synth(
        self,
        synth_id: str,
        name: str,
        parent_ids: List[str],
        generation_method: str,
        mutation_log: List[str],
    ) -> None:
        """Record a new synth in the lineage database.

        Args:
            synth_id: Unique synth identifier
            name: SynthDef name
            parent_ids: List of parent synth IDs
            generation_method: Creation method (generated/mutation/crossover)
            mutation_log: List of mutations applied

        Example:
            >>> tracker = LineageTracker()
            >>> tracker.record_synth(
            ...     "synt_m1",
            ...     "tb303_m1",
            ...     ["tb303"],
            ...     "mutation",
            ...     ["Saw → Pulse", "cutoff: 1200 → 1440"]
            ... )
        """
        record = SynthRecord(
            id=synth_id,
            name=name,
            parent_ids=parent_ids,
            generation_method=generation_method,
            mutation_log=mutation_log,
        )

        self._records[synth_id] = record
        self._save()

    def rate_synth(
        self,
        synth_id: str,
        score: int,
        notes: Optional[str] = None
    ) -> None:
        """Record user rating for a synth.

        Args:
            synth_id: Synth to rate
            score: Rating 1-5
            notes: Optional feedback text

        Raises:
            ValueError: If score not in range 1-5
            KeyError: If synth_id not found

        Example:
            >>> tracker = LineageTracker()
            >>> tracker.rate_synth("tb303_m1", 5, "Perfect acid sound!")
        """
        if score < 1 or score > 5:
            raise ValueError(f"Rating must be 1-5, got {score}")

        if synth_id not in self._records:
            raise KeyError(f"Synth not found: {synth_id}")

        record = self._records[synth_id]
        record.user_rating = score
        record.user_notes = notes
        self._save()

    def get_lineage(self, synth_id: str) -> Dict[str, Any]:
        """Get full ancestry and descendants for a synth.

        Args:
            synth_id: Synth to trace

        Returns:
            Dictionary with ancestors, descendants, and generation info

        Example:
            >>> tracker = LineageTracker()
            >>> lineage = tracker.get_lineage("tb303_m2")
            >>> lineage
            {
                'synth_id': 'tb303_m2',
                'ancestors': ['tb303', 'tb303_m1'],
                'descendants': ['tb303_m3', 'tb303_m4'],
                'generation': 2,
                'family_tree': {
                    'tb303': {
                        'tb303_m1': {
                            'tb303_m2': {}
                        }
                    }
                }
            }
        """
        if synth_id not in self._records:
            raise KeyError(f"Synth not found: {synth_id}")

        # Trace ancestors
        ancestors = self._get_ancestors(synth_id)

        # Find descendants
        descendants = self._get_descendants(synth_id)

        # Calculate generation (distance from root)
        generation = len(ancestors)

        # Build family tree
        family_tree = self._build_family_tree(synth_id)

        return {
            "synth_id": synth_id,
            "ancestors": ancestors,
            "descendants": descendants,
            "generation": generation,
            "family_tree": family_tree,
            "record": asdict(self._records[synth_id]),
        }

    def _get_ancestors(self, synth_id: str) -> List[str]:
        """Recursively trace ancestors to root."""
        ancestors = []
        current_id = synth_id

        while True:
            record = self._records.get(current_id)
            if not record or not record.parent_ids:
                break

            # Take first parent (could handle multiple parents differently)
            parent_id = record.parent_ids[0]
            ancestors.insert(0, parent_id)  # Insert at start for correct order
            current_id = parent_id

        return ancestors

    def _get_descendants(self, synth_id: str) -> List[str]:
        """Find all children and grandchildren."""
        descendants = []

        for record_id, record in self._records.items():
            if synth_id in record.parent_ids:
                descendants.append(record_id)
                # Recursively get descendants
                descendants.extend(self._get_descendants(record_id))

        return descendants

    def _build_family_tree(self, synth_id: str) -> Dict[str, Any]:
        """Build hierarchical family tree starting from synth."""
        record = self._records.get(synth_id)
        if not record:
            return {}

        tree: Dict[str, Any] = {}

        # Get children
        children = [
            rid for rid, r in self._records.items()
            if synth_id in r.parent_ids
        ]

        for child_id in children:
            tree[child_id] = self._build_family_tree(child_id)

        return tree

    def get_top_rated(
        self,
        limit: int = 10,
        min_rating: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get highest-rated synths.

        Args:
            limit: Maximum number of results
            min_rating: Minimum rating threshold (1-5)

        Returns:
            List of synth records sorted by rating (descending)

        Example:
            >>> tracker = LineageTracker()
            >>> top = tracker.get_top_rated(limit=5, min_rating=4)
            >>> top[0]['user_rating']
            5
        """
        # Filter rated synths
        rated = [
            record for record in self._records.values()
            if record.user_rating is not None
        ]

        # Apply minimum rating filter
        if min_rating is not None:
            rated = [r for r in rated if r.user_rating >= min_rating]

        # Sort by rating (descending)
        rated.sort(key=lambda r: r.user_rating, reverse=True)

        # Convert to dict and limit
        return [asdict(r) for r in rated[:limit]]

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about evolutionary generations.

        Returns:
            Dictionary with generation counts and depth metrics

        Example:
            >>> tracker = LineageTracker()
            >>> stats = tracker.get_generation_stats()
            >>> stats
            {
                'total_synths': 42,
                'original_synths': 5,
                'mutated_synths': 28,
                'crossover_synths': 9,
                'max_generation': 7,
                'avg_generation': 3.2,
                'avg_rating': 4.1,
            }
        """
        total = len(self._records)
        if total == 0:
            return {
                'total_synths': 0,
                'original_synths': 0,
                'mutated_synths': 0,
                'crossover_synths': 0,
                'max_generation': 0,
                'avg_generation': 0.0,
                'avg_rating': 0.0,
            }

        # Count by generation method
        original = sum(1 for r in self._records.values() if r.generation_method == "original")
        mutated = sum(1 for r in self._records.values() if r.generation_method == "mutation")
        crossover = sum(1 for r in self._records.values() if r.generation_method == "crossover")

        # Calculate generation depths
        generations = []
        for synth_id in self._records.keys():
            ancestors = self._get_ancestors(synth_id)
            generations.append(len(ancestors))

        max_gen = max(generations) if generations else 0
        avg_gen = sum(generations) / len(generations) if generations else 0.0

        # Calculate average rating
        rated = [r.user_rating for r in self._records.values() if r.user_rating is not None]
        avg_rating = sum(rated) / len(rated) if rated else 0.0

        return {
            'total_synths': total,
            'original_synths': original,
            'mutated_synths': mutated,
            'crossover_synths': crossover,
            'max_generation': max_gen,
            'avg_generation': round(avg_gen, 2),
            'avg_rating': round(avg_rating, 2),
        }


# Global singleton instance
_tracker: Optional[LineageTracker] = None


def get_tracker() -> LineageTracker:
    """Get global lineage tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = LineageTracker()
    return _tracker


# Convenience functions using global tracker

def record_synth(
    synth_id: str,
    name: str,
    parent_ids: List[str],
    generation_method: str,
    mutation_log: List[str],
) -> None:
    """Record a new synth in the lineage database.

    See LineageTracker.record_synth for details.
    """
    tracker = get_tracker()
    tracker.record_synth(synth_id, name, parent_ids, generation_method, mutation_log)


def rate_synth(synth_id: str, score: int, notes: Optional[str] = None) -> None:
    """Record user rating for a synth.

    See LineageTracker.rate_synth for details.
    """
    tracker = get_tracker()
    tracker.rate_synth(synth_id, score, notes)


def get_synth_lineage(synth_id: str) -> Dict[str, Any]:
    """Get full ancestry and descendants for a synth.

    See LineageTracker.get_lineage for details.
    """
    tracker = get_tracker()
    return tracker.get_lineage(synth_id)


def get_top_rated(limit: int = 10, min_rating: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get highest-rated synths.

    See LineageTracker.get_top_rated for details.
    """
    tracker = get_tracker()
    return tracker.get_top_rated(limit, min_rating)


def get_generation_stats() -> Dict[str, Any]:
    """Get statistics about evolutionary generations.

    See LineageTracker.get_generation_stats for details.
    """
    tracker = get_tracker()
    return tracker.get_generation_stats()
