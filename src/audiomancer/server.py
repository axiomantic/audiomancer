"""MCP server for audiomancer.

Provides Model Context Protocol server interface for audio sample search,
analysis, and synth metadata access. Tools are designed for LLM consumption
with structured JSON responses.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import mcp.server.stdio

from audiomancer.storage.unified import UnifiedSampleStorage
from audiomancer.storage.synth_store import SynthStore
from audiomancer.analyzers import (
    get_basic_metadata,
    extract_spectral_features,
    extract_rhythm_features,
    extract_tonal_features,
    extract_audio_embedding,
    classify_instrument,
)
from audiomancer.config import load_config, ensure_directories
from audiomancer.errors import (
    AudiomancerError,
    SampleNotFoundError,
    AnalysisError,
    LibraryError,
    PackNotFoundError,
    SourceNotAvailableError,
)
from audiomancer.library import LibraryManager


server = Server("audiomancer")

# Global storage instances (initialized in main)
storage: Optional[UnifiedSampleStorage] = None
synth_store: Optional[SynthStore] = None
library_manager: Optional[LibraryManager] = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="search_samples",
            description="Search audio samples by text query and/or filters. Returns sample metadata including instrument type, BPM, key, duration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text search query (searches file paths and instrument types)"
                    },
                    "instrument_type": {
                        "type": "string",
                        "description": "Filter by instrument classification (e.g., 'kick', 'snare', 'bass')"
                    },
                    "bpm_min": {
                        "type": "number",
                        "description": "Minimum BPM"
                    },
                    "bpm_max": {
                        "type": "number",
                        "description": "Maximum BPM"
                    },
                    "key": {
                        "type": "string",
                        "description": "Musical key (e.g., 'C', 'Am', 'F#')"
                    },
                    "mood": {
                        "type": "string",
                        "description": "Mood tag (e.g., 'dark', 'bright', 'aggressive')"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of results"
                    }
                }
            }
        ),
        Tool(
            name="find_similar",
            description="Find samples similar to a given sample using audio embeddings. Returns semantically similar samples ranked by distance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sample_id": {
                        "type": "string",
                        "description": "Sample ID to find similar samples for"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of similar samples to return"
                    }
                },
                "required": ["sample_id"]
            }
        ),
        Tool(
            name="describe_sample",
            description="Get complete metadata and analysis for a sample including spectral features, rhythm, tonality, and ML classifications.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sample_id": {
                        "type": "string",
                        "description": "Sample ID to retrieve details for"
                    }
                },
                "required": ["sample_id"]
            }
        ),
        Tool(
            name="analyze_file",
            description="Analyze a new audio file and add it to the database. Extracts all features including embeddings, spectral, rhythm, and tonal analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to audio file to analyze"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="list_synths",
            description="List available SuperCollider SynthDefs with optional category filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by synth category (e.g., 'bass', 'pad', 'lead')"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum number of results"
                    }
                }
            }
        ),
        Tool(
            name="get_synth",
            description="Get full details for a SuperCollider SynthDef including controls, source code, and characteristics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "SynthDef name"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_stats",
            description="Get library statistics including total samples, synths, instrument type distribution, and BPM ranges.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        # Library management tools
        Tool(
            name="list_packs",
            description="List all available sample packs from the source directory (e.g., Google Drive). Shows status (enabled/cached/remote) for each pack.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_packs",
            description="Search sample packs by name pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to match against pack names"
                    }
                },
                "required": ["pattern"]
            }
        ),
        Tool(
            name="get_pack_status",
            description="Get detailed status of a sample pack including files, size, and sample IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pack_name": {
                        "type": "string",
                        "description": "Name of the pack folder"
                    }
                },
                "required": ["pack_name"]
            }
        ),
        Tool(
            name="enable_pack",
            description="Enable a sample pack - copies from source to local cache and creates symlinks for SuperDirt.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pack_name": {
                        "type": "string",
                        "description": "Name of the pack to enable"
                    },
                    "max_size_mb": {
                        "type": "integer",
                        "default": 10,
                        "description": "Skip files larger than this (MB)"
                    }
                },
                "required": ["pack_name"]
            }
        ),
        Tool(
            name="disable_pack",
            description="Disable a sample pack - removes symlinks but keeps cached files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pack_name": {
                        "type": "string",
                        "description": "Name of the pack to disable"
                    }
                },
                "required": ["pack_name"]
            }
        ),
        Tool(
            name="purge_pack",
            description="Remove a sample pack from local cache entirely.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pack_name": {
                        "type": "string",
                        "description": "Name of the pack to purge"
                    }
                },
                "required": ["pack_name"]
            }
        ),
        Tool(
            name="list_enabled_samples",
            description="List all enabled sample IDs with their categories. These can be used in TidalCycles patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category (bd, sn, hh, etc.)"
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls with structured error handling."""
    try:
        if name == "search_samples":
            return await search_samples(**arguments)
        elif name == "find_similar":
            return await find_similar(**arguments)
        elif name == "describe_sample":
            return await describe_sample(**arguments)
        elif name == "analyze_file":
            return await analyze_file(**arguments)
        elif name == "list_synths":
            return await list_synths(**arguments)
        elif name == "get_synth":
            return await get_synth(**arguments)
        elif name == "get_stats":
            return await get_stats(**arguments)
        # Library management tools
        elif name == "list_packs":
            return await list_packs_tool(**arguments)
        elif name == "search_packs":
            return await search_packs_tool(**arguments)
        elif name == "get_pack_status":
            return await get_pack_status_tool(**arguments)
        elif name == "enable_pack":
            return await enable_pack_tool(**arguments)
        elif name == "disable_pack":
            return await disable_pack_tool(**arguments)
        elif name == "purge_pack":
            return await purge_pack_tool(**arguments)
        elif name == "list_enabled_samples":
            return await list_enabled_samples_tool(**arguments)
        else:
            error_response = {
                "error": "UnknownTool",
                "message": f"Unknown tool: {name}",
                "available_tools": [
                    "search_samples", "find_similar", "describe_sample",
                    "analyze_file", "list_synths", "get_synth", "get_stats",
                    "list_packs", "search_packs", "get_pack_status",
                    "enable_pack", "disable_pack", "purge_pack", "list_enabled_samples"
                ]
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    except AudiomancerError as e:
        # Structured error response with details
        error_response = e.to_dict()
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    except Exception as e:
        # Unexpected error
        error_response = {
            "error": "InternalError",
            "message": str(e),
            "type": type(e).__name__
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def search_samples(
    query: Optional[str] = None,
    instrument_type: Optional[str] = None,
    bpm_min: Optional[float] = None,
    bpm_max: Optional[float] = None,
    key: Optional[str] = None,
    mood: Optional[str] = None,
    limit: int = 20
) -> list[TextContent]:
    """Search samples with filters.

    Args:
        query: Text search query
        instrument_type: Filter by instrument type
        bpm_min: Minimum BPM
        bpm_max: Maximum BPM
        key: Musical key filter
        mood: Mood tag filter
        limit: Maximum results

    Returns:
        TextContent with JSON array of sample metadata
    """
    if storage is None:
        raise AudiomancerError("Storage not initialized")

    results = storage.sample_store.search(
        query=query,
        instrument_type=instrument_type,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        key=key,
        mood=mood,
        limit=limit
    )

    # Format for LLM consumption
    formatted = []
    for sample in results:
        formatted.append({
            "id": sample["id"],
            "file_path": sample["file_path"],
            "instrument_type": sample.get("instrument_type"),
            "bpm": sample.get("bpm"),
            "key": sample.get("key"),
            "duration_ms": sample.get("duration_ms"),
            "sample_rate": sample.get("sample_rate"),
            "channels": sample.get("channels"),
            "mood": sample.get("mood"),
        })

    response = {
        "results": formatted,
        "count": len(formatted),
        "query": {
            "text": query,
            "instrument_type": instrument_type,
            "bpm_range": [bpm_min, bpm_max] if bpm_min or bpm_max else None,
            "key": key,
            "mood": mood,
        }
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def find_similar(
    sample_id: str,
    limit: int = 10
) -> list[TextContent]:
    """Find samples similar to a given sample.

    Args:
        sample_id: Sample ID to find similar samples for
        limit: Maximum number of similar samples

    Returns:
        TextContent with JSON array of similar samples with distances

    Raises:
        SampleNotFoundError: If sample_id not found
    """
    if storage is None:
        raise AudiomancerError("Storage not initialized")

    try:
        similar = storage.find_similar(
            sample_id=sample_id,
            limit=limit,
            exclude_self=True
        )
    except SampleNotFoundError:
        raise SampleNotFoundError(
            sample_id,
            details={"reason": "No sample with this ID exists"}
        )

    # Format results
    formatted = []
    for sample, distance in similar:
        formatted.append({
            "id": sample["id"],
            "file_path": sample["file_path"],
            "instrument_type": sample.get("instrument_type"),
            "bpm": sample.get("bpm"),
            "key": sample.get("key"),
            "distance": float(distance),
        })

    response = {
        "query_sample_id": sample_id,
        "similar_samples": formatted,
        "count": len(formatted)
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def describe_sample(sample_id: str) -> list[TextContent]:
    """Get full metadata and analysis for a sample.

    Args:
        sample_id: Sample ID

    Returns:
        TextContent with complete sample metadata

    Raises:
        SampleNotFoundError: If sample not found
    """
    if storage is None:
        raise AudiomancerError("Storage not initialized")

    sample = storage.get_sample(sample_id)
    if sample is None:
        raise SampleNotFoundError(sample_id)

    # Convert to serializable format
    serializable_sample = dict(sample)

    # Convert datetime objects to ISO strings (handle both datetime and str)
    from datetime import datetime
    if "created_at" in serializable_sample:
        if isinstance(serializable_sample["created_at"], datetime):
            serializable_sample["created_at"] = serializable_sample["created_at"].isoformat()
    if "updated_at" in serializable_sample:
        if isinstance(serializable_sample["updated_at"], datetime):
            serializable_sample["updated_at"] = serializable_sample["updated_at"].isoformat()

    return [TextContent(type="text", text=json.dumps(serializable_sample, indent=2))]


async def analyze_file(path: str) -> list[TextContent]:
    """Analyze a new audio file and add to database.

    Args:
        path: Path to audio file

    Returns:
        TextContent with analysis results and sample ID

    Raises:
        AnalysisError: If analysis fails
    """
    if storage is None:
        raise AudiomancerError("Storage not initialized")

    file_path = Path(path).expanduser().absolute()

    if not file_path.exists():
        raise AnalysisError(
            f"File not found: {path}",
            details={"path": str(file_path), "reason": "File does not exist"}
        )

    try:
        # Run analysis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        # Extract all features
        basic = await loop.run_in_executor(None, get_basic_metadata, str(file_path))
        spectral = await loop.run_in_executor(None, extract_spectral_features, str(file_path))
        rhythm = await loop.run_in_executor(None, extract_rhythm_features, str(file_path))
        tonal = await loop.run_in_executor(None, extract_tonal_features, str(file_path))
        embedding = await loop.run_in_executor(None, extract_audio_embedding, str(file_path))
        instrument = await loop.run_in_executor(None, classify_instrument, str(file_path))

        # Combine into sample metadata
        from audiomancer.storage.interfaces import SampleMetadata

        sample = SampleMetadata(
            id=basic.id,
            file_path=str(file_path),
            file_hash=basic.file_hash,
            duration_ms=basic.duration_ms,
            sample_rate=basic.sample_rate,
            channels=basic.channels,
            bit_depth=basic.bit_depth,
            file_size_bytes=basic.file_size_bytes,
            spectral_centroid=spectral.spectral_centroid,
            spectral_bandwidth=spectral.spectral_bandwidth,
            spectral_rolloff=spectral.spectral_rolloff,
            zero_crossing_rate=spectral.zero_crossing_rate,
            rms_energy=spectral.rms_energy,
            dynamic_range=spectral.dynamic_range,
            bpm=rhythm.bpm,
            bpm_confidence=rhythm.confidence,
            is_loop=rhythm.is_loop,
            key=tonal.key,
            key_confidence=tonal.key_confidence,
            tuning_frequency=tonal.tuning_frequency,
            pitch_salience=tonal.pitch_salience,
            instrument_type=instrument.primary_class,
            instrument_confidence=instrument.confidence,
        )

        # Add to storage
        sample_id = storage.add_sample_with_embedding(sample, embedding.embedding)

        response = {
            "success": True,
            "sample_id": sample_id,
            "file_path": str(file_path),
            "analysis": {
                "instrument_type": instrument.primary_class,
                "bpm": rhythm.bpm,
                "key": tonal.key,
                "duration_ms": basic.duration_ms,
            }
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        raise AnalysisError(
            f"Analysis failed for {path}: {str(e)}",
            details={"path": str(file_path), "error": str(e), "type": type(e).__name__}
        )


async def list_synths(
    category: Optional[str] = None,
    limit: int = 50
) -> list[TextContent]:
    """List available SynthDefs.

    Args:
        category: Optional category filter
        limit: Maximum results

    Returns:
        TextContent with JSON array of synth metadata
    """
    if synth_store is None:
        raise AudiomancerError("Synth store not initialized")

    # Get all synths
    synths = synth_store.list_all(limit=limit)

    # Filter by category if provided
    if category:
        synths = [
            s for s in synths
            if s.get("categorization", {}).get("category") == category
        ]

    # Format for LLM
    formatted = []
    for synth in synths:
        formatted.append({
            "id": synth["id"],
            "name": synth["name"],
            "category": synth.get("categorization", {}).get("category"),
            "num_controls": len(synth.get("controls", [])),
            "has_gate": synth.get("characteristics", {}).get("has_gate", False),
        })

    response = {
        "synths": formatted,
        "count": len(formatted),
        "filter": {"category": category} if category else None
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def get_synth(name: str) -> list[TextContent]:
    """Get full details for a SynthDef.

    Args:
        name: SynthDef name

    Returns:
        TextContent with complete synth metadata

    Raises:
        AudiomancerError: If synth not found
    """
    if synth_store is None:
        raise AudiomancerError("Synth store not initialized")

    synth = synth_store.get_by_name(name)
    if synth is None:
        raise AudiomancerError(
            f"SynthDef not found: {name}",
            details={"name": name, "reason": "No synth with this name exists"}
        )

    # Convert datetime objects (handle both datetime and str)
    from datetime import datetime

    serializable_synth = dict(synth)
    if "created_at" in serializable_synth:
        if isinstance(serializable_synth["created_at"], datetime):
            serializable_synth["created_at"] = serializable_synth["created_at"].isoformat()
    if "updated_at" in serializable_synth:
        if isinstance(serializable_synth["updated_at"], datetime):
            serializable_synth["updated_at"] = serializable_synth["updated_at"].isoformat()

    return [TextContent(type="text", text=json.dumps(serializable_synth, indent=2))]


async def get_stats() -> list[TextContent]:
    """Get library statistics.

    Returns:
        TextContent with library statistics
    """
    if storage is None or synth_store is None:
        raise AudiomancerError("Storage not initialized")

    # Get sample stats
    total_samples = storage.sample_store.count()

    # Get instrument type distribution
    instrument_stats = storage.sample_store.get_instrument_distribution()

    # Get synth stats
    total_synths = synth_store.count()

    response = {
        "samples": {
            "total": total_samples,
            "by_instrument": instrument_stats,
        },
        "synths": {
            "total": total_synths,
        }
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


# Library management tool handlers

async def list_packs_tool() -> list[TextContent]:
    """List all available sample packs from source."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    loop = asyncio.get_event_loop()
    packs = await loop.run_in_executor(None, library_manager.list_packs)

    # Get status for each pack
    formatted = []
    for pack in packs:
        try:
            status = await loop.run_in_executor(
                None, library_manager.get_pack_status, pack["name"]
            )
            formatted.append({
                "name": pack["name"],
                "status": status["status"],
                "file_count": pack["file_count"],
                "size_mb": round(pack["size_mb"], 1),
                "sample_ids": pack["sample_ids"],
            })
        except Exception:
            formatted.append({
                "name": pack["name"],
                "status": "unknown",
                "file_count": pack["file_count"],
                "size_mb": round(pack["size_mb"], 1),
            })

    response = {
        "packs": formatted,
        "count": len(formatted),
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def search_packs_tool(pattern: str) -> list[TextContent]:
    """Search packs by name pattern."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    loop = asyncio.get_event_loop()
    packs = await loop.run_in_executor(None, library_manager.search_packs, pattern)

    formatted = []
    for pack in packs:
        try:
            status = await loop.run_in_executor(
                None, library_manager.get_pack_status, pack["name"]
            )
            formatted.append({
                "name": pack["name"],
                "status": status["status"],
                "file_count": pack["file_count"],
                "size_mb": round(pack["size_mb"], 1),
            })
        except Exception:
            formatted.append({
                "name": pack["name"],
                "file_count": pack["file_count"],
                "size_mb": round(pack["size_mb"], 1),
            })

    response = {
        "pattern": pattern,
        "results": formatted,
        "count": len(formatted),
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def get_pack_status_tool(pack_name: str) -> list[TextContent]:
    """Get detailed status of a pack."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(
        None, library_manager.get_pack_status, pack_name
    )

    return [TextContent(type="text", text=json.dumps(status, indent=2))]


async def enable_pack_tool(pack_name: str, max_size_mb: int = 10) -> list[TextContent]:
    """Enable a sample pack."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    result = await library_manager.enable_pack_async(
        pack_name=pack_name,
        max_size_mb=max_size_mb,
    )

    response = {
        "success": True,
        "pack_name": result["pack_name"],
        "samples_enabled": result["samples_enabled"],
        "sample_ids": result["sample_ids"],
        "copy_stats": result["copy_stats"],
        "message": f"Enabled {result['samples_enabled']} samples. Restart SuperDirt to load.",
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def disable_pack_tool(pack_name: str) -> list[TextContent]:
    """Disable a sample pack."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    loop = asyncio.get_event_loop()
    count = await loop.run_in_executor(
        None, library_manager.disable_pack, pack_name
    )

    response = {
        "success": True,
        "pack_name": pack_name,
        "samples_disabled": count,
        "message": f"Disabled {count} samples. Restart SuperDirt to apply.",
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def purge_pack_tool(pack_name: str) -> list[TextContent]:
    """Purge a sample pack from cache."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    loop = asyncio.get_event_loop()
    removed = await loop.run_in_executor(
        None, library_manager.purge_pack, pack_name
    )

    response = {
        "success": removed,
        "pack_name": pack_name,
        "message": "Pack removed from cache." if removed else "Pack was not in cache.",
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def list_enabled_samples_tool(category: Optional[str] = None) -> list[TextContent]:
    """List enabled sample IDs."""
    if library_manager is None:
        raise AudiomancerError("Library manager not initialized")

    loop = asyncio.get_event_loop()
    samples = await loop.run_in_executor(None, library_manager.list_enabled_samples)

    # Filter by category if provided
    if category:
        samples = [s for s in samples if s.get("category") == category]

    # Group by category for easier use
    by_category: dict[str, list[str]] = {}
    for sample in samples:
        cat = sample.get("category", "misc")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(sample["id"])

    response = {
        "samples": samples,
        "by_category": by_category,
        "count": len(samples),
        "filter": {"category": category} if category else None,
        "tip": "Use sample IDs in TidalCycles: d1 $ sound \"sample_id\"",
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def main():
    """Run the MCP server."""
    global storage, synth_store, library_manager

    # Load config
    config = load_config()
    ensure_directories(config)

    # Initialize storage
    storage = UnifiedSampleStorage(
        db_path=config.storage.db_path,
        embeddings_path=config.storage.embeddings_path
    )

    synth_store = SynthStore(str(config.storage.db_path))

    # Initialize library manager
    library_manager = LibraryManager(
        source_dir=config.library.source_dir,
        samples_dir=config.library.samples_dir,
        library_dir=config.library.library_dir,
    )

    # Run server
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="audiomancer",
                server_version="0.1.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(listChanged=False)
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
