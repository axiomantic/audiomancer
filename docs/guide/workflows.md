# Workflows

## Sample Library Management

**Goal**: Enable sample packs from Google Drive for use in TidalCycles.

```
You: "What sample packs do I have?"

AI: [calls list_packs]
    You have 47 packs available:
    - 808 Drum Kit (4 files, 2.1 MB) - remote
    - Vinyl House Drums (12 files, 8.4 MB) - remote
    - Tech Loops 125 (6 files, 15.2 MB) - enabled
    ...

You: "Enable the 808 Drum Kit"

AI: [calls enable_pack "808 Drum Kit"]
    Enabled 808 Drum Kit:
    - Copied 4 files to samples/
    - Created symlinks in library/
    - Sample IDs: 808dk_bd, 808dk_sn, 808dk_hh

    Restart SuperDirt to load: Ctrl+Enter on start_superdirt.scd

You: "What kicks do I have now?"

AI: [calls list_enabled_samples, filters by category]
    Enabled kicks (bd):
    - 808dk_bd (2 variations)
    - vihodr_bd (1 variation)
```

**Pack Status**:

- `remote` - On Google Drive, not cached locally
- `cached` - Copied to samples/, but not enabled (no symlinks)
- `enabled` - Active in library/, SuperDirt can load it

## Pattern Generation

**Goal**: Generate TidalCycles patterns using your enabled samples.

```
You: "Generate a techno drum pattern at 130 BPM"

AI: [calls generate_pattern with sample_lookup]
    Generated 4-bar techno pattern:

    d1 $ sound "808dk_bd 808dk_bd ~ 808dk_bd" # speed 1.05
    d2 $ sound "808dk_sn" # n (irand 3) # gain 0.9
    d3 $ sound "808dk_hh*8" # gain 0.7 # pan (rand)

You: "Make the hats more sparse"

AI: [modifies pattern]
    d3 $ sound "808dk_hh(5,8)" # gain 0.7

You: "Add some variation to the kick"

AI: [adds pattern variation]
    d1 $ sound "808dk_bd(<3 4>,8)" # speed (range 0.95 1.1 $ slow 4 sine)
```

The AI uses your actual sample IDs (like `808dk_bd`) instead of generic names because it queries your enabled library.

## Sample Discovery

**Goal**: Find samples by description or similarity.

```
You: "Find samples similar to this kick" [with sample ID or path]

AI: [calls find_similar]
    Similar to 808dk_bd:
    1. vihodr_bd (0.92 similarity) - warmer, more sub
    2. techse_bd (0.87 similarity) - harder attack
    3. dnbpk_bd (0.81 similarity) - longer decay

You: "Search for dark ambient pads"

AI: [calls search_samples]
    Found 3 matching samples:
    - ambpk_pad (key: Dm, 8.2s)
    - drkam_pad (key: Am, 12.1s)
    ...
```

## Next Steps

- [MCP Tools](mcp-tools.md) - Complete tool reference
- [CLI Commands](cli.md) - Command-line usage
