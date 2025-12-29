"""SynthStore implementation using SQLAlchemy.

This module provides concrete implementation of synth storage operations
following the same patterns as SampleStore.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from audiomancer.errors import StorageError, SynthDefError
from audiomancer.storage.db import Base, Synth, SynthLineage


class SynthStore:
    """SQLite implementation of synth storage.

    Provides atomic CRUD operations for synth metadata with fail-fast error handling.

    Example:
        >>> store = SynthStore("~/.audiomancer/samples.db")
        >>> synth = {
        ...     "id": "synth_abc123",
        ...     "name": "tb303",
        ...     "file_path": "/synths/tb303.scd",
        ...     "file_hash": "abc123",
        ...     "source_code": "SynthDef(...)",
        ...     "controls": [{"name": "freq", "default": 440.0}],
        ...     "characteristics": {"num_channels": 2, "has_gate": True},
        ... }
        >>> synth_id = store.add(synth)
        >>> retrieved = store.get(synth_id)
        >>> retrieved['name']
        'tb303'
    """

    def __init__(self, db_path: str):
        """Initialize store with database connection.

        Args:
            db_path: Path to SQLite database file (will be created if missing)

        Example:
            >>> store = SynthStore("~/.audiomancer/samples.db")
            >>> store = SynthStore(":memory:")  # In-memory for testing
        """
        # Expand user paths
        if db_path != ":memory:":
            db_path = str(Path(db_path).expanduser().absolute())

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        # Enable foreign key constraints
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create tables
        Base.metadata.create_all(self.engine)

    def _synth_to_dict(self, synth: Synth) -> dict:
        """Convert SQLAlchemy model to dict.

        Args:
            synth: SQLAlchemy Synth instance

        Returns:
            Dictionary with all fields
        """
        return {
            "id": synth.id,
            "name": synth.name,
            "file_path": synth.file_path,
            "file_hash": synth.file_hash,
            "characteristics": json.loads(synth.characteristics) if synth.characteristics else {},
            "categorization": json.loads(synth.categorization) if synth.categorization else {},
            "source_code": synth.source_code,
            "controls": json.loads(synth.controls) if synth.controls else [],
            "created_at": datetime.fromisoformat(synth.created_at),
            "updated_at": datetime.fromisoformat(synth.updated_at),
        }

    def _dict_to_synth(self, synth_dict: dict) -> Synth:
        """Convert dict to SQLAlchemy model.

        Args:
            synth_dict: Synth dictionary

        Returns:
            SQLAlchemy Synth instance ready for database insertion
        """
        # Handle datetime fields
        created_at = synth_dict.get("created_at", datetime.now())
        updated_at = synth_dict.get("updated_at", datetime.now())

        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()

        # Serialize JSON fields
        characteristics = synth_dict.get("characteristics")
        if characteristics is not None:
            characteristics = json.dumps(characteristics)

        categorization = synth_dict.get("categorization")
        if categorization is not None:
            categorization = json.dumps(categorization)

        controls = synth_dict.get("controls")
        if controls is not None:
            controls = json.dumps(controls)

        return Synth(
            id=synth_dict["id"],
            name=synth_dict["name"],
            file_path=synth_dict["file_path"],
            file_hash=synth_dict["file_hash"],
            characteristics=characteristics,
            categorization=categorization,
            source_code=synth_dict["source_code"],
            controls=controls,
            created_at=created_at,
            updated_at=updated_at,
        )

    def add(self, synth: dict) -> str:
        """Add synth to database.

        Args:
            synth: Complete synth metadata to store

        Returns:
            Synth ID (format: "synth_{hash[:8]}")

        Raises:
            StorageError: If synth with same name or hash already exists

        Example:
            >>> synth = {
            ...     "id": "synth_abc123",
            ...     "name": "tb303",
            ...     "file_path": "/synths/tb303.scd",
            ...     "file_hash": "abc123",
            ...     "source_code": "SynthDef(...)",
            ...     "controls": [],
            ... }
            >>> synth_id = store.add(synth)
            >>> synth_id
            "synth_abc123"
        """
        session = self.SessionLocal()
        try:
            # Check for existing synth with same name
            existing = session.query(Synth).filter_by(name=synth["name"]).first()
            if existing:
                raise StorageError(
                    f"Synth with name '{synth['name']}' already exists",
                    details={
                        "existing_id": existing.id,
                        "existing_path": existing.file_path,
                        "name": synth["name"],
                    }
                )

            # Check for existing synth with same hash
            existing = session.query(Synth).filter_by(file_hash=synth["file_hash"]).first()
            if existing:
                raise StorageError(
                    "Synth with same content already exists",
                    details={
                        "existing_id": existing.id,
                        "existing_name": existing.name,
                        "file_hash": synth["file_hash"],
                    }
                )

            db_synth = self._dict_to_synth(synth)
            session.add(db_synth)
            session.commit()
            return db_synth.id

        except StorageError:
            session.rollback()
            raise
        except IntegrityError as e:
            session.rollback()
            raise StorageError(
                "Failed to add synth due to database constraint violation",
                details={"error": str(e), "synth_id": synth.get("id")},
            )
        except Exception as e:
            session.rollback()
            raise StorageError(
                "Unexpected error adding synth to database",
                details={"error": str(e), "synth_id": synth.get("id")},
            )
        finally:
            session.close()

    def get(self, synth_id: str) -> Optional[dict]:
        """Retrieve synth by ID.

        Args:
            synth_id: Synth ID (format: "synth_{hash[:8]}")

        Returns:
            Synth metadata if found, None otherwise

        Example:
            >>> synth = store.get("synth_abc123")
            >>> synth['name']
            'tb303'
            >>> store.get("synth_nonexistent")
            None
        """
        session = self.SessionLocal()
        try:
            synth = session.query(Synth).filter_by(id=synth_id).first()
            if synth:
                return self._synth_to_dict(synth)
            return None
        finally:
            session.close()

    def get_by_name(self, name: str) -> Optional[dict]:
        """Retrieve synth by name.

        Args:
            name: Synth name (e.g., "tb303")

        Returns:
            Synth metadata if found, None otherwise

        Example:
            >>> synth = store.get_by_name("tb303")
            >>> synth['id']
            "synth_abc123"
        """
        session = self.SessionLocal()
        try:
            synth = session.query(Synth).filter_by(name=name).first()
            if synth:
                return self._synth_to_dict(synth)
            return None
        finally:
            session.close()

    def get_by_path(self, file_path: str) -> Optional[dict]:
        """Retrieve synth by file path.

        Args:
            file_path: Absolute path to .scd file

        Returns:
            Synth metadata if found, None otherwise

        Example:
            >>> synth = store.get_by_path("/synths/tb303.scd")
            >>> synth['name']
            'tb303'
        """
        session = self.SessionLocal()
        try:
            synth = session.query(Synth).filter_by(file_path=file_path).first()
            if synth:
                return self._synth_to_dict(synth)
            return None
        finally:
            session.close()

    def get_by_hash(self, file_hash: str) -> Optional[dict]:
        """Retrieve synth by file hash.

        Used for deduplication - check if synth already exists before adding.

        Args:
            file_hash: SHA256 hash of source code

        Returns:
            Synth metadata if found, None otherwise

        Example:
            >>> synth = store.get_by_hash("abc123")
            >>> synth is not None
            True
        """
        session = self.SessionLocal()
        try:
            synth = session.query(Synth).filter_by(file_hash=file_hash).first()
            if synth:
                return self._synth_to_dict(synth)
            return None
        finally:
            session.close()

    def update(self, synth_id: str, updates: dict) -> bool:
        """Update synth fields.

        Only updates specified fields, leaving others unchanged. Automatically
        updates the updated_at timestamp.

        Args:
            synth_id: Synth ID to update
            updates: Dictionary of field names and new values

        Returns:
            True if synth was updated, False if not found

        Example:
            >>> success = store.update(
            ...     "synth_abc123",
            ...     {"characteristics": {"num_channels": 2}}
            ... )
            >>> success
            True
        """
        session = self.SessionLocal()
        try:
            synth = session.query(Synth).filter_by(id=synth_id).first()
            if not synth:
                return False

            # Handle JSON fields
            if "characteristics" in updates and updates["characteristics"] is not None:
                updates["characteristics"] = json.dumps(updates["characteristics"])
            if "categorization" in updates and updates["categorization"] is not None:
                updates["categorization"] = json.dumps(updates["categorization"])
            if "controls" in updates and updates["controls"] is not None:
                updates["controls"] = json.dumps(updates["controls"])

            # Update fields
            for key, value in updates.items():
                if hasattr(synth, key):
                    setattr(synth, key, value)

            # Always update timestamp
            synth.updated_at = datetime.now().isoformat()

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            raise StorageError(
                "Failed to update synth",
                details={"error": str(e), "synth_id": synth_id},
            )
        finally:
            session.close()

    def delete(self, synth_id: str) -> bool:
        """Delete synth from database.

        Args:
            synth_id: Synth ID to delete

        Returns:
            True if synth was deleted, False if not found

        Example:
            >>> success = store.delete("synth_abc123")
            >>> success
            True
        """
        session = self.SessionLocal()
        try:
            synth = session.query(Synth).filter_by(id=synth_id).first()
            if not synth:
                return False

            session.delete(synth)
            session.commit()
            return True

        except Exception as e:
            session.rollback()
            raise StorageError(
                "Failed to delete synth",
                details={"error": str(e), "synth_id": synth_id},
            )
        finally:
            session.close()

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        has_gate: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Search synths with filters and pagination.

        All filters are combined with AND logic. Text query searches name and file_path.

        Args:
            query: Text search in name or file path
            category: Filter by category (bass, lead, pad, drum, fx)
            has_gate: Filter by gate parameter presence
            limit: Maximum results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of matching synths (up to limit)

        Example:
            >>> # Search for bass synths
            >>> results = store.search(category="bass", limit=10)
            >>> len(results) <= 10
            True
        """
        session = self.SessionLocal()
        try:
            query_obj = session.query(Synth)

            # Apply filters
            if query:
                query_obj = query_obj.filter(
                    (Synth.name.like(f"%{query}%")) | (Synth.file_path.like(f"%{query}%"))
                )
            if category:
                # Search in categorization JSON
                query_obj = query_obj.filter(Synth.categorization.like(f'%"{category}"%'))
            if has_gate is not None:
                # Search in characteristics JSON
                gate_str = "true" if has_gate else "false"
                query_obj = query_obj.filter(Synth.characteristics.like(f'%"has_gate": {gate_str}%'))

            # Apply pagination
            results = query_obj.limit(limit).offset(offset).all()

            return [self._synth_to_dict(synth) for synth in results]

        finally:
            session.close()

    def count(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        has_gate: Optional[bool] = None,
    ) -> int:
        """Count synths matching filters.

        Same filter logic as search(), but returns count instead of results.

        Args:
            query: Text search in name or file path
            category: Filter by category
            has_gate: Filter by gate parameter presence

        Returns:
            Number of matching synths

        Example:
            >>> total = store.count(category="bass")
            >>> total
            15
        """
        session = self.SessionLocal()
        try:
            query_obj = session.query(Synth)

            # Apply same filters as search()
            if query:
                query_obj = query_obj.filter(
                    (Synth.name.like(f"%{query}%")) | (Synth.file_path.like(f"%{query}%"))
                )
            if category:
                query_obj = query_obj.filter(Synth.categorization.like(f'%"{category}"%'))
            if has_gate is not None:
                gate_str = "true" if has_gate else "false"
                query_obj = query_obj.filter(Synth.characteristics.like(f'%"has_gate": {gate_str}%'))

            return query_obj.count()

        finally:
            session.close()

    def list_all(self, limit: int = 100) -> list[dict]:
        """List all synths with optional limit.

        Convenience method that calls search() with no filters.

        Args:
            limit: Maximum number of synths to return

        Returns:
            List of synth metadata dictionaries

        Example:
            >>> synths = store.list_all(limit=50)
            >>> len(synths) <= 50
            True
        """
        return self.search(limit=limit)

    def add_lineage(self, synth_id: str, parent_synth_id: str, contribution_weight: float = 0.5) -> None:
        """Record synth lineage (parent-child relationship).

        Used to track synth evolution when one synth is derived from another.

        Args:
            synth_id: Child synth ID
            parent_synth_id: Parent synth ID
            contribution_weight: How much parent contributed (0-1)

        Raises:
            StorageError: If synths don't exist or lineage already recorded

        Example:
            >>> store.add_lineage("synth_new", "synth_original", 0.8)
        """
        session = self.SessionLocal()
        try:
            # Verify both synths exist
            synth = session.query(Synth).filter_by(id=synth_id).first()
            parent = session.query(Synth).filter_by(id=parent_synth_id).first()

            if not synth:
                raise StorageError(
                    f"Synth not found: {synth_id}",
                    details={"synth_id": synth_id}
                )
            if not parent:
                raise StorageError(
                    f"Parent synth not found: {parent_synth_id}",
                    details={"parent_synth_id": parent_synth_id}
                )

            # Create lineage record
            lineage = SynthLineage(
                synth_id=synth_id,
                parent_synth_id=parent_synth_id,
                contribution_weight=contribution_weight,
                created_at=datetime.now().isoformat(),
            )

            session.add(lineage)
            session.commit()

        except StorageError:
            session.rollback()
            raise
        except IntegrityError as e:
            session.rollback()
            raise StorageError(
                "Failed to add lineage (may already exist)",
                details={
                    "error": str(e),
                    "synth_id": synth_id,
                    "parent_synth_id": parent_synth_id,
                }
            )
        except Exception as e:
            session.rollback()
            raise StorageError(
                "Unexpected error adding lineage",
                details={"error": str(e)},
            )
        finally:
            session.close()

    def get_lineage(self, synth_id: str) -> list[dict]:
        """Get parent synths (lineage) for a synth.

        Args:
            synth_id: Synth ID

        Returns:
            List of parent synth records with contribution weights

        Example:
            >>> parents = store.get_lineage("synth_new")
            >>> parents[0]['parent_synth_id']
            'synth_original'
            >>> parents[0]['contribution_weight']
            0.8
        """
        session = self.SessionLocal()
        try:
            lineages = session.query(SynthLineage).filter_by(synth_id=synth_id).all()

            return [
                {
                    "parent_synth_id": l.parent_synth_id,
                    "contribution_weight": l.contribution_weight,
                    "created_at": datetime.fromisoformat(l.created_at),
                }
                for l in lineages
            ]

        finally:
            session.close()
