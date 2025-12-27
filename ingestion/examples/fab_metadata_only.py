"""Fab marketplace integration example - metadata only.

This example demonstrates how to:
- Authenticate with Fab marketplace
- Generate manifests without downloading files
- Save manifests for all library assets

NOTE: This example requires fab-api-client and authentication setup.
See the following projects for more information:
- fab-api-client: https://github.com/brentlopez/fab-api-client
- asset-marketplace-client-core: https://github.com/brentlopez/asset-marketplace-client-core
"""

import json
import sys
from pathlib import Path

try:
    from fab_api_client import FabClient
except ImportError:
    print("Error: fab-api-client not installed", file=sys.stderr)
    print("Install with: uv sync --extra fab", file=sys.stderr)
    print("\nFor more information:", file=sys.stderr)
    print("- fab-api-client: https://github.com/brentlopez/fab-api-client", file=sys.stderr)
    print("- asset-marketplace-client-core: https://github.com/brentlopez/asset-marketplace-client-core", file=sys.stderr)
    sys.exit(1)

from game_asset_tracker_ingestion import SourceRegistry


def main():
    # Note: Authentication setup is required
    # Refer to fab-api-client and asset-marketplace-client-core for details
    
    print("Fab Marketplace Integration Example", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print("\nNOTE: You need to set up authentication first.", file=sys.stderr)
    print("See fab-api-client documentation for details.\n", file=sys.stderr)
    
    # Example placeholder - replace with actual authentication
    # from fab_egl_adapter import FabEGLAdapter
    # adapter = FabEGLAdapter()
    # auth_provider = adapter.get_auth_provider()
    # client = FabClient(auth=auth_provider)
    
    print("To use this example:", file=sys.stderr)
    print("1. Set up authentication (see fab-api-client)", file=sys.stderr)
    print("2. Uncomment the authentication code above", file=sys.stderr)
    print("3. Uncomment the pipeline code below", file=sys.stderr)
    print("\nExample (once authenticated):", file=sys.stderr)
    print("-" * 50, file=sys.stderr)
    
    # Example code (commented out until authentication is set up)
    """
    # Create pipeline with metadata-only strategy
    pipeline = SourceRegistry.create_pipeline(
        'fab',
        client=client,
        download_strategy='metadata_only'
    )
    
    # Generate manifests
    output_dir = Path("manifests/fab")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for manifest in pipeline.generate_manifests():
        # Save each manifest
        output_file = output_dir / f"{manifest['pack_id']}.json"
        with open(output_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ {manifest['pack_name']}", file=sys.stderr)
        count += 1
    
    print(f"\nGenerated {count} manifests in {output_dir}", file=sys.stderr)
    """
    
    print("\n# Create pipeline", file=sys.stderr)
    print("pipeline = SourceRegistry.create_pipeline(", file=sys.stderr)
    print("    'fab',", file=sys.stderr)
    print("    client=client,", file=sys.stderr)
    print("    download_strategy='metadata_only'", file=sys.stderr)
    print(")", file=sys.stderr)
    print("\n# Generate and save manifests", file=sys.stderr)
    print("for manifest in pipeline.generate_manifests():", file=sys.stderr)
    print("    # Process manifest...", file=sys.stderr)
    

if __name__ == '__main__':
    main()
