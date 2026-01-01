"""ML-based audio classification for audiomancer.

This module provides functions for classifying audio into instrument categories,
moods, and genres using pre-trained Essentia TensorFlow models.
"""

import numpy as np
import essentia.standard as es
from typing import Optional

from ..errors import AnalysisFailedError, ModelLoadError
from .models import load_model
from .model_cache import get_effnet_model, get_classifier_model


# Instrument class mapping for MTG-Jamendo instrument model
# Based on MTG-Jamendo-Dataset taxonomy
INSTRUMENT_CLASSES = [
    "accordion", "acousticbassguitar", "acousticguitar", "bass", "beat",
    "bell", "bongo", "brass", "cello", "clarinet", "classicalguitar",
    "computer", "doublebass", "drummachine", "drums", "electricguitar",
    "electricpiano", "flute", "guitar", "harmonica", "harp", "horn",
    "keyboard", "oboe", "orchestra", "organ", "pad", "percussion",
    "piano", "pipeorgan", "rhodes", "sampler", "saxophone", "strings",
    "synthesizer", "trombone", "trumpet", "viola", "violin", "voice",
]


# Mood/theme class mapping for MTG-Jamendo moodtheme model
MOOD_CLASSES = [
    "action", "adventure", "advertising", "background", "ballad", "calm",
    "children", "christmas", "commercial", "cool", "corporate", "dark",
    "deep", "documentary", "drama", "dramatic", "dream", "emotional",
    "energetic", "epic", "fast", "film", "fun", "funny", "game", "groovy",
    "happy", "heavy", "holiday", "hopeful", "inspiring", "love", "meditative",
    "melancholic", "melodic", "motivational", "movie", "nature", "party",
    "positive", "powerful", "relaxing", "retro", "romantic", "sad", "sexy",
    "slow", "soft", "soundscape", "space", "sport", "summer", "trailer",
    "travel", "upbeat", "uplifting",
]


# Genre class mapping for MTG-Jamendo genre model
GENRE_CLASSES = [
    "60s", "70s", "80s", "90s", "acidjazz", "alternative", "alternativerock",
    "ambient", "atmospheric", "blues", "bluesrock", "bossanova", "breakbeat",
    "celtic", "chanson", "chillout", "choir", "classical", "classicrock",
    "club", "contemporary", "country", "dance", "dancepop", "darkambient",
    "darkwave", "deephouse", "disco", "downtempo", "drumnbass", "dub",
    "dubstep", "easylistening", "edm", "electronic", "electronica", "electropop",
    "ethnic", "eurodance", "experimental", "folk", "funk", "fusion", "groove",
    "grunge", "hard", "hardrock", "hiphop", "house", "indie", "industrial",
    "instrumentalpop", "instrumentalrock", "jazz", "jazzfusion", "latin",
    "lounge", "medieval", "metal", "minimal", "newage", "newwave", "orchestral",
    "pop", "popfolk", "poprock", "postrock", "progressive", "psychedelic",
    "punkrock", "rap", "reggae", "rnb", "rock", "rocknroll", "singersongwriter",
    "soul", "soundtrack", "swing", "symphonic", "synthpop", "techno", "trance",
    "triphop", "world", "worldfusion",
]


def classify_instrument(
    audio: np.ndarray,
    sr: int,
    model_path: Optional[str] = None,
    top_k: int = 3,
) -> dict:
    """Classify audio into instrument categories using Essentia's pre-trained models.

    Uses MTG-Jamendo instrument classification model to detect instrument presence.
    This requires a two-stage pipeline:
    1. Extract embeddings using discogs-effnet base model
    2. Pass embeddings to classification head

    Args:
        audio: Audio samples as numpy array (mono or stereo)
        sr: Sample rate in Hz
        model_path: Path to custom model file, or None to use default
        top_k: Number of top predictions to return

    Returns:
        Dictionary with keys:
        - instrument_type: Most likely instrument (str)
        - instrument_confidence: Confidence score 0-1 (float)
        - top_predictions: List of (instrument, confidence) tuples

    Raises:
        ModelLoadError: If model file not found
        AnalysisFailedError: If classification fails

    Example:
        >>> result = classify_instrument(audio, 44100)
        >>> result['instrument_type']
        'drums'
        >>> result['instrument_confidence']
        0.92
        >>> result['top_predictions']
        [('drums', 0.92), ('percussion', 0.78), ('beat', 0.45)]
    """
    try:
        # Ensure mono audio
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)

        # Resample to 16kHz (Essentia models expect 16kHz)
        if sr != 16000:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

        # Minimum length check - effnet needs ~1 second of audio
        min_samples = 16000  # 1 second at 16kHz
        if len(audio) < min_samples:
            # Pad with zeros (silence) to minimum length
            padding = np.zeros(min_samples - len(audio))
            audio = np.concatenate([audio, padding])

        # Stage 1: Extract embeddings using discogs-effnet base model (cached)
        effnet = get_effnet_model()
        embeddings = effnet(audio)

        # Check if embeddings are empty
        if embeddings.size == 0:
            raise AnalysisFailedError(
                "Audio too short for classification",
                details={"stage": "instrument classification", "audio_length": len(audio)}
            )

        # Convert to numpy array if needed
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        # Average embeddings across patches
        if embeddings.ndim == 2:
            embeddings = np.mean(embeddings, axis=0)

        # Reshape to 2D for TensorflowPredict2D (expects [batch_size, features])
        embeddings_2d = embeddings.reshape(1, -1).astype(np.float32)

        # Stage 2: Pass embeddings to classification head (cached)
        if model_path is None:
            classifier = get_classifier_model("mtg_jamendo_instrument")
        else:
            # Custom model path - create new instance (not cached)
            classifier = es.TensorflowPredict2D(
                graphFilename=model_path,
                input="model/Placeholder",
                output="model/Sigmoid",
            )
        predictions_2d = classifier(embeddings_2d)

        # Extract first (and only) batch element
        predictions = predictions_2d[0]

        # Get top-k predictions
        top_indices = np.argsort(predictions)[-top_k:][::-1]
        top_predictions = [
            (INSTRUMENT_CLASSES[i], float(predictions[i]))
            for i in top_indices
        ]

        # Get top prediction
        instrument_type = top_predictions[0][0]
        instrument_confidence = top_predictions[0][1]

        return {
            "instrument_type": instrument_type,
            "instrument_confidence": instrument_confidence,
            "top_predictions": top_predictions,
        }

    except ModelLoadError:
        raise
    except Exception as e:
        raise AnalysisFailedError(
            "Instrument classification failed",
            details={
                "error": str(e),
                "stage": "instrument classification",
                "model": model_path or "default",
            }
        )


def extract_mood_tags(
    audio: np.ndarray,
    sr: int,
    top_k: int = 3,
    threshold: float = 0.1,
) -> list[str]:
    """Extract mood/theme tags using Essentia's mood classifiers.

    Uses MTG-Jamendo mood/theme classification model.
    This requires a two-stage pipeline:
    1. Extract embeddings using discogs-effnet base model
    2. Pass embeddings to classification head

    Args:
        audio: Audio samples as numpy array (mono or stereo)
        sr: Sample rate in Hz
        top_k: Maximum number of mood tags to return
        threshold: Minimum confidence threshold (0-1)

    Returns:
        List of mood tags sorted by confidence

    Raises:
        ModelLoadError: If model file not found
        AnalysisFailedError: If classification fails

    Example:
        >>> moods = extract_mood_tags(audio, 44100)
        >>> moods
        ['dark', 'electronic', 'energetic']
    """
    try:
        # Ensure mono audio
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)

        # Resample to 16kHz
        if sr != 16000:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

        # Minimum length check - effnet needs ~1 second of audio
        min_samples = 16000  # 1 second at 16kHz
        if len(audio) < min_samples:
            # Pad with zeros (silence) to minimum length
            padding = np.zeros(min_samples - len(audio))
            audio = np.concatenate([audio, padding])

        # Stage 1: Extract embeddings using discogs-effnet base model (cached)
        effnet = get_effnet_model()
        embeddings = effnet(audio)

        # Check if embeddings are empty
        if embeddings.size == 0:
            raise AnalysisFailedError(
                "Audio too short for mood classification",
                details={"stage": "mood classification", "audio_length": len(audio)}
            )

        # Convert to numpy array if needed
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        # Average embeddings across patches
        if embeddings.ndim == 2:
            embeddings = np.mean(embeddings, axis=0)

        # Reshape to 2D for TensorflowPredict2D (expects [batch_size, features])
        embeddings_2d = embeddings.reshape(1, -1).astype(np.float32)

        # Stage 2: Pass embeddings to classification head (cached)
        classifier = get_classifier_model("mtg_jamendo_moodtheme")
        predictions_2d = classifier(embeddings_2d)

        # Extract first (and only) batch element
        predictions = predictions_2d[0]

        # Filter by threshold and get top-k
        filtered_indices = np.where(predictions >= threshold)[0]
        filtered_predictions = predictions[filtered_indices]

        # Sort by confidence
        sorted_indices = np.argsort(filtered_predictions)[::-1][:top_k]
        top_mood_indices = filtered_indices[sorted_indices]

        # Map to mood labels
        mood_tags = [MOOD_CLASSES[i] for i in top_mood_indices]

        return mood_tags

    except ModelLoadError:
        raise
    except Exception as e:
        raise AnalysisFailedError(
            "Mood classification failed",
            details={
                "error": str(e),
                "stage": "mood classification",
            }
        )


def extract_genre_tags(
    audio: np.ndarray,
    sr: int,
    top_k: int = 3,
    threshold: float = 0.1,
) -> list[str]:
    """Extract genre tags using Essentia's genre classifiers.

    Uses MTG-Jamendo genre classification model.
    This requires a two-stage pipeline:
    1. Extract embeddings using discogs-effnet base model
    2. Pass embeddings to classification head

    Args:
        audio: Audio samples as numpy array (mono or stereo)
        sr: Sample rate in Hz
        top_k: Maximum number of genre tags to return
        threshold: Minimum confidence threshold (0-1)

    Returns:
        List of genre tags sorted by confidence

    Raises:
        ModelLoadError: If model file not found
        AnalysisFailedError: If classification fails

    Example:
        >>> genres = extract_genre_tags(audio, 44100)
        >>> genres
        ['techno', 'electronic', 'house']
    """
    try:
        # Ensure mono audio
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)

        # Resample to 16kHz
        if sr != 16000:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

        # Minimum length check - effnet needs ~1 second of audio
        min_samples = 16000  # 1 second at 16kHz
        if len(audio) < min_samples:
            # Pad with zeros (silence) to minimum length
            padding = np.zeros(min_samples - len(audio))
            audio = np.concatenate([audio, padding])

        # Stage 1: Extract embeddings using discogs-effnet base model (cached)
        effnet = get_effnet_model()
        embeddings = effnet(audio)

        # Check if embeddings are empty
        if embeddings.size == 0:
            raise AnalysisFailedError(
                "Audio too short for genre classification",
                details={"stage": "genre classification", "audio_length": len(audio)}
            )

        # Convert to numpy array if needed
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        # Average embeddings across patches
        if embeddings.ndim == 2:
            embeddings = np.mean(embeddings, axis=0)

        # Reshape to 2D for TensorflowPredict2D (expects [batch_size, features])
        embeddings_2d = embeddings.reshape(1, -1).astype(np.float32)

        # Stage 2: Pass embeddings to classification head (cached)
        classifier = get_classifier_model("mtg_jamendo_genre")
        predictions_2d = classifier(embeddings_2d)

        # Extract first (and only) batch element
        predictions = predictions_2d[0]

        # Filter by threshold and get top-k
        filtered_indices = np.where(predictions >= threshold)[0]
        filtered_predictions = predictions[filtered_indices]

        # Sort by confidence
        sorted_indices = np.argsort(filtered_predictions)[::-1][:top_k]
        top_genre_indices = filtered_indices[sorted_indices]

        # Map to genre labels
        genre_tags = [GENRE_CLASSES[i] for i in top_genre_indices]

        return genre_tags

    except ModelLoadError:
        raise
    except Exception as e:
        raise AnalysisFailedError(
            "Genre classification failed",
            details={
                "error": str(e),
                "stage": "genre classification",
            }
        )
