#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def run_filesystem(args: argparse.Namespace) -> None:
    from game_asset_tracker_ingestion.registry import SourceRegistry

    pipeline = SourceRegistry.create_pipeline(
        "filesystem",
        path=Path(args.path),
        pack_name=args.name,
        tags=args.tags or [],
        license_url=args.license,
    )

    for manifest in pipeline.generate_manifests():
        print(json.dumps(manifest, indent=2))


def run_fab(args: argparse.Namespace) -> None:
    try:
        from fab_egl_adapter import EpicGamesLauncherAuth, MitmproxyExtractor
        from fab_api_client import FabClient
    except ImportError:
        print("FAB dependencies not installed. Run: uv sync --extra fab", file=sys.stderr)
        sys.exit(1)

    from game_asset_tracker_ingestion.registry import SourceRegistry

    print("Initializing FAB authentication...", file=sys.stderr)
    print("This will open Epic Games Launcher to capture auth cookies.", file=sys.stderr)
    extractor = MitmproxyExtractor()
    cookies = extractor.capture_cookies(auto_install_cert=True)
    auth = EpicGamesLauncherAuth(cookies=cookies)
    client = FabClient(auth=auth)

    print("Creating FAB pipeline...", file=sys.stderr)
    pipeline = SourceRegistry.create_pipeline(
        "fab",
        client=client,
        download_strategy=args.download_strategy,
    )

    output_dir = Path(args.output_dir) if args.output_dir else Path("manifests/fab")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching FAB library assets...", file=sys.stderr)
    manifest_count = 0
    for manifest in pipeline.generate_manifests():
        manifest_count += 1
        pack_id = manifest.get("pack_id", f"pack_{manifest_count}")
        output_path = output_dir / f"{pack_id}.json"
        output_path.write_text(json.dumps(manifest, indent=2))
        print(f"Saved: {output_path}", file=sys.stderr)
        print(json.dumps(manifest))

    print(f"Completed: {manifest_count} manifests generated", file=sys.stderr)


def run_uas(args: argparse.Namespace) -> None:
    try:
        from uas_adapter import UnityHubAuth, AssetDownloader
        from uas_adapter.extractors import ElectronExtractor
        from uas_adapter.parsers import PackageExtractor
        from uas_api_client import UnityClient
    except ImportError:
        print("UAS dependencies not installed. Run: uv sync --extra uas", file=sys.stderr)
        sys.exit(1)

    from game_asset_tracker_ingestion.registry import SourceRegistry

    print("Initializing UAS authentication...", file=sys.stderr)
    extractor = ElectronExtractor()
    tokens = extractor.extract_tokens()
    auth = UnityHubAuth(
        access_token=tokens["accessToken"],
        access_token_expiration=tokens["accessTokenExpiration"],
        refresh_token=tokens["refreshToken"],
    )
    client = UnityClient(auth, rate_limit_delay=1.5)

    output_dir = Path(args.output_dir) if args.output_dir else Path("manifests/uas")
    output_dir.mkdir(parents=True, exist_ok=True)

    strategy = args.download_strategy

    if strategy in ("download", "extract"):
        print(f"Running UAS ingestion with {strategy} strategy...", file=sys.stderr)
        downloader = AssetDownloader(auth)
        pkg_extractor = PackageExtractor() if strategy == "extract" else None
        downloads_dir = output_dir / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        library = client.get_library()
        manifest_count = 0

        for item in library.results:
            asset_id = str(item.package_id)
            print(f"Downloading {item.display_name} ({asset_id})...", file=sys.stderr)

            def progress_cb(msg: str) -> None:
                print(f"  {msg}", file=sys.stderr)

            result = downloader.download_asset(
                asset_id=asset_id,
                output_dir=str(downloads_dir),
                on_progress=progress_cb,
            )
            print(
                f"  Downloaded: {result['file_path']} ({result['size_mb']:.2f} MB)", file=sys.stderr
            )

            if strategy == "extract" and pkg_extractor:
                extract_dir = output_dir / "extracted" / asset_id
                extract_dir.mkdir(parents=True, exist_ok=True)
                pkg_extractor.extract_package(result["file_path"], str(extract_dir))
                print(f"  Extracted to: {extract_dir}", file=sys.stderr)

            manifest_count += 1

        print(f"Completed: {manifest_count} packages processed", file=sys.stderr)
        return

    if strategy == "manifests_only":
        print("Running UAS ingestion with manifests_only strategy...", file=sys.stderr)
        downloader = AssetDownloader(auth)
        library = client.get_library()
        manifest_count = 0

        for item in library.results:
            asset_id = str(item.package_id)
            print(f"Fetching download info for {item.display_name}...", file=sys.stderr)
            download_info = downloader.get_download_info(asset_id)
            manifest = {
                "pack_id": f"uas_{asset_id}",
                "name": item.display_name,
                "source": "uas",
                "download_url": download_info.get("url"),
                "decryption_key": download_info.get("key"),
            }
            manifest_count += 1
            output_path = output_dir / f"uas_{asset_id}.json"
            output_path.write_text(json.dumps(manifest, indent=2))
            print(f"Saved: {output_path}", file=sys.stderr)
            print(json.dumps(manifest))

        print(f"Completed: {manifest_count} manifests generated", file=sys.stderr)
        return

    print("Creating UAS pipeline (metadata_only)...", file=sys.stderr)
    pipeline = SourceRegistry.create_pipeline(
        "uas",
        client=client,
        download_strategy="metadata_only",
    )

    print("Fetching UAS library assets...", file=sys.stderr)
    manifest_count = 0
    for manifest in pipeline.generate_manifests():
        manifest_count += 1
        pack_id = manifest.get("pack_id", f"pack_{manifest_count}")
        output_path = output_dir / f"{pack_id}.json"
        output_path.write_text(json.dumps(manifest, indent=2))
        print(f"Saved: {output_path}", file=sys.stderr)
        print(json.dumps(manifest))

    print(f"Completed: {manifest_count} manifests generated", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="GUI helper for game-asset-tracker ingestion")
    subparsers = parser.add_subparsers(dest="source", required=True)

    fs_parser = subparsers.add_parser("filesystem", help="Ingest from filesystem")
    fs_parser.add_argument("--path", required=True, help="Path to asset directory")
    fs_parser.add_argument("--name", required=True, help="Pack name")
    fs_parser.add_argument("--tags", nargs="*", default=[], help="Tags")
    fs_parser.add_argument("--license", help="License URL")

    fab_parser = subparsers.add_parser("fab", help="Ingest from FAB (Epic)")
    fab_parser.add_argument(
        "--download-strategy",
        choices=["metadata_only", "manifests_only"],
        default="metadata_only",
        help="Download strategy",
    )
    fab_parser.add_argument("--output-dir", help="Output directory for manifests")

    uas_parser = subparsers.add_parser("uas", help="Ingest from UAS (Unity)")
    uas_parser.add_argument(
        "--download-strategy",
        choices=["metadata_only", "manifests_only", "download", "extract"],
        default="metadata_only",
        help="Download strategy: metadata_only (API only), manifests_only (get download info), download (download+decrypt), extract (download+decrypt+extract)",
    )
    uas_parser.add_argument("--output-dir", help="Output directory for manifests")

    args = parser.parse_args()

    if args.source == "filesystem":
        run_filesystem(args)
    elif args.source == "fab":
        run_fab(args)
    elif args.source == "uas":
        run_uas(args)


if __name__ == "__main__":
    main()
