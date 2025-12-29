-- Migration: 001_initial_schema
-- Description: Create initial tables for samples, synths, patterns, and lineage tracking
-- Created: 2025-01-01

-- Sample metadata table
CREATE TABLE IF NOT EXISTS samples (
    -- Identity
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL UNIQUE,

    -- Basic metadata (required)
    duration_ms REAL NOT NULL,
    sample_rate INTEGER NOT NULL,
    channels INTEGER NOT NULL,
    bit_depth INTEGER NOT NULL,
    file_size_bytes INTEGER NOT NULL,

    -- Spectral features (optional)
    spectral_centroid REAL,
    spectral_bandwidth REAL,
    spectral_rolloff REAL,
    zero_crossing_rate REAL,
    rms_energy REAL,
    dynamic_range REAL,

    -- Rhythm analysis (optional)
    bpm REAL,
    bpm_confidence REAL,
    is_loop INTEGER,

    -- Tonal analysis (optional)
    key TEXT,
    key_confidence REAL,
    tuning_frequency REAL,
    pitch_salience REAL,

    -- ML-derived categories (optional)
    instrument_type TEXT,
    instrument_confidence REAL,
    mood TEXT,
    genre_tags TEXT,

    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Synth definitions table
CREATE TABLE IF NOT EXISTS synths (
    -- Identity
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL UNIQUE,

    -- Characteristics (JSON objects)
    characteristics TEXT,
    categorization TEXT,

    -- Source and controls
    source_code TEXT NOT NULL,
    controls TEXT,

    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Pattern storage table
CREATE TABLE IF NOT EXISTS patterns (
    -- Identity
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,

    -- Pattern data
    midi_data BLOB,
    tidal_code TEXT,
    sc_code TEXT,

    -- Generation parameters (JSON)
    generation_params TEXT,

    -- Lineage tracking
    parent_pattern_id TEXT,
    generation_number INTEGER NOT NULL DEFAULT 0,

    -- User feedback
    rating INTEGER,

    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (parent_pattern_id) REFERENCES patterns(id) ON DELETE SET NULL
);

-- Synth lineage tracking table
CREATE TABLE IF NOT EXISTS synth_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synth_id TEXT NOT NULL,
    parent_synth_id TEXT NOT NULL,
    contribution_weight REAL DEFAULT 0.5,
    created_at TEXT NOT NULL,

    FOREIGN KEY (synth_id) REFERENCES synths(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_synth_id) REFERENCES synths(id) ON DELETE CASCADE,
    UNIQUE(synth_id, parent_synth_id)
);

-- Indexes for common queries

-- Sample indexes
CREATE INDEX IF NOT EXISTS idx_samples_file_path ON samples(file_path);
CREATE INDEX IF NOT EXISTS idx_samples_file_hash ON samples(file_hash);
CREATE INDEX IF NOT EXISTS idx_samples_instrument_type ON samples(instrument_type);
CREATE INDEX IF NOT EXISTS idx_samples_bpm ON samples(bpm) WHERE bpm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_samples_key ON samples(key) WHERE key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_samples_is_loop ON samples(is_loop) WHERE is_loop IS NOT NULL;

-- Synth indexes
CREATE INDEX IF NOT EXISTS idx_synths_name ON synths(name);
CREATE INDEX IF NOT EXISTS idx_synths_file_path ON synths(file_path);
CREATE INDEX IF NOT EXISTS idx_synths_file_hash ON synths(file_hash);

-- Pattern indexes
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(type);
CREATE INDEX IF NOT EXISTS idx_patterns_rating ON patterns(rating) WHERE rating IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_patterns_parent ON patterns(parent_pattern_id) WHERE parent_pattern_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_patterns_generation ON patterns(generation_number);

-- Synth lineage indexes
CREATE INDEX IF NOT EXISTS idx_synth_lineage_child ON synth_lineage(synth_id);
CREATE INDEX IF NOT EXISTS idx_synth_lineage_parent ON synth_lineage(parent_synth_id);
