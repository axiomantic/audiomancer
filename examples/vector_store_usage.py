"""Example usage of LanceDBVectorStore for audio embeddings.

This example demonstrates:
1. Creating a vector store
2. Adding embeddings (single and batch)
3. Searching for similar samples
4. Using pagination and exclusion filters
5. Different distance metrics
"""

from pathlib import Path
import tempfile
import shutil

from audiomancer.storage import LanceDBVectorStore


def main():
    """Demonstrate vector store operations."""
    # Create temporary database
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Creating vector store at: {temp_dir}")

    try:
        # Initialize store
        store = LanceDBVectorStore(temp_dir)
        print(f"✓ Vector store initialized\n")

        # Example 1: Add single embedding
        print("Example 1: Adding single embedding")
        kick_embedding = [0.8] + [0.1] * 127  # 128-dim vector
        store.add_embedding("smpl_kick001", kick_embedding)
        print("✓ Added kick embedding\n")

        # Example 2: Batch add embeddings
        print("Example 2: Batch adding embeddings")
        items = [
            ("smpl_snare001", [0.2] + [0.8] * 127),
            ("smpl_hihat001", [0.5, 0.5] + [0.1] * 126),
            ("smpl_kick002", [0.75] + [0.15] * 127),  # Similar to kick001
            ("smpl_bass001", [0.1, 0.1, 0.9] + [0.1] * 125),
        ]
        store.add_embeddings_batch(items)
        print(f"✓ Added {len(items)} embeddings in batch\n")

        # Example 3: Search for similar samples
        print("Example 3: Finding similar kicks")
        query = [0.8] + [0.1] * 127  # Same as kick001
        results = store.search_similar(query, limit=3)

        print("Most similar samples:")
        for sample_id, distance in results:
            print(f"  {sample_id}: distance={distance:.4f}")
        print()

        # Example 4: Pagination
        print("Example 4: Paginated search")
        page1 = store.search_similar(query, limit=2, offset=0)
        page2 = store.search_similar(query, limit=2, offset=2)

        print("Page 1 (offset=0, limit=2):")
        for sample_id, distance in page1:
            print(f"  {sample_id}: distance={distance:.4f}")

        print("Page 2 (offset=2, limit=2):")
        for sample_id, distance in page2:
            print(f"  {sample_id}: distance={distance:.4f}")
        print()

        # Example 5: Exclude specific samples
        print("Example 5: Search with exclusions")
        results_excluded = store.search_similar(
            query,
            limit=3,
            exclude_ids=["smpl_kick001"]  # Exclude exact match
        )

        print("Results excluding smpl_kick001:")
        for sample_id, distance in results_excluded:
            print(f"  {sample_id}: distance={distance:.4f}")
        print()

        # Example 6: L2 distance metric
        print("Example 6: Using L2 distance metric")
        results_l2 = store.search_similar(
            query,
            limit=3,
            distance_metric="l2"
        )

        print("L2 distance results:")
        for sample_id, distance in results_l2:
            print(f"  {sample_id}: distance={distance:.4f}")
        print()

        # Example 7: Retrieve specific embedding
        print("Example 7: Retrieving embedding")
        retrieved = store.get_embedding("smpl_kick001")
        print(f"Retrieved embedding dimension: {len(retrieved)}")
        print(f"First 5 values: {retrieved[:5]}\n")

        # Example 8: Delete embedding
        print("Example 8: Deleting embedding")
        deleted = store.delete_embedding("smpl_hihat001")
        print(f"✓ Deleted smpl_hihat001: {deleted}")

        # Verify deletion
        after_delete = store.search_similar(query, limit=10)
        result_ids = [sample_id for sample_id, _ in after_delete]
        print(f"Remaining samples: {result_ids}\n")

        print("All examples completed successfully!")

    except ValueError as e:
        print(f"❌ Validation error: {e}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up temporary database")


if __name__ == "__main__":
    main()
