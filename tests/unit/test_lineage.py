"""Unit tests for synth lineage tracking."""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime

from audiomancer.generators.lineage import (
    LineageTracker,
    SynthRecord,
    record_synth,
    rate_synth,
    get_synth_lineage,
    get_top_rated,
    get_generation_stats,
)


class TestSynthRecord:
    """Tests for SynthRecord dataclass."""

    def test_create_record(self):
        """Test creating a synth record."""
        record = SynthRecord(
            id="synt_abc123",
            name="tb303_m1",
            parent_ids=["tb303"],
            generation_method="mutation",
            mutation_log=["Saw → Pulse"],
        )

        assert record.id == "synt_abc123"
        assert record.name == "tb303_m1"
        assert record.parent_ids == ["tb303"]
        assert record.generation_method == "mutation"
        assert record.mutation_log == ["Saw → Pulse"]
        assert record.user_rating is None
        assert record.user_notes is None
        assert isinstance(record.created_at, datetime)

    def test_record_with_rating(self):
        """Test record with user rating."""
        record = SynthRecord(
            id="synt_abc123",
            name="tb303_m1",
            parent_ids=["tb303"],
            generation_method="mutation",
            mutation_log=["Saw → Pulse"],
            user_rating=5,
            user_notes="Perfect acid sound",
        )

        assert record.user_rating == 5
        assert record.user_notes == "Perfect acid sound"


class TestLineageTracker:
    """Tests for LineageTracker class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def tracker(self, temp_db):
        """Create tracker with temporary database."""
        return LineageTracker(db_path=temp_db)

    def test_init_creates_db(self, temp_db):
        """Test initialization creates database file."""
        tracker = LineageTracker(db_path=temp_db)

        # Database should be created on first save
        assert tracker.db_path == temp_db

    def test_record_synth(self, tracker):
        """Test recording a synth."""
        tracker.record_synth(
            synth_id="synt_m1",
            name="tb303_m1",
            parent_ids=["tb303"],
            generation_method="mutation",
            mutation_log=["Saw → Pulse"],
        )

        # Should be in records
        assert "synt_m1" in tracker._records
        record = tracker._records["synt_m1"]
        assert record.name == "tb303_m1"
        assert record.parent_ids == ["tb303"]

    def test_record_multiple_synths(self, tracker):
        """Test recording multiple synths."""
        tracker.record_synth(
            "synt_1", "synth1", [], "original", []
        )
        tracker.record_synth(
            "synt_2", "synth2", ["synt_1"], "mutation", ["mod1"]
        )
        tracker.record_synth(
            "synt_3", "synth3", ["synt_1"], "mutation", ["mod2"]
        )

        assert len(tracker._records) == 3

    def test_rate_synth(self, tracker):
        """Test rating a synth."""
        tracker.record_synth(
            "synt_m1", "tb303_m1", ["tb303"], "mutation", []
        )

        tracker.rate_synth("synt_m1", score=5, notes="Excellent!")

        record = tracker._records["synt_m1"]
        assert record.user_rating == 5
        assert record.user_notes == "Excellent!"

    def test_rate_synth_invalid_score(self, tracker):
        """Test rating with invalid score raises error."""
        tracker.record_synth("synt_m1", "tb303_m1", [], "mutation", [])

        with pytest.raises(ValueError) as exc_info:
            tracker.rate_synth("synt_m1", score=6)

        assert "1-5" in str(exc_info.value)

        with pytest.raises(ValueError):
            tracker.rate_synth("synt_m1", score=0)

    def test_rate_nonexistent_synth(self, tracker):
        """Test rating nonexistent synth raises error."""
        with pytest.raises(KeyError) as exc_info:
            tracker.rate_synth("nonexistent", score=5)

        assert "not found" in str(exc_info.value)

    def test_get_lineage_simple(self, tracker):
        """Test getting lineage for simple parent-child."""
        tracker.record_synth("synt_root", "root", [], "original", [])
        tracker.record_synth("synt_child", "child", ["synt_root"], "mutation", [])

        lineage = tracker.get_lineage("synt_child")

        assert lineage["synth_id"] == "synt_child"
        assert lineage["ancestors"] == ["synt_root"]
        assert lineage["generation"] == 1
        assert lineage["descendants"] == []

    def test_get_lineage_multi_generation(self, tracker):
        """Test lineage with multiple generations."""
        # Create a chain: root → gen1 → gen2 → gen3
        tracker.record_synth("synt_root", "root", [], "original", [])
        tracker.record_synth("synt_gen1", "gen1", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_gen2", "gen2", ["synt_gen1"], "mutation", [])
        tracker.record_synth("synt_gen3", "gen3", ["synt_gen2"], "mutation", [])

        lineage = tracker.get_lineage("synt_gen3")

        assert lineage["ancestors"] == ["synt_root", "synt_gen1", "synt_gen2"]
        assert lineage["generation"] == 3
        assert lineage["descendants"] == []

    def test_get_lineage_with_descendants(self, tracker):
        """Test lineage includes descendants."""
        tracker.record_synth("synt_root", "root", [], "original", [])
        tracker.record_synth("synt_child1", "child1", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_child2", "child2", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_grandchild", "gc", ["synt_child1"], "mutation", [])

        lineage = tracker.get_lineage("synt_root")

        assert lineage["generation"] == 0  # Root has generation 0
        assert "synt_child1" in lineage["descendants"]
        assert "synt_child2" in lineage["descendants"]
        assert "synt_grandchild" in lineage["descendants"]

    def test_get_lineage_family_tree(self, tracker):
        """Test family tree structure."""
        tracker.record_synth("synt_root", "root", [], "original", [])
        tracker.record_synth("synt_child1", "child1", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_child2", "child2", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_grandchild", "gc", ["synt_child1"], "mutation", [])

        lineage = tracker.get_lineage("synt_root")

        tree = lineage["family_tree"]
        assert "synt_child1" in tree
        assert "synt_child2" in tree
        assert "synt_grandchild" in tree["synt_child1"]

    def test_get_lineage_nonexistent(self, tracker):
        """Test getting lineage for nonexistent synth raises error."""
        with pytest.raises(KeyError):
            tracker.get_lineage("nonexistent")

    def test_get_top_rated(self, tracker):
        """Test getting top rated synths."""
        tracker.record_synth("synt_1", "s1", [], "original", [])
        tracker.record_synth("synt_2", "s2", [], "original", [])
        tracker.record_synth("synt_3", "s3", [], "original", [])

        tracker.rate_synth("synt_1", 5)
        tracker.rate_synth("synt_2", 3)
        tracker.rate_synth("synt_3", 4)

        top = tracker.get_top_rated(limit=2)

        assert len(top) == 2
        assert top[0]["id"] == "synt_1"
        assert top[0]["user_rating"] == 5
        assert top[1]["id"] == "synt_3"
        assert top[1]["user_rating"] == 4

    def test_get_top_rated_with_min_rating(self, tracker):
        """Test filtering by minimum rating."""
        tracker.record_synth("synt_1", "s1", [], "original", [])
        tracker.record_synth("synt_2", "s2", [], "original", [])
        tracker.record_synth("synt_3", "s3", [], "original", [])

        tracker.rate_synth("synt_1", 5)
        tracker.rate_synth("synt_2", 3)
        tracker.rate_synth("synt_3", 4)

        top = tracker.get_top_rated(min_rating=4)

        assert len(top) == 2
        assert all(r["user_rating"] >= 4 for r in top)

    def test_get_top_rated_unrated(self, tracker):
        """Test top rated with unrated synths."""
        tracker.record_synth("synt_1", "s1", [], "original", [])
        tracker.record_synth("synt_2", "s2", [], "original", [])

        # No ratings
        top = tracker.get_top_rated()

        assert len(top) == 0

    def test_get_generation_stats_empty(self, tracker):
        """Test generation stats with empty database."""
        stats = tracker.get_generation_stats()

        assert stats["total_synths"] == 0
        assert stats["original_synths"] == 0
        assert stats["mutated_synths"] == 0
        assert stats["crossover_synths"] == 0
        assert stats["max_generation"] == 0
        assert stats["avg_generation"] == 0.0

    def test_get_generation_stats_basic(self, tracker):
        """Test generation statistics."""
        tracker.record_synth("synt_root", "root", [], "original", [])
        tracker.record_synth("synt_m1", "m1", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_m2", "m2", ["synt_root"], "mutation", [])
        tracker.record_synth("synt_cross", "cross", ["synt_m1", "synt_m2"], "crossover", [])

        stats = tracker.get_generation_stats()

        assert stats["total_synths"] == 4
        assert stats["original_synths"] == 1
        assert stats["mutated_synths"] == 2
        assert stats["crossover_synths"] == 1
        assert stats["max_generation"] == 2  # crossover is generation 2

    def test_get_generation_stats_with_ratings(self, tracker):
        """Test generation stats includes average rating."""
        tracker.record_synth("synt_1", "s1", [], "original", [])
        tracker.record_synth("synt_2", "s2", [], "original", [])
        tracker.record_synth("synt_3", "s3", [], "original", [])

        tracker.rate_synth("synt_1", 5)
        tracker.rate_synth("synt_2", 3)
        # synt_3 unrated

        stats = tracker.get_generation_stats()

        # Average of 5 and 3 is 4.0
        assert stats["avg_rating"] == 4.0

    def test_persistence_save_and_load(self, temp_db):
        """Test database persists across instances."""
        # Create first tracker and add data
        tracker1 = LineageTracker(db_path=temp_db)
        tracker1.record_synth("synt_1", "s1", [], "original", [])
        tracker1.rate_synth("synt_1", 5, "Great!")

        # Create new tracker instance (should load from disk)
        tracker2 = LineageTracker(db_path=temp_db)

        assert "synt_1" in tracker2._records
        record = tracker2._records["synt_1"]
        assert record.name == "s1"
        assert record.user_rating == 5
        assert record.user_notes == "Great!"

    def test_persistence_datetime_roundtrip(self, temp_db):
        """Test datetime is preserved across save/load."""
        tracker1 = LineageTracker(db_path=temp_db)
        tracker1.record_synth("synt_1", "s1", [], "original", [])

        original_time = tracker1._records["synt_1"].created_at

        # Load from disk
        tracker2 = LineageTracker(db_path=temp_db)
        loaded_time = tracker2._records["synt_1"].created_at

        # Should be same time (within microseconds)
        assert original_time.replace(microsecond=0) == loaded_time.replace(microsecond=0)


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    def test_record_synth_convenience(self, temp_db, monkeypatch):
        """Test record_synth convenience function."""
        # Patch get_tracker to use temp db
        from audiomancer.generators import lineage as lineage_module

        tracker = LineageTracker(db_path=temp_db)
        monkeypatch.setattr(lineage_module, "_tracker", tracker)

        record_synth("synt_1", "s1", [], "original", [])

        assert "synt_1" in tracker._records

    def test_rate_synth_convenience(self, temp_db, monkeypatch):
        """Test rate_synth convenience function."""
        from audiomancer.generators import lineage as lineage_module

        tracker = LineageTracker(db_path=temp_db)
        monkeypatch.setattr(lineage_module, "_tracker", tracker)

        tracker.record_synth("synt_1", "s1", [], "original", [])
        rate_synth("synt_1", 5, "Excellent")

        assert tracker._records["synt_1"].user_rating == 5

    def test_get_synth_lineage_convenience(self, temp_db, monkeypatch):
        """Test get_synth_lineage convenience function."""
        from audiomancer.generators import lineage as lineage_module

        tracker = LineageTracker(db_path=temp_db)
        monkeypatch.setattr(lineage_module, "_tracker", tracker)

        tracker.record_synth("synt_root", "root", [], "original", [])
        tracker.record_synth("synt_child", "child", ["synt_root"], "mutation", [])

        lineage = get_synth_lineage("synt_child")

        assert lineage["ancestors"] == ["synt_root"]

    def test_get_top_rated_convenience(self, temp_db, monkeypatch):
        """Test get_top_rated convenience function."""
        from audiomancer.generators import lineage as lineage_module

        tracker = LineageTracker(db_path=temp_db)
        monkeypatch.setattr(lineage_module, "_tracker", tracker)

        tracker.record_synth("synt_1", "s1", [], "original", [])
        tracker.rate_synth("synt_1", 5)

        top = get_top_rated(limit=1)

        assert len(top) == 1
        assert top[0]["user_rating"] == 5

    def test_get_generation_stats_convenience(self, temp_db, monkeypatch):
        """Test get_generation_stats convenience function."""
        from audiomancer.generators import lineage as lineage_module

        tracker = LineageTracker(db_path=temp_db)
        monkeypatch.setattr(lineage_module, "_tracker", tracker)

        tracker.record_synth("synt_1", "s1", [], "original", [])

        stats = get_generation_stats()

        assert stats["total_synths"] == 1
        assert stats["original_synths"] == 1
