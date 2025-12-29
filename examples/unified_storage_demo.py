#!/usr/bin/env python3
"""
Unified Storage Demo

Demonstrates the unified storage layer that coordinates atomic operations
across SQLite (metadata) and LanceDB (embeddings).

This example shows:
1. Adding samples with embeddings atomically
2. Finding similar samples by embedding
3. Combined text and similarity search
4. Atomic rollback on errors
"""

from datetime import datetime
from pathlib import Path
import tempfile

from audiomancer.storage.interfaces import SampleMetadata
from audiomancer.storage.unified import UnifiedSampleStorage


def main():
    # Create temporary storage for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        storage = UnifiedSampleStorage(
            db_path=tmppath / "samples.db",
            embeddings_path=tmppath / "embeddings"
        )

        print("=== Unified Storage Demo ===\n")

        # 1. Add samples with embeddings atomically
        print("1. Adding samples with embeddings...")
        samples_data = [
            ("smpl_kick1", "hash1", "/samples/kicks/808_kick.wav", [0.5] * 128, 125.0, "kick"),
            ("smpl_kick2", "hash2", "/samples/kicks/909_kick.wav", [0.52] * 128, 128.0, "kick"),
            ("smpl_snare", "hash3", "/samples/snares/808_snare.wav", [0.7] * 128, 126.0, "snare"),
            ("smpl_hihat", "hash4", "/samples/hihats/closed_hat.wav", [0.9] * 128, 130.0, "hi-hat"),
        ]

        for sid, hash_val, path, emb, bpm, instr in samples_data:
            sample = SampleMetadata(
                id=sid,
                file_path=path,
                file_hash=hash_val,
                duration_ms=250.5,
                sample_rate=44100,
                channels=1,
                bit_depth=16,
                file_size_bytes=44100,
                bpm=bpm,
                instrument_type=instr,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            storage.add_sample_with_embedding(sample, emb)
            print(f"  Added {sid}: {instr} @ {bpm} BPM")

        print()

        # 2. Find similar samples
        print("2. Finding samples similar to smpl_kick1...")
        similar = storage.find_similar("smpl_kick1", limit=3, exclude_self=True)
        for sample, distance in similar:
            print(f"  {sample['id']}: {sample['instrument_type']} (distance: {distance:.4f})")

        print()

        # 3. Combined text and similarity search
        print("3. Combined search: kicks similar to [0.5] * 128...")
        query_emb = [0.5] * 128
        results = storage.search_by_text_and_similarity(
            query_embedding=query_emb,
            text_query="kick",
            limit=5
        )
        print(f"  Found {len(results)} matching samples:")
        for sample in results:
            print(f"    {sample['id']}: {sample['file_path']}")

        print()

        # 4. Text-only search with filters
        print("4. Text search: samples with BPM 125-128...")
        results = storage.search_by_text_and_similarity(
            text_query="samples",
            filters={"bpm_min": 125.0, "bpm_max": 128.0},
            limit=10
        )
        print(f"  Found {len(results)} samples:")
        for sample in results:
            print(f"    {sample['id']}: {sample['instrument_type']} @ {sample.get('bpm', 'N/A')} BPM")

        print()

        # 5. Demonstrate atomic rollback
        print("5. Demonstrating atomic rollback on invalid embedding...")
        bad_sample = SampleMetadata(
            id="smpl_bad",
            file_path="/samples/bad.wav",
            file_hash="hash_bad",
            duration_ms=100.0,
            sample_rate=44100,
            channels=1,
            bit_depth=16,
            file_size_bytes=22050,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        invalid_emb = [0.1] * 127  # Wrong dimension!

        try:
            storage.add_sample_with_embedding(bad_sample, invalid_emb)
        except Exception as e:
            print(f"  Error caught: {type(e).__name__}: {str(e)}")

        # Verify sample was NOT added (atomic rollback)
        check = storage.get_sample("smpl_bad")
        print(f"  Sample in database after rollback: {check is not None}")
        print(f"  (Expected: False - sample was rolled back)")

        print()

        # 6. Batch operations
        print("6. Batch adding samples...")
        batch_items = [
            (
                SampleMetadata(
                    id=f"smpl_batch_{i}",
                    file_path=f"/samples/batch/sample_{i}.wav",
                    file_hash=f"batch_hash_{i}",
                    duration_ms=200.0,
                    sample_rate=44100,
                    channels=1,
                    bit_depth=16,
                    file_size_bytes=35280,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ),
                [0.6 + i * 0.01] * 128
            )
            for i in range(5)
        ]

        sample_ids = storage.add_samples_with_embeddings_batch(batch_items)
        print(f"  Added {len(sample_ids)} samples in batch")

        print()
        print("=== Demo Complete ===")


if __name__ == "__main__":
    main()
