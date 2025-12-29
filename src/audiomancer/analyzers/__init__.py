"""Audio analysis for audiomancer.

Provides interfaces for SynthDef parsing and audio feature extraction,
including basic metadata, spectral, rhythm, tonal analysis, ML classification,
and audio embeddings.
"""

from .interfaces import (
    ControlSpec,
    SynthControl,
    SynthDefMetadata,
    SynthDefParser,
    SynthDefStore,
)
from .basic import get_basic_metadata, BasicMetadata
from .spectral import extract_spectral_features, SpectralFeatures
from .rhythm import extract_rhythm_features
from .tonal import extract_tonal_features
from .synthdef import (
    parse_synthdef,
    categorize_synthdef,
    SynthDefInfo,
    SynthControl as SynthDefControl,
)
from .classifier import (
    classify_instrument,
    extract_mood_tags,
    extract_genre_tags,
)
from .embeddings import (
    extract_audio_embedding,
    cosine_similarity,
    euclidean_distance,
)
from .models import (
    load_model,
    download_model,
    list_models,
    clear_cache,
)

__all__ = [
    # SynthDef interfaces
    "ControlSpec",
    "SynthControl",
    "SynthDefMetadata",
    "SynthDefParser",
    "SynthDefStore",
    # SynthDef parsing
    "parse_synthdef",
    "categorize_synthdef",
    "SynthDefInfo",
    "SynthDefControl",
    # Audio analysis functions
    "get_basic_metadata",
    "BasicMetadata",
    "extract_spectral_features",
    "SpectralFeatures",
    "extract_rhythm_features",
    "extract_tonal_features",
    # ML classification
    "classify_instrument",
    "extract_mood_tags",
    "extract_genre_tags",
    # Audio embeddings
    "extract_audio_embedding",
    "cosine_similarity",
    "euclidean_distance",
    # Model management
    "load_model",
    "download_model",
    "list_models",
    "clear_cache",
]
