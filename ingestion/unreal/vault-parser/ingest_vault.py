#!/usr/bin/env python3
"""
Unreal Engine VaultCache Asset Ingestion Script

This script scans the local VaultCache directory where Unreal Engine stores
downloaded assets from the Fab marketplace, parses their manifest files, and
generates standardized JSON manifests that conform to the Game Asset Tracking System schema.

It merges local file information from the VaultCache with web-scraped metadata
from fab_metadata.json to create fully hydrated asset pack manifests.
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional


def load_web_metadata(metadata_path: Path) -> Dict[str, dict]:
    """
    Load web-scraped metadata from fab_metadata.json into a lookup dictionary.
    
    Args:
        metadata_path: Path to the fab_metadata.json file
        
    Returns:
        Dictionary keyed by asset title (lowercase) for case-insensitive matching
    """
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
        
        # Create lookup dictionary keyed by lowercase title for matching
        lookup = {}
        for item in metadata_list:
            title = item.get('title', '').strip()
            if title:
                lookup[title.lower()] = item
        
        return lookup
    except FileNotFoundError:
        print(f"Warning: Web metadata file not found at {metadata_path}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse web metadata JSON: {e}", file=sys.stderr)
        return {}


def parse_json_manifest(manifest_path: Path) -> Optional[dict]:
    """
    Parse a JSON manifest file from the VaultCache.
    
    Args:
        manifest_path: Path to the manifest file
        
    Returns:
        Parsed manifest dictionary or None if parsing fails
    """
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Not a JSON file (might be binary)
        return None
    except Exception as e:
        print(f"Warning: Failed to read manifest at {manifest_path}: {e}", file=sys.stderr)
        return None


def extract_file_extension(filename: str) -> str:
    """
    Extract and normalize file extension.
    
    Args:
        filename: The filename to extract extension from
        
    Returns:
        Lowercase extension without dot (e.g., 'png', 'fbx', 'uasset')
    """
    ext = Path(filename).suffix.lstrip('.').lower()
    return ext if ext else 'unknown'


def derive_local_tags(relative_path: str) -> List[str]:
    """
    Derive local tags from the folder structure of a file path.
    
    Args:
        relative_path: The relative path of the file
        
    Returns:
        List of lowercase tags derived from folder names
    """
    path_parts = Path(relative_path).parts
    if len(path_parts) > 1:
        # Use folder names as tags (exclude filename itself)
        tags = []
        for part in path_parts[:-1]:
            if part and not part.startswith('.'):
                # Normalize: lowercase, replace underscores/spaces with hyphens
                normalized = part.lower().replace('_', '-').replace(' ', '-')
                tags.append(normalized)
        return tags
    return []


def get_actual_file_size(data_folder: Path, relative_path: str) -> int:
    """
    Get the actual file size from the data folder.
    
    Args:
        data_folder: Path to the data folder
        relative_path: Relative path of the file
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    file_path = data_folder / relative_path
    try:
        if file_path.exists():
            return file_path.stat().st_size
    except Exception:
        pass
    return 0


def build_manifest_from_vault(
    vault_folder: Path,
    web_lookup: Dict[str, dict]
) -> Optional[dict]:
    """
    Build a standardized asset pack manifest from a VaultCache folder.
    
    Args:
        vault_folder: Path to the vault cache folder (contains data/ and manifest)
        web_lookup: Dictionary of web-scraped metadata keyed by title
        
    Returns:
        Asset pack manifest conforming to schema or None if parsing fails
    """
    manifest_file = vault_folder / 'manifest'
    data_folder = vault_folder / 'data'
    
    # Check if manifest file exists
    if not manifest_file.exists():
        print(f"Warning: No manifest file in {vault_folder.name}", file=sys.stderr)
        return None
    
    # Parse the manifest
    manifest_data = parse_json_manifest(manifest_file)
    if not manifest_data:
        # Binary manifest - skip for V1
        print(f"Info: Skipping binary manifest in {vault_folder.name}", file=sys.stderr)
        return None
    
    # Extract title from CustomFields first (more human-readable), fallback to AppNameString
    app_name = None
    custom_fields = manifest_data.get('CustomFields', {})
    
    # Try Vault.TitleText first (human-readable name)
    if 'Vault.TitleText' in custom_fields:
        app_name = custom_fields['Vault.TitleText']
    
    # Fallback to AppNameString
    if not app_name:
        app_name = manifest_data.get('AppNameString', manifest_data.get('AppName', ''))
    
    if not app_name:
        print(f"Warning: No AppName found in manifest for {vault_folder.name}", file=sys.stderr)
        app_name = vault_folder.name  # Fallback to folder name
    
    # Try to match with web metadata
    web_meta = web_lookup.get(app_name.lower())
    
    # Generate pack_id
    pack_id = str(uuid.uuid4())
    
    # Build global_tags from web metadata
    global_tags = []
    if web_meta:
        tags = web_meta.get('tags', [])
        # Normalize tags to lowercase with hyphens
        global_tags = [tag.lower().replace(' ', '-') for tag in tags if tag]
    
    # Get license link - prefer web metadata URL, fallback to Vault.ActionUrl
    license_link = None
    if web_meta:
        license_link = web_meta.get('original_url')
    elif 'Vault.ActionUrl' in custom_fields:
        license_link = custom_fields['Vault.ActionUrl']
    
    # Build assets array from FileManifestList
    assets = []
    file_manifest_list = manifest_data.get('FileManifestList', [])
    
    for file_entry in file_manifest_list:
        filename = file_entry.get('Filename', '')
        
        if not filename:
            continue
        
        # Get actual file size from data folder
        file_size = get_actual_file_size(data_folder, filename)
        
        # Build asset entry
        asset = {
            'relative_path': filename,
            'file_type': extract_file_extension(filename),
            'size_bytes': file_size
        }
        
        # Derive local_tags from path (folder structure)
        local_tags = derive_local_tags(filename)
        if local_tags:
            asset['local_tags'] = local_tags
        
        assets.append(asset)
    
    # Skip if no assets found
    if not assets:
        print(f"Warning: No assets found in manifest for {vault_folder.name}", file=sys.stderr)
        return None
    
    # Build the complete manifest
    manifest = {
        'pack_id': pack_id,
        'pack_name': app_name,
        'root_path': str(data_folder.resolve()),
        'source': 'Fab Marketplace',
        'assets': assets
    }
    
    # Add optional fields
    if license_link:
        manifest['license_link'] = license_link
    
    if global_tags:
        manifest['global_tags'] = global_tags
    
    return manifest


def scan_vault_cache(vault_cache_path: Path, web_lookup: Dict[str, dict]) -> tuple[List[dict], int, int]:
    """
    Scan the VaultCache directory and build manifests for all assets.
    
    Args:
        vault_cache_path: Path to the VaultCache directory
        web_lookup: Dictionary of web-scraped metadata
        
    Returns:
        Tuple of (manifests list, matched_count, orphaned_count)
    """
    manifests = []
    matched_count = 0
    orphaned_count = 0
    
    if not vault_cache_path.exists():
        print(f"Error: VaultCache directory not found at {vault_cache_path}", file=sys.stderr)
        return manifests, 0, 0
    
    # Iterate through all folders in VaultCache
    for vault_folder in vault_cache_path.iterdir():
        if not vault_folder.is_dir():
            continue
        
        # Skip hidden folders and the FabLibrary metadata folder
        if vault_folder.name.startswith('.') or vault_folder.name == 'FabLibrary':
            continue
        
        manifest = build_manifest_from_vault(vault_folder, web_lookup)
        if manifest:
            manifests.append(manifest)
            
            # Check if matched with web metadata
            if manifest.get('global_tags') or (manifest.get('license_link') and 'fab.com' in manifest.get('license_link', '')):
                matched_count += 1
            else:
                orphaned_count += 1
    
    return manifests, matched_count, orphaned_count


def main():
    """Main entry point for the script."""
    # Define paths
    script_dir = Path(__file__).parent
    vault_cache_path = Path('/Users/Shared/UnrealEngine/Launcher/VaultCache')
    web_metadata_path = script_dir.parent.parent / 'asset_scraping' / 'platforms' / 'fab' / 'output' / 'fab_metadata.json'
    output_path = script_dir / 'output' / 'vault_assets.json'
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("Loading web metadata...", file=sys.stderr)
    web_lookup = load_web_metadata(web_metadata_path)
    print(f"Loaded {len(web_lookup)} web metadata entries", file=sys.stderr)
    
    print(f"\nScanning VaultCache at {vault_cache_path}...", file=sys.stderr)
    manifests, matched_count, orphaned_count = scan_vault_cache(vault_cache_path, web_lookup)
    
    # Write output
    if manifests:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifests, f, indent=2)
        
        print(f"\n✓ Success!", file=sys.stderr)
        print(f"Found {len(manifests)} cached assets. {matched_count} matched with Web Metadata.", file=sys.stderr)
        if orphaned_count > 0:
            print(f"({orphaned_count} orphan assets without web metadata)", file=sys.stderr)
        print(f"\nOutput written to: {output_path}", file=sys.stderr)
    else:
        print("\nNo assets found in VaultCache.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
