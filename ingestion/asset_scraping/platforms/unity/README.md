# Unity Asset Store Metadata Scraper

A tool for scraping and processing metadata from Unity Asset Store listings in your "My Assets" library.

## Overview

This project extracts metadata from your Unity Asset Store assets, including:
- Asset titles and descriptions
- Keywords/tags
- License information
- Asset Store IDs and URLs

The scraper uses Playwright browser automation to navigate your "My Assets" page and extract metadata from each asset's detail page.

## Quick Start

### 1. Setup & Authentication

First, authenticate with Unity Asset Store:

```bash
cd setup
python3 generate_unity_auth.py
```

This will launch a browser where you can log in. Your session will be saved to `setup/auth.json`.

**See [setup/README.md](setup/README.md) for detailed authentication instructions.**

### 2. Scrape Metadata

```bash
cd scraping
python3 scrape_unity_metadata.py
```

The scraper will process all assets in your library and save results to `output/unity_metadata.json`.

**See [scraping/README.md](scraping/README.md) for detailed scraping documentation.**

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         WORKFLOW                            │
└─────────────────────────────────────────────────────────────┘

1. SETUP & AUTHENTICATION (setup/)
   └─→ generate_unity_auth.py (interactive login)
         ↓
   auth.json created

2. SCRAPING (scraping/)
   ├─→ Load auth from setup/auth.json
   ├─→ Navigate to "My Assets" page
   ├─→ Iterate through all pages
   ├─→ Extract metadata from each asset
   └─→ Save to output/unity_metadata.json

3. POST-PROCESSING (post_processing/)
   └─→ [Future] HTML to Markdown conversion

4. OUTPUT (output/)
   └─→ unity_metadata.json (metadata export)
```

## Project Structure

```
unity-scraper/
├── README.md                # This file
├── setup/                   # Authentication
│   ├── README.md
│   ├── generate_unity_auth.py
│   └── auth.json            # Your auth state (gitignored)
├── scraping/                # Main scraping functionality
│   ├── README.md
│   └── scrape_unity_metadata.py
├── post_processing/         # Future: HTML to Markdown conversion
│   └── README.md
├── output/                  # Generated files
│   └── unity_metadata.json
└── docs/                    # Future: GUI documentation
    └── README.md
```

## Features

### Current
- **Modal-based navigation** - Maintains pagination state while scraping
- **Robust selectors** - Multiple fallback strategies for reliability
- **Error handling** - Individual failures don't stop the scraper
- **Automatic pagination** - Handles multi-page asset libraries

### Planned
- **GUI interface** - Similar to fab-scraper with progress tracking
- **Parallel execution** - Faster scraping with multiple workers
- **HTML to Markdown** - Clean description formatting
- **Resume capability** - Skip already-scraped assets
- **Command-line options** - Headless mode, output path, etc.

## Requirements

- Python 3.7+
- Playwright (for browser automation)

```bash
pip install playwright
python3 -m playwright install
```

## Output Format

The scraper generates JSON with this structure:

```json
[
  {
    "asset_store_id": "12345",
    "title": "Fantasy Dragon Pack",
    "description": "High-quality dragon models with animations...",
    "keywords": ["3D", "Characters", "Fantasy", "Dragons"],
    "license_text": "Standard Unity Asset Store License",
    "original_url": "https://assetstore.unity.com/packages/3d/characters/fantasy-dragon-pack-12345"
  }
]
```

## Performance

- **Per asset**: ~1-2 seconds (requires full page load)
- **100 assets**: ~3-5 minutes
- **Large libraries**: Consider running overnight

The modal-based approach is necessary to maintain pagination state but requires individual page loads.

## Documentation

- **[Setup & Authentication](setup/README.md)** - How to authenticate with Unity Asset Store
- **[Scraping Guide](scraping/README.md)** - Command-line usage and technical details
- **[Post-Processing](post_processing/README.md)** - Future HTML to Markdown conversion
- **[GUI Documentation](docs/README.md)** - Future GUI user guide

## Troubleshooting

### Common Issues

**auth.json not found**
- Run setup first: `cd setup && python3 generate_unity_auth.py`
- See [setup/README.md](setup/README.md)

**Could not find assets**
- Your `auth.json` may have expired
- Regenerate using the setup script
- Make sure you're logged in to Unity Asset Store

**Slow performance**
- This is expected - each asset requires a full page load
- For large libraries, let it run overnight
- Future: Parallel execution support

**Script hangs**
- Try running in non-headless mode to see what's happening
- Check internet connection
- Website structure may have changed

## Integration

This scraper is part of the Game Asset Tracking System. The output can be:
1. Manually reviewed for completeness
2. Merged with filesystem-scanned data (future feature)
3. Used to enrich Asset Pack manifests with Unity-specific metadata

See the main project documentation for the complete data flow.

## License

This tool is for personal use with your own Unity Asset Store library. Respect Unity's terms of service.
