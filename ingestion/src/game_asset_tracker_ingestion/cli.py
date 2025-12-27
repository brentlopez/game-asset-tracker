"""Command-line interface for the asset ingestion tool.

This module provides the CLI entry point for generating JSON manifests
from asset directories.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

from .scanner import scan_directory, validate_url
from .types import Manifest
from .validator import validate_manifest_with_error_details


def generate_manifest(
    pack_name: str,
    root_path: Path,
    source: str,
    global_tags: list[str],
    license_link: str | None = None,
) -> Manifest:
    """Generate a complete JSON manifest for an asset pack.

    Args:
        pack_name: Human-readable name of the pack
        root_path: Absolute path to the pack root directory
        source: Origin of the pack (e.g., "Unity Asset Store")
        global_tags: Tags applicable to the entire pack
        license_link: Optional URL or path to license documentation

    Returns:
        Dictionary conforming to the strict JSON schema

    Raises:
        ValueError: If input validation fails
    """
    # Validate license URL if provided
    if license_link:
        validate_url(license_link)

    # Generate unique pack ID (lowercase UUID as per schema)
    pack_id = str(uuid.uuid4())

    # Resolve root path to absolute
    root_path_abs = root_path.resolve()

    # Scan directory and collect assets
    print(f"Scanning directory: {root_path_abs}", file=sys.stderr)
    assets = scan_directory(root_path_abs)
    print(f"Found {len(assets)} assets", file=sys.stderr)

    # Build manifest
    manifest = Manifest(
        pack_id=pack_id,
        pack_name=pack_name,
        root_path=str(root_path_abs),
        source=source,
        license_link=license_link or "",
        global_tags=global_tags,
        assets=assets,
    )

    return manifest


def main() -> None:
    """Main entry point for the ingestion script."""
    parser = argparse.ArgumentParser(
        description="Generate JSON manifest for game asset packs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  ingest --path /path/to/assets --name "My Pack" --source "Unity" --tags paid 3d

  # Pipe to file
  ingest --path /path/to/assets --name "My Pack" --source "Unity" --tags music > output.json

  # With license link
  ingest --path /path/to/assets --name "My Pack" --source "Unity" \\
      --tags paid music --license "https://example.com/license"
        """,
    )

    parser.add_argument(
        "--path", required=True, help="Root directory to scan (absolute or relative path)"
    )

    parser.add_argument("--name", required=True, help="Human-readable name of the asset pack")

    parser.add_argument(
        "--source",
        required=True,
        help='Source of the pack (e.g., "Unity Asset Store", "Epic Marketplace")',
    )

    parser.add_argument(
        "--tags",
        nargs="+",
        default=[],
        help="Global tags for the pack (space-separated)",
    )

    parser.add_argument("--license", help="URL or file path to license documentation")

    args = parser.parse_args()

    # Validate path exists
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    if not path.is_dir():
        print(f"Error: Path is not a directory: {path}", file=sys.stderr)
        sys.exit(1)

    # Generate manifest
    try:
        manifest = generate_manifest(
            pack_name=args.name,
            root_path=path,
            source=args.source,
            global_tags=args.tags,
            license_link=args.license,
        )

        # Validate against JSON schema
        print("Validating manifest against schema...", file=sys.stderr)
        is_valid, error_msg = validate_manifest_with_error_details(manifest)

        if not is_valid:
            print("Error: Manifest validation failed:", file=sys.stderr)
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        print("Validation successful!", file=sys.stderr)

        # Output JSON to stdout
        json.dump(manifest, sys.stdout, indent=2)
        print()  # Add newline at end

    except Exception as e:
        print(f"Error: Failed to generate manifest: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
