"""Basic filesystem scanning example.

This example demonstrates how to:
- Scan a local directory
- Generate a manifest
- Display summary statistics
- Save output to JSON file
"""

import json
import sys
from pathlib import Path

from game_asset_tracker_ingestion import SourceRegistry


def main():
    # Scan a directory (change this to your asset directory)
    asset_dir = Path.home() / "Documents" / "GameAssets"
    
    if not asset_dir.exists():
        print(f"Directory not found: {asset_dir}", file=sys.stderr)
        print(f"Please update the asset_dir variable in this script", file=sys.stderr)
        return
    
    print(f"Scanning directory: {asset_dir}", file=sys.stderr)
    
    # Create pipeline
    pipeline = SourceRegistry.create_pipeline('filesystem', path=asset_dir)
    
    # Generate manifest
    manifest = next(pipeline.generate_manifests())
    
    # Display summary
    print(f"\n✓ Manifest generated successfully", file=sys.stderr)
    print(f"  Pack: {manifest['pack_name']}", file=sys.stderr)
    print(f"  Files: {len(manifest['assets'])}", file=sys.stderr)
    
    total_size = sum(a['size_bytes'] for a in manifest['assets'])
    print(f"  Total size: {total_size / 1024**2:.1f} MB", file=sys.stderr)
    
    # Save to file
    output_file = Path("manifest.json")
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest saved to {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
