#!/usr/bin/env python3
"""Example: Generate manifests for Unity Asset Store assets.

This script demonstrates how to use the UAS platform integration to generate
JSON manifests for assets in your Unity Asset Store library.

Prerequisites:
1. Install with UAS support:
   cd ingestion && uv sync --extra uas

2. Authentication setup (requires uas-adapter):
   The uas-adapter package provides authentication helpers for Unity Asset Store.
   See uas-adapter documentation for setup instructions.

Architecture:
   This integration follows the asset-marketplace-client-core architecture.
   See asset-marketplace-client-core project for details on the multi-tier design.

For more information:
- uas-api-client: Core Unity API client library
- uas-adapter: Authentication and adapter utilities
- asset-marketplace-client-core: Architecture documentation
"""

import json
import sys
from pathlib import Path


def main():
    """Generate manifests for UAS assets."""
    
    # Check if UAS support is available
    try:
        from game_asset_tracker_ingestion import SourceRegistry
        
        if 'uas' not in SourceRegistry.list_sources():
            print("ERROR: UAS platform not available.", file=sys.stderr)
            print("Install with: uv sync --extra uas", file=sys.stderr)
            sys.exit(1)
    except ImportError as e:
        print(f"ERROR: Cannot import ingestion library: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Import UAS client libraries
    try:
        from uas_api_client import UnityClient
    except ImportError:
        print("ERROR: uas-api-client not installed.", file=sys.stderr)
        print("Install with: uv sync --extra uas", file=sys.stderr)
        sys.exit(1)
    
    # NOTE: Authentication requires uas-adapter package
    # The following code demonstrates the authentication workflow.
    # Refer to uas-adapter documentation for actual implementation.
    print("\n" + "="*70)
    print("Unity Asset Store Manifest Generation")
    print("="*70)
    print("\nNOTE: This example requires authentication setup via uas-adapter.")
    print("See uas-adapter project for authentication helpers and documentation.")
    print("\nArchitecture: This follows the asset-marketplace-client-core design.")
    print("See asset-marketplace-client-core project for multi-tier architecture details.\n")
    
    # Example authentication workflow (requires uas-adapter)
    print("Expected authentication workflow:")
    print("  1. Set up authentication (via uas-adapter)")
    print("  2. Initialize UnityClient with auth provider")
    print("  3. Create ingestion pipeline")
    print("  4. Generate manifests\n")
    
    # For demonstration, we'll show the expected code structure:
    print("Example code structure:")
    print("-" * 70)
    example_code = """
    # Step 1-2: Authentication (requires uas-adapter)
    # NOTE: Authentication setup has been removed from this example.
    # Refer to uas-adapter documentation for authentication methods.
    
    # Step 3: Create authenticated client
    # auth = ... # Create auth provider (see uas-adapter docs)
    # client = UnityClient(auth, rate_limit_delay=1.5)
    
    # Step 4: Create pipeline
    from game_asset_tracker_ingestion import SourceRegistry
    
    pipeline = SourceRegistry.create_pipeline(
        'uas',
        client=client,
        download_strategy='metadata_only'  # Phase 2: metadata only
    )
    
    # Step 5: Generate manifests
    output_dir = Path("manifests/uas")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for manifest in pipeline.generate_manifests():
        pack_name = manifest['pack_name']
        output_file = output_dir / f"{manifest['pack_id']}.json"
        
        with open(output_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ Generated manifest for: {pack_name}")
        
        # Show asset metadata
        asset = manifest['assets'][0]  # Phase 2: single placeholder asset
        metadata = asset['metadata']
        if 'publisher' in metadata:
            print(f"  Publisher: {metadata['publisher']}")
        if 'category' in metadata:
            print(f"  Category: {metadata['category']}")
        if 'unity_version' in metadata:
            print(f"  Unity Version: {metadata['unity_version']}")
        if 'price' in metadata:
            print(f"  Price: ${metadata['price']}")
        if 'package_size_mb' in metadata:
            print(f"  Size: {metadata['package_size_mb']} MB")
        print()
    
    print(f"\\nManifests saved to: {output_dir}")
    """
    print(example_code)
    print("-" * 70)
    
    print("\nTo run this workflow:")
    print("1. Install uas-adapter (see uas-adapter documentation)")
    print("2. Set up authentication following uas-adapter documentation")
    print("3. Modify this script to include your authentication setup")
    print("4. Run: python examples/uas_ingestion.py\n")
    
    print("For more information:")
    print("- uas-api-client: Unity API client library")
    print("- uas-adapter: Authentication and adapter utilities")
    print("- asset-marketplace-client-core: Architecture documentation\n")


if __name__ == '__main__':
    main()
