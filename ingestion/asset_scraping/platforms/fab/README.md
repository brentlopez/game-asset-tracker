# Fab Metadata Scraper

A comprehensive tool for scraping and processing metadata from Fab.com (Unreal Engine Marketplace) listings.

## Overview

This project provides both GUI and command-line interfaces for:
1. **Authenticating** with Fab.com
2. **Scraping** metadata from your Fab library
3. **Post-processing** HTML descriptions to clean Markdown

The scraper supports parallel execution for fast scraping of large libraries, with built-in captcha mitigation and bandwidth measurement.

## Quick Start

### 1. Setup & Authentication

First, authenticate with Fab.com:

```bash
cd setup
python3 generate_fab_auth.py
```

This will launch a browser where you can log in. Your session will be saved to `setup/auth.json`.

**See [setup/README.md](setup/README.md) for detailed authentication instructions.**

### 2. Scrape Metadata

#### Using the GUI (Recommended)

```bash
python3 scraper_gui.py
```

The GUI provides an easy interface for all scraping options with real-time progress tracking.

**See [docs/README.md](docs/README.md) for complete GUI documentation.**

#### Using Command Line

```bash
cd scraping
python3 scrape_fab_metadata.py --headless --parallel 5
```

**See [scraping/README.md](scraping/README.md) for all command-line options.**

### 3. Post-Process (Optional)

Convert HTML descriptions to clean Markdown:

```bash
cd post_processing
python3 convert_html_to_markdown.py ../output/fab_metadata.json
```

Or use the **Post-Processing** tab in the GUI.

**See [post_processing/README.md](post_processing/README.md) for conversion details.**

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         WORKFLOW                            │
└─────────────────────────────────────────────────────────────┘

1. SETUP & AUTHENTICATION (setup/)
   ├─→ generate_fab_auth.py (interactive login)
   │   OR
   └─→ convert_cookies.py (manual cookie export)
         ↓
   auth.json created
         ↓
   [Optional] extract_urls_console.js → fab_library_urls.json

2. SCRAPING (scraping/)
   ├─→ Load auth from setup/auth.json
   ├─→ Scrape Fab.com library (or use pre-collected URLs)
   ├─→ Extract metadata from each listing
   └─→ Save to output/fab_metadata.json

3. POST-PROCESSING (post_processing/)
   ├─→ Load output/fab_metadata.json
   ├─→ Convert HTML descriptions to Markdown
   └─→ Save updated JSON (with raw_description preserved)

4. OUTPUT (output/)
   └─→ fab_metadata.json (final clean metadata)
```

## Project Structure

```
fab-scraper/
├── scraper_gui.py           # Main GUI launcher
├── README.md                # This file
├── setup/                   # Authentication & URL collection
│   ├── README.md
│   ├── generate_fab_auth.py
│   ├── convert_cookies.py
│   ├── extract_urls_console.js
│   ├── auth.json            # Your auth state (gitignored)
│   └── fab_library_urls.json
├── scraping/                # Main scraping functionality
│   ├── README.md
│   └── scrape_fab_metadata.py
├── post_processing/         # HTML to Markdown conversion
│   ├── README.md
│   └── convert_html_to_markdown.py
├── output/                  # Generated files
│   ├── fab_metadata.json
│   └── fab_bandwidth_report.jsonl
└── docs/                    # GUI documentation
    └── README.md
```

## Features

### Scraping
- **Parallel execution** - 5-10x faster with multiple workers
- **Captcha mitigation** - Randomized UA, fresh browsers, backoff & retry
- **Resume capability** - Skip already-scraped URLs
- **Bandwidth measurement** - Track data usage per listing
- **Proxy support** - Rotate through multiple proxies
- **Flexible scheduling** - Configurable delays and burst patterns

### GUI
- **Two-tab interface** - Scraping and Post-Processing
- **Real-time progress** - Progress bar with current/total counts
- **Color-coded logs** - Easy-to-read status messages
- **File browsers** - Point-and-click file selection
- **Process control** - Start/Stop with graceful shutdown

### Post-Processing
- **Parallel conversion** - Fast HTML to Markdown conversion
- **Raw preservation** - Original HTML kept in `raw_description`
- **Clean output** - Removes navigation, UI elements, and clutter

## Requirements

- Python 3.7+
- Playwright (for browser automation)
- BeautifulSoup4 (for HTML conversion)

```bash
pip install playwright beautifulsoup4
playwright install
```

## Output Format

The scraper generates JSON with this structure:

```json
[
  {
    "fab_id": "uuid-string",
    "title": "Asset Pack Name",
    "description": "Clean Markdown description",
    "raw_description": "Original HTML (after conversion)",
    "tags": ["tag1", "tag2"],
    "license_text": "License information",
    "original_url": "https://www.fab.com/listings/uuid"
  }
]
```

## Performance

Parallel scraping dramatically speeds up large libraries:

| Workers | Time (100 pages) | Speedup |
|---------|------------------|---------|
| 1       | ~50 minutes      | 1x      |
| 5       | ~10 minutes      | 5x      |
| 10      | ~5 minutes       | 10x     |

**Resource usage per worker:**
- CPU: 10-20%
- Memory: 200-500 MB

## Manifest Fetching (Non-Functional)

⚠️ **The `--fetch-manifests` option exists but does not work due to Cloudflare protection.**

### Why It Doesn't Work

FAB's manifest API endpoints (`/e/artifacts/{id}/manifest`) are protected by Cloudflare's bot detection that blocks **all programmatic access**, even when:
- Requests are made from an authenticated browser
- Requests use JavaScript `fetch()` in the browser context
- All authentication cookies are included

**Result**: HTTP 403 Forbidden with Cloudflare challenge page

### What the Scraper Captures

The scraper successfully captures all publicly visible metadata:
- ✅ Title
- ✅ Description (HTML)
- ✅ Tags
- ✅ License text
- ✅ FAB ID (UUID)
- ✅ Original URL

But **cannot** access:
- ❌ Manifest data (download URLs, file lists)
- ❌ Artifact metadata
- ❌ Version-specific information

### Future Options

1. **Wait for FAB API changes** - Epic may provide official API access
2. **Parse library exports** - The `fab_library_export_*.json` files may contain some manifest data
3. **Manual extraction** - Not scalable for automation

## Documentation

- **[Setup & Authentication](setup/README.md)** - How to authenticate with Fab.com
- **[Scraping Guide](scraping/README.md)** - Command-line usage and all options
- **[Post-Processing](post_processing/README.md)** - HTML to Markdown conversion
- **[GUI Documentation](docs/README.md)** - Complete GUI user guide

## Troubleshooting

### Common Issues

**auth.json not found**
- Run setup first: `cd setup && python3 generate_fab_auth.py`
- See [setup/README.md](setup/README.md)

**Too many captchas**
- Reduce parallel workers
- Enable `--randomize-ua` and `--skip-on-captcha`
- See [scraping/README.md](scraping/README.md#avoiding-captchas)

**High memory usage**
- Reduce parallel workers
- Use `--headless` and `--block-heavy` flags

**Process hangs**
- Use GUI Stop button for graceful shutdown
- Or manually: `pkill -9 -f scrape_fab_metadata.py`

## License

This tool is for personal use with your own Fab.com library. Respect Fab.com's terms of service.
