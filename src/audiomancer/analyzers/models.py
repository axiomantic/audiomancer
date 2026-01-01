"""ML model management for audiomancer.

This module handles downloading, caching, and loading of Essentia TensorFlow models
for audio classification and embedding extraction.

Models are cached in ~/.local/share/audiomancer/models/
"""

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Optional, Literal

from ..errors import ModelLoadError


ModelType = Literal[
    "musicnn",
    "vggish",
    "openl3",
    "mtg_jamendo_instrument",
    "mtg_jamendo_moodtheme",
    "mtg_jamendo_genre",
]


# Essentia model URLs and checksums
# See: https://essentia.upf.edu/models.html
MODEL_REGISTRY = {
    "musicnn": {
        "url": "https://essentia.upf.edu/models/feature-extractors/musicnn/msd-musicnn-1.pb",
        "sha256": "cdea0722bcee7f731286843f2233e3aa69887bb5c3e2dce011eff55f38d04f3e",
        "description": "MusiCNN embeddings (128-dim) trained on Million Song Dataset",
    },
    "vggish": {
        "url": "https://essentia.upf.edu/models/feature-extractors/vggish/audioset-vggish-3.pb",
        "sha256": "609458111eae0f1f608627be21b041d4bcf8eff98dcaaa4e55380b6e0ea5e2d0",
        "description": "VGGish embeddings (128-dim) trained on AudioSet",
    },
    "mtg_jamendo_instrument": {
        "url": "https://essentia.upf.edu/models/classification-heads/mtg_jamendo_instrument/mtg_jamendo_instrument-discogs-effnet-1.pb",
        "sha256": "2e8c3003c722e098da371b6a1f7ad0ce62fac0dcfc09c7c7997d430941196c2a",
        "description": "Instrument classification (40 classes) from MTG-Jamendo",
    },
    "mtg_jamendo_moodtheme": {
        "url": "https://essentia.upf.edu/models/classification-heads/mtg_jamendo_moodtheme/mtg_jamendo_moodtheme-discogs-effnet-1.pb",
        "sha256": "03f2b047020aee4ab39f8880da7bdae2a36d06a1508d656c6d424ad4d6de07a9",
        "description": "Mood/theme classification (56 classes) from MTG-Jamendo",
    },
    "mtg_jamendo_genre": {
        "url": "https://essentia.upf.edu/models/classification-heads/mtg_jamendo_genre/mtg_jamendo_genre-discogs-effnet-1.pb",
        "sha256": "a46f94fd85b03b403d6498a820e3ee652e05a24fc2a344d84545ac36224e698e",
        "description": "Genre classification (87 classes) from MTG-Jamendo",
    },
}


def get_model_dir() -> Path:
    """Get the model cache directory.

    Returns:
        Path to ~/.local/share/audiomancer/models/
    """
    model_dir = Path.home() / ".local" / "share" / "audiomancer" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def get_model_path(model_type: ModelType) -> Path:
    """Get the path to a model file.

    Args:
        model_type: Model type identifier

    Returns:
        Path to model file in cache directory

    Example:
        >>> path = get_model_path("musicnn")
        >>> path.name
        'musicnn.pb'
    """
    model_dir = get_model_dir()
    return model_dir / f"{model_type}.pb"


def is_valid_sha256(s: str) -> bool:
    """Check if string is a valid SHA256 hex digest.

    SHA256 hashes are 64 hexadecimal characters (0-9, a-f).
    Placeholder values contain invalid chars like g-z.
    """
    if len(s) != 64:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def verify_model_checksum(path: Path, expected_sha256: str) -> bool:
    """Verify model file integrity using SHA256.

    Args:
        path: Path to model file
        expected_sha256: Expected SHA256 hex digest

    Returns:
        True if checksum matches, False otherwise
        Also returns True if expected_sha256 is a placeholder (invalid hex)

    Example:
        >>> path = Path("model.pb")
        >>> verify_model_checksum(path, "abc123...")
        True
    """
    # Skip verification for placeholder checksums
    if not is_valid_sha256(expected_sha256):
        return True

    try:
        with open(path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return file_hash == expected_sha256
    except Exception:
        return False


def download_model(
    model_type: ModelType,
    force: bool = False,
    verify_checksum: bool = True,
) -> Path:
    """Download an Essentia model from the model zoo.

    Downloads to ~/.local/share/audiomancer/models/ and verifies checksum.

    Args:
        model_type: Model type to download
        force: Force re-download even if file exists
        verify_checksum: Verify SHA256 checksum after download

    Returns:
        Path to downloaded model file

    Raises:
        ModelLoadError: If download fails or checksum mismatch

    Example:
        >>> path = download_model("musicnn")
        >>> path.exists()
        True
        >>> path.stat().st_size > 0
        True
    """
    if model_type not in MODEL_REGISTRY:
        raise ModelLoadError(
            f"Unknown model type: {model_type}",
            details={
                "model_type": model_type,
                "available_models": list(MODEL_REGISTRY.keys()),
            }
        )

    model_info = MODEL_REGISTRY[model_type]
    model_path = get_model_path(model_type)

    # Check if already exists and valid
    if model_path.exists() and not force:
        if verify_checksum:
            if verify_model_checksum(model_path, model_info["sha256"]):
                return model_path
            else:
                # Checksum mismatch, re-download
                model_path.unlink()
        else:
            return model_path

    # Download from Essentia model zoo
    try:
        print(f"Downloading {model_type} model from Essentia...")
        print(f"  URL: {model_info['url']}")
        print(f"  Description: {model_info['description']}")

        urllib.request.urlretrieve(model_info["url"], model_path)

    except Exception as e:
        if model_path.exists():
            model_path.unlink()
        raise ModelLoadError(
            f"Failed to download {model_type} model",
            details={
                "model_type": model_type,
                "url": model_info["url"],
                "error": str(e),
            }
        )

    # Verify checksum
    if verify_checksum:
        if not verify_model_checksum(model_path, model_info["sha256"]):
            model_path.unlink()
            raise ModelLoadError(
                f"Downloaded {model_type} model failed checksum verification",
                details={
                    "model_type": model_type,
                    "path": str(model_path),
                    "expected_sha256": model_info["sha256"],
                }
            )

    print(f"  Downloaded to: {model_path}")
    return model_path


def load_model(
    model_type: ModelType,
    auto_download: bool = True,
) -> Path:
    """Load an Essentia model, downloading if necessary.

    Args:
        model_type: Model type to load
        auto_download: Automatically download if not cached

    Returns:
        Path to model file

    Raises:
        ModelLoadError: If model not found and auto_download=False

    Example:
        >>> model_path = load_model("musicnn")
        >>> model_path.exists()
        True
    """
    model_path = get_model_path(model_type)

    if model_path.exists():
        return model_path

    if not auto_download:
        raise ModelLoadError(
            f"Model not found: {model_type}",
            details={
                "model_type": model_type,
                "path": str(model_path),
                "hint": "Set auto_download=True or run download_model()",
            }
        )

    return download_model(model_type)


def list_models(include_cached_only: bool = False) -> dict[str, dict]:
    """List available models and their status.

    Args:
        include_cached_only: Only show cached models

    Returns:
        Dictionary mapping model type to info dict with keys:
        - cached: Whether model is cached locally (bool)
        - path: Path to cached model if exists (str | None)
        - description: Model description (str)

    Example:
        >>> models = list_models()
        >>> "musicnn" in models
        True
        >>> models["musicnn"]["cached"]
        True
    """
    result = {}

    for model_type, info in MODEL_REGISTRY.items():
        model_path = get_model_path(model_type)
        cached = model_path.exists()

        if include_cached_only and not cached:
            continue

        result[model_type] = {
            "cached": cached,
            "path": str(model_path) if cached else None,
            "description": info["description"],
        }

    return result


def clear_cache(model_type: Optional[ModelType] = None) -> None:
    """Clear model cache.

    Args:
        model_type: Specific model to clear, or None to clear all

    Example:
        >>> clear_cache("musicnn")  # Clear specific model
        >>> clear_cache()  # Clear all models
    """
    if model_type is not None:
        model_path = get_model_path(model_type)
        if model_path.exists():
            model_path.unlink()
    else:
        model_dir = get_model_dir()
        for model_file in model_dir.glob("*.pb"):
            model_file.unlink()
