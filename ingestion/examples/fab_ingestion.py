"""Example: Generate manifests for all Fab assets in user's library.

This script demonstrates the complete workflow for ingesting Fab marketplace
assets using the three-tier authentication architecture:
- Tier 3: fab-egl-adapter extracts credentials from Epic Games Launcher
- Tier 2: fab-api-client uses credentials to authenticate API calls
- Tier 1: game-asset-tracker-ingestion transforms data to manifests

Prerequisites:
- fab-api-client installed: uv sync --extra fab
- fab-egl-adapter installed (for authentication)
- Epic Games Launcher installed with active session
"""

import json
import sys
from pathlib import Path


def main():
    """Generate manifests for all Fab assets in user's library."""
    
    # Check if Fab support is available
    try:
        from game_asset_tracker_ingestion import SourceRegistry
        
        if 'fab' not in SourceRegistry.list_sources():
            print("Error: Fab platform not available.", file=sys.stderr)
            print("Install with: uv sync --extra fab", file=sys.stderr)
            return 1
    except ImportError as e:
        print(f"Error: Could not import ingestion library: {e}", file=sys.stderr)
        return 1
    
    # Tier 3: Extract authentication from Epic Games Launcher
    print("Step 1: Extracting authentication from Epic Games Launcher...")
    try:
        from fab_egl_adapter import FabEGLAdapter
        
        adapter = FabEGLAdapter()
        auth_provider = adapter.get_auth_provider()
        print("✓ Authentication extracted successfully")
    except Exception as e:
        print(f"Error: Could not extract authentication from EGL: {e}", file=sys.stderr)
        print("\nTroubleshooting:", file=sys.stderr)
        print("- Ensure Epic Games Launcher is installed", file=sys.stderr)
        print("- Ensure you're logged into Epic Games Launcher", file=sys.stderr)
        print("- Try restarting Epic Games Launcher", file=sys.stderr)
        return 1
    
    # Tier 2: Create authenticated Fab client
    print("\nStep 2: Creating authenticated Fab client...")
    try:
        from fab_api_client import FabClient
        
        client = FabClient(auth=auth_provider)
        print("✓ Fab client created successfully")
    except Exception as e:
        print(f"Error: Could not create Fab client: {e}", file=sys.stderr)
        return 1
    
    # Tier 1: Create ingestion pipeline
    print("\nStep 3: Creating ingestion pipeline...")
    try:
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=client,
            download_strategy='metadata_only'  # Phase 2: metadata only
        )
        print("✓ Pipeline created successfully")
    except Exception as e:
        print(f"Error: Could not create pipeline: {e}", file=sys.stderr)
        return 1
    
    # Setup output directory
    output_dir = Path("manifests/fab")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nStep 4: Generating manifests to {output_dir}/")
    
    # Generate manifests
    count = 0
    errors = 0
    
    try:
        for manifest in pipeline.generate_manifests():
            pack_id = manifest['pack_id']
            pack_name = manifest['pack_name']
            
            # Write to file
            output_file = output_dir / f"{pack_id}.json"
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                
                print(f"  ✓ {pack_name} → {output_file.name}")
                count += 1
            except Exception as e:
                print(f"  ✗ Failed to write {pack_name}: {e}", file=sys.stderr)
                errors += 1
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError during manifest generation: {e}", file=sys.stderr)
        return 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Generated {count} manifests in {output_dir}")
    if errors > 0:
        print(f"Failed to write {errors} manifests", file=sys.stderr)
    print(f"{'='*60}")
    
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
