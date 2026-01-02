# Configuration Examples

## Minimal Global Config

```yaml
# ~/.config/audiomancer/config.yaml
library:
  source_dir: ~/Samples
```

This is the minimum needed to use audiomancer. All other settings use builtin defaults.

## High-Performance Analysis

```yaml
# ~/.config/audiomancer/config.yaml
library:
  copy_workers: 32          # More parallel workers
  max_file_size_mb: 50      # Larger files allowed

analysis:
  max_file_size_mb: 100     # Analyze larger files
  embedding_dim: 256        # Higher quality embeddings
```

## Multiple Sample Sources

```yaml
# ~/.config/audiomancer/config.yaml
sources:
  samples:
    paths:
      - ~/Music/Samples
      - ~/Library/Audio/Sample Libraries
      - /Volumes/External/Samples
  synths:
    paths:
      - ~/synths
      - ~/Library/Application Support/SuperCollider/synthdefs
```

## Project-Specific Override

```yaml
# .audiomancer.yaml (in project directory)
library:
  project_root: ~/Development/my-music
  source_dir: ~/Library/CloudStorage/GoogleDrive/My Music Samples
  max_file_size_mb: 5       # Smaller files for this project

analysis:
  max_file_size_mb: 20      # Override global setting
```

## Custom Storage Locations

```yaml
# ~/.config/audiomancer/config.yaml
storage:
  db_path: ~/Music/audiomancer/database.db
  embeddings_path: ~/Music/audiomancer/embeddings
  models_path: ~/Music/audiomancer/models
```

## Next Steps

- [Configuration System](system.md) - How configuration works
- [API Reference](../api/index.md) - Python configuration API
