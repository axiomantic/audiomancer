-- audiomancer SQLite schema
-- Version: 1
-- Created: 2025-01-01

-- Sample metadata table
CREATE TABLE IF NOT EXISTS samples (
    -- Identity
    id TEXT PRIMARY KEY,  -- Format: "smpl_{hash[:8]}"
    file_path TEXT NOT NULL UNIQUE,  -- Absolute path to audio file
    file_hash TEXT NOT NULL UNIQUE,  -- SHA256 hash for deduplication

    -- Basic metadata (required)
    duration_ms REAL NOT NULL,  -- Duration in milliseconds
    sample_rate INTEGER NOT NULL,  -- Sample rate in Hz (44100, 48000, etc.)
    channels INTEGER NOT NULL,  -- Number of channels (1=mono, 2=stereo)
    bit_depth INTEGER NOT NULL,  -- Bit depth (16, 24, 32)
    file_size_bytes INTEGER NOT NULL,  -- File size in bytes

    -- Spectral features (optional)
    spectral_centroid REAL,  -- Brightness in Hz
    spectral_bandwidth REAL,  -- Frequency spread in Hz
    spectral_rolloff REAL,  -- High frequency energy in Hz
    zero_crossing_rate REAL,  -- Roughness/noisiness (0-1)
    rms_energy REAL,  -- Overall loudness (0-1)
    dynamic_range REAL,  -- Peak-to-valley difference in dB

    -- Rhythm analysis (optional)
    bpm REAL,  -- Tempo in beats per minute
    bpm_confidence REAL,  -- Confidence score (0-1)
    is_loop INTEGER,  -- Boolean: 1=loop, 0=one-shot, NULL=unknown

    -- Tonal analysis (optional)
    key TEXT,  -- Musical key (C, Cm, F#, etc.)
    key_confidence REAL,  -- Confidence score (0-1)
    tuning_frequency REAL,  -- Reference tuning (default 440 Hz)
    pitch_salience REAL,  -- Tonal vs percussive (0-1, higher=tonal)

    -- ML-derived categories (optional)
    instrument_type TEXT,  -- Category: kick, snare, hi-hat, bass, pad, etc.
    instrument_confidence REAL,  -- Classification confidence (0-1)
    mood TEXT,  -- JSON array: ["dark", "energetic"]
    genre_tags TEXT,  -- JSON array: ["techno", "house"]

    -- Timestamps
    created_at TEXT NOT NULL,  -- ISO 8601 format
    updated_at TEXT NOT NULL   -- ISO 8601 format
);

-- Synth definitions table
CREATE TABLE IF NOT EXISTS synths (
    -- Identity
    id TEXT PRIMARY KEY,  -- Format: "synth_{hash[:8]}"
    name TEXT NOT NULL UNIQUE,  -- User-friendly name (e.g., "tb303", "deep_bass")
    file_path TEXT NOT NULL UNIQUE,  -- Path to .scd file
    file_hash TEXT NOT NULL UNIQUE,  -- SHA256 hash of source code

    -- Characteristics (JSON objects)
    characteristics TEXT,  -- JSON: {"envelope": "short", "timbre": "bright", ...}
    categorization TEXT,  -- JSON: {"family": "bass", "tags": ["acid", "303"]}

    -- Source and controls
    source_code TEXT NOT NULL,  -- Complete SynthDef source code
    controls TEXT,  -- JSON array: [{"name": "cutoff", "min": 200, "max": 4000, "default": 1000}, ...]

    -- Timestamps
    created_at TEXT NOT NULL,  -- ISO 8601 format
    updated_at TEXT NOT NULL   -- ISO 8601 format
);

-- Pattern storage table
CREATE TABLE IF NOT EXISTS patterns (
    -- Identity
    id TEXT PRIMARY KEY,  -- Format: "ptrn_{hash[:8]}"
    type TEXT NOT NULL,  -- Pattern type: "midi", "tidal", "supercollider"

    -- Pattern data (store one of these based on type)
    midi_data BLOB,  -- Binary MIDI data
    tidal_code TEXT,  -- TidalCycles code
    sc_code TEXT,  -- SuperCollider code

    -- Generation parameters (JSON)
    generation_params TEXT,  -- JSON: {"model": "music_vae", "temperature": 0.8, ...}

    -- Lineage tracking
    parent_pattern_id TEXT,  -- Reference to parent pattern (for variations)
    generation_number INTEGER NOT NULL DEFAULT 0,  -- How many generations from original

    -- User feedback
    rating INTEGER,  -- User rating (1-5 stars, NULL=unrated)

    -- Timestamps
    created_at TEXT NOT NULL,  -- ISO 8601 format
    updated_at TEXT NOT NULL,  -- ISO 8601 format

    FOREIGN KEY (parent_pattern_id) REFERENCES patterns(id) ON DELETE SET NULL
);

-- Synth lineage tracking table (many-to-many: synth -> parent synths)
CREATE TABLE IF NOT EXISTS synth_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synth_id TEXT NOT NULL,  -- Child synth
    parent_synth_id TEXT NOT NULL,  -- Parent synth
    contribution_weight REAL DEFAULT 0.5,  -- How much parent influenced child (0-1)
    created_at TEXT NOT NULL,  -- ISO 8601 format

    FOREIGN KEY (synth_id) REFERENCES synths(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_synth_id) REFERENCES synths(id) ON DELETE CASCADE,
    UNIQUE(synth_id, parent_synth_id)  -- Prevent duplicate lineage entries
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
