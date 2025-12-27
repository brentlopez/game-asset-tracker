"""Metadata extraction for various file types.

This module handles format-specific metadata extraction, such as audio duration,
sample rate, image dimensions, etc.
"""

from pathlib import Path

from .types import AssetMetadata

# Optional: Audio metadata extraction
try:
    from mutagen import File as MutagenFile  # type: ignore[attr-defined]

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    MutagenFile = None


# Set of audio file extensions that we can extract metadata from
AUDIO_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a", "aac", "wma"}


def extract_audio_metadata(file_path: Path) -> AssetMetadata:
    """Extract metadata from audio files using mutagen.

    Args:
        file_path: Path to the audio file

    Returns:
        Dictionary with audio metadata (duration, sample_rate, bitrate, channels)
        Returns empty dict if extraction fails or mutagen is not available.
    """
    if not MUTAGEN_AVAILABLE:
        return AssetMetadata()

    try:
        audio = MutagenFile(str(file_path))
        if audio is None:
            return AssetMetadata()

        metadata = AssetMetadata()

        # Extract duration
        if hasattr(audio.info, "length"):
            duration_seconds = audio.info.length
            metadata["duration"] = f"{duration_seconds:.2f}s"  # type: ignore[typeddict-unknown-key]

        # Extract sample rate
        if hasattr(audio.info, "sample_rate"):
            metadata["sample_rate"] = str(audio.info.sample_rate)  # type: ignore[typeddict-unknown-key]

        # Extract bitrate
        if hasattr(audio.info, "bitrate"):
            metadata["bitrate"] = str(audio.info.bitrate)  # type: ignore[typeddict-unknown-key]

        # Extract channels
        if hasattr(audio.info, "channels"):
            metadata["channels"] = str(audio.info.channels)  # type: ignore[typeddict-unknown-key]

        return metadata

    except Exception:
        # Fail silently and return empty metadata
        return AssetMetadata()


def extract_metadata(file_path: Path, file_type: str) -> AssetMetadata:
    """Extract metadata for a file based on its type.

    Args:
        file_path: Path to the file
        file_type: File extension (lowercase)

    Returns:
        Dictionary with format-specific metadata
    """
    # Extract audio metadata for audio files
    if file_type in AUDIO_EXTENSIONS:
        return extract_audio_metadata(file_path)

    # Future: Add image metadata extraction (dimensions, color depth, etc.)
    # Future: Add 3D model metadata extraction (poly count, vertices, etc.)

    return AssetMetadata()
