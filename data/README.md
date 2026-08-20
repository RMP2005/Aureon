# Data

Centralized data storage for the Aureon platform.

## Structure

```
data/
├── raw/          → Immutable ingested data (append-only)
├── processed/    → Cleaned, transformed datasets
├── features/     → Engineered feature sets for ML
└── snapshots/    → Simulation state checkpoints
```

## Conventions

- **raw/** is append-only — never modify or delete source files
- **processed/** files should be reproducible from raw via documented pipelines
- **features/** datasets should include metadata about transformations applied
- **snapshots/** use timestamped filenames for ordering
- Large binary files (>100 MB) should use Git LFS or external storage
