"""Cached model loading for audiomancer.

Loads TensorFlow models once and reuses them for all files to avoid
expensive repeated model initialization.

The cache is maintained in a module-level dictionary that persists
for the lifetime of the Python process.
"""

import essentia.standard as es
from typing import Optional

from .models import load_model


# Global model cache - persists for process lifetime
_model_cache: dict[str, es.TensorflowPredict] = {}


def get_effnet_model() -> es.TensorflowPredictEffnetDiscogs:
    """Get or create cached discogs-effnet model.

    This is the base model used by all MTG-Jamendo classification heads.
    Loading it once and reusing it across all classifications provides
    significant performance improvements.

    Returns:
        Cached TensorflowPredictEffnetDiscogs instance

    Example:
        >>> effnet = get_effnet_model()
        >>> embeddings = effnet(audio)
        >>> # Second call returns same instance (no reload)
        >>> effnet2 = get_effnet_model()
        >>> assert effnet is effnet2
    """
    cache_key = "discogs_effnet"

    if cache_key not in _model_cache:
        effnet_path = str(load_model("discogs_effnet"))
        _model_cache[cache_key] = es.TensorflowPredictEffnetDiscogs(
            graphFilename=effnet_path,
            output="PartitionedCall:1",
        )

    return _model_cache[cache_key]


def get_classifier_model(model_name: str) -> es.TensorflowPredict2D:
    """Get or create cached classifier model.

    Supports MTG-Jamendo classification heads:
    - mtg_jamendo_instrument (40 classes)
    - mtg_jamendo_moodtheme (56 classes)
    - mtg_jamendo_genre (87 classes)

    Args:
        model_name: Name of the classifier model

    Returns:
        Cached TensorflowPredict2D instance

    Example:
        >>> classifier = get_classifier_model("mtg_jamendo_instrument")
        >>> predictions = classifier(embeddings)
        >>> # Second call returns same instance (no reload)
        >>> classifier2 = get_classifier_model("mtg_jamendo_instrument")
        >>> assert classifier is classifier2
    """
    if model_name not in _model_cache:
        model_path = str(load_model(model_name))
        _model_cache[model_name] = es.TensorflowPredict2D(
            graphFilename=model_path,
            input="model/Placeholder",
            output="model/Sigmoid",
        )

    return _model_cache[model_name]


def get_embedding_model(model_name: str = "musicnn") -> es.TensorflowPredict:
    """Get or create cached embedding model.

    Supports embedding models:
    - musicnn: MusiCNN embeddings (recommended for music)
    - vggish: VGGish embeddings (general audio)
    - openl3: OpenL3 embeddings (environmental sounds)

    Args:
        model_name: Name of the embedding model

    Returns:
        Cached TensorflowPredict instance (specific subtype varies by model)

    Example:
        >>> model = get_embedding_model("musicnn")
        >>> embedding = model(audio)
        >>> # Second call returns same instance (no reload)
        >>> model2 = get_embedding_model("musicnn")
        >>> assert model is model2
    """
    cache_key = f"embedding_{model_name}"

    if cache_key not in _model_cache:
        model_path = str(load_model(model_name))

        # Model-specific configuration
        if model_name == "vggish":
            _model_cache[cache_key] = es.TensorflowPredictVGGish(
                graphFilename=model_path,
                output="model/vggish/fc2/BiasAdd",
            )
        elif model_name == "musicnn":
            _model_cache[cache_key] = es.TensorflowPredictMusiCNN(
                graphFilename=model_path,
                output="model/dense/BiasAdd",
            )
        elif model_name == "openl3":
            # OpenL3 uses generic TensorflowPredict
            _model_cache[cache_key] = es.TensorflowPredict(
                graphFilename=model_path,
                output="model/openl3/embedding",
            )
        else:
            # Fallback to generic TensorflowPredict
            _model_cache[cache_key] = es.TensorflowPredict(
                graphFilename=model_path,
            )

    return _model_cache[cache_key]


def clear_cache() -> None:
    """Clear all cached models.

    Useful for testing or to free memory. Models will be reloaded
    on next use.

    Example:
        >>> # Use some models
        >>> effnet = get_effnet_model()
        >>> classifier = get_classifier_model("mtg_jamendo_instrument")
        >>>
        >>> # Clear cache to free memory
        >>> clear_cache()
        >>>
        >>> # Next call will reload from disk
        >>> effnet2 = get_effnet_model()
        >>> assert effnet2 is not effnet  # Different instance
    """
    _model_cache.clear()


def get_cache_stats() -> dict[str, int]:
    """Get statistics about the model cache.

    Returns:
        Dictionary with cache statistics:
        - num_models: Number of models currently cached
        - model_names: List of cached model keys

    Example:
        >>> stats = get_cache_stats()
        >>> stats["num_models"]
        3
        >>> "discogs_effnet" in stats["model_names"]
        True
    """
    return {
        "num_models": len(_model_cache),
        "model_names": list(_model_cache.keys()),
    }
