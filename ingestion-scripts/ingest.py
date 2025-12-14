#!/usr/bin/env python3
"""
Game Asset Tracking System - Ingestion Script

Scans a directory tree and generates a JSON manifest conforming to the
strict schema defined in ARCHITECTURE.md.

Features:
- Heuristic tagging from folder structure
- Metadata extraction (size, extension, audio duration)
- UUID generation for pack identification
- JSON output to stdout for easy piping
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# Optional: Audio metadata extraction
try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def extract_audio_metadata(file_path: str) -> Optional[Dict[str, str]]:
    """
    Extract metadata from audio files using mutagen.
    
    Args:
        file_path: Absolute path to the audio file
        
    Returns:
        Dictionary with audio metadata or None if extraction fails
    """
    if not MUTAGEN_AVAILABLE:
        return None
    
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            return None
        
        metadata = {}
        
        # Extract duration
        if hasattr(audio.info, 'length'):
            duration_seconds = audio.info.length
            metadata['duration'] = f"{duration_seconds:.2f}s"
        
        # Extract sample rate
        if hasattr(audio.info, 'sample_rate'):
            metadata['sample_rate'] = str(audio.info.sample_rate)
        
        # Extract bitrate
        if hasattr(audio.info, 'bitrate'):
            metadata['bitrate'] = str(audio.info.bitrate)
        
        # Extract channels
        if hasattr(audio.info, 'channels'):
            metadata['channels'] = str(audio.info.channels)
        
        return metadata if metadata else None
    
    except Exception:
        # Fail silently and continue
        return None


def derive_local_tags(relative_path: str) -> List[str]:
    """
    Derive tags from the folder structure.
    
    Example:
        "Audio/Explosions/SciFi/boom.wav" -> ["Audio", "Explosions", "SciFi"]
    
    Args:
        relative_path: Path relative to pack root
        
    Returns:
        List of tags derived from folder names
    """
    path_parts = Path(relative_path).parts
    # Exclude the filename itself, only use directory names
    return list(path_parts[:-1]) if len(path_parts) > 1 else []


def scan_directory(root_path: str, pack_id: str) -> List[Dict]:
    """
    Recursively scan a directory and collect asset metadata.
    
    Args:
        root_path: Absolute path to the pack root directory
        pack_id: UUID for the pack
        
    Returns:
        List of asset dictionaries conforming to the schema
    """
    assets = []
    root_path_obj = Path(root_path).resolve()
    
    # Walk the directory tree
    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            # Skip hidden files and system files
            if filename.startswith('.'):
                continue
            
            file_path = Path(dirpath) / filename
            
            try:
                # Get file stats
                stat_info = file_path.stat()
                size_bytes = stat_info.st_size
                
                # Calculate relative path
                relative_path = file_path.relative_to(root_path_obj)
                
                # Extract file extension
                file_type = file_path.suffix.lstrip('.').lower()
                if not file_type:
                    file_type = "unknown"
                
                # Derive local tags from folder structure
                local_tags = derive_local_tags(str(relative_path))
                
                # Initialize metadata
                metadata = {}
                
                # Try to extract audio metadata
                audio_extensions = {'wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac', 'wma'}
                if file_type in audio_extensions:
                    audio_metadata = extract_audio_metadata(str(file_path))
                    if audio_metadata:
                        metadata.update(audio_metadata)
                
                # Build asset dictionary
                asset = {
                    "relative_path": str(relative_path),
                    "file_type": file_type,
                    "size_bytes": size_bytes,
                    "metadata": metadata,
                    "local_tags": local_tags
                }
                
                assets.append(asset)
            
            except Exception as e:
                # Log error to stderr but continue processing
                print(f"Warning: Failed to process {file_path}: {e}", file=sys.stderr)
                continue
    
    return assets


def generate_manifest(
    pack_name: str,
    root_path: str,
    source: str,
    global_tags: List[str],
    license_link: Optional[str] = None
) -> Dict:
    """
    Generate a complete JSON manifest for an asset pack.
    
    Args:
        pack_name: Human-readable name of the pack
        root_path: Absolute path to the pack root directory
        source: Origin of the pack (e.g., "Unity Asset Store")
        global_tags: Tags applicable to the entire pack
        license_link: Optional URL or path to license documentation
        
    Returns:
        Dictionary conforming to the strict JSON schema
    """
    # Generate unique pack ID
    pack_id = str(uuid.uuid4())
    
    # Resolve root path to absolute
    root_path_abs = str(Path(root_path).resolve())
    
    # Scan directory and collect assets
    print(f"Scanning directory: {root_path_abs}", file=sys.stderr)
    assets = scan_directory(root_path_abs, pack_id)
    print(f"Found {len(assets)} assets", file=sys.stderr)
    
    # Build manifest
    manifest = {
        "pack_id": pack_id,
        "pack_name": pack_name,
        "root_path": root_path_abs,
        "source": source,
        "license_link": license_link or "",
        "global_tags": global_tags,
        "assets": assets
    }
    
    return manifest


def main():
    """Main entry point for the ingestion script."""
    parser = argparse.ArgumentParser(
        description="Generate JSON manifest for game asset packs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python ingest.py --path /path/to/assets --name "My Pack" --source "Unity" --tags paid 3d

  # Pipe to file
  python ingest.py --path /path/to/assets --name "My Pack" --source "Unity" --tags music > output.json

  # With license link
  python ingest.py --path /path/to/assets --name "My Pack" --source "Unity" \\
      --tags paid music --license "https://example.com/license"
        """
    )
    
    parser.add_argument(
        '--path',
        required=True,
        help='Root directory to scan (absolute or relative path)'
    )
    
    parser.add_argument(
        '--name',
        required=True,
        help='Human-readable name of the asset pack'
    )
    
    parser.add_argument(
        '--source',
        required=True,
        help='Source of the pack (e.g., "Unity Asset Store", "Epic Marketplace")'
    )
    
    parser.add_argument(
        '--tags',
        nargs='+',
        default=[],
        help='Global tags for the pack (space-separated)'
    )
    
    parser.add_argument(
        '--license',
        help='URL or file path to license documentation'
    )
    
    args = parser.parse_args()
    
    # Validate path exists
    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.path):
        print(f"Error: Path is not a directory: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    # Generate manifest
    try:
        manifest = generate_manifest(
            pack_name=args.name,
            root_path=args.path,
            source=args.source,
            global_tags=args.tags,
            license_link=args.license
        )
        
        # Output JSON to stdout
        json.dump(manifest, sys.stdout, indent=2)
        print()  # Add newline at end
        
    except Exception as e:
        print(f"Error: Failed to generate manifest: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
