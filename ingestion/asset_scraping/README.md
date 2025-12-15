# Asset Scraping

A modular, platform-agnostic system for scraping metadata from online game asset marketplaces.

## Overview

The Asset Scraping system provides a unified GUI for scraping metadata from multiple asset marketplaces (Fab, Unity Asset Store, etc.). It uses a plugin-based architecture where each platform implements a standard GUI module interface.

## Quick Start

### Prerequisites

```bash
cd /Users/brentlopez/Projects/game-asset-tracker/ingestion/asset_scraping
pip install -r requirements.txt
python3 -m playwright install
```

### Launch the GUI

```bash
python3 asset_scraper.py
```

The GUI will launch with a platform selector in the top-right corner. Select a platform to access its Setup, Scraping, and Post-Processing tabs.

## Architecture

### Platform-Agnostic Core

- **`asset_scraper.py`** - Main GUI application that:
  - Reads `platforms.json` to discover available platforms
  - Provides a dropdown selector for switching between platforms
  - Creates a consistent 3-tab interface (Setup, Scraping, Post-Processing)
  - Dynamically loads platform-specific GUI modules

### Platform Manifest

**`platforms.json`** defines available platforms:

```json
{
  "platforms": [
    {
      "id": "fab",
      "name": "Fab (Epic)",
      "gui_module": "platforms.fab.gui",
      "enabled": true
    },
    {
      "id": "unity",
      "name": "Unity Asset Store",
      "gui_module": "platforms.unity.gui",
      "enabled": true
    }
  ]
}
```

### Platform Structure

Each platform lives in `platforms/<platform_id>/` with the following structure:

```
platforms/
└── <platform_id>/
    ├── gui.py              # Platform GUI module (required)
    ├── setup/              # Authentication scripts
    ├── scraping/           # Scraping scripts
    ├── post_processing/    # Post-processing scripts
    ├── output/             # Generated files
    └── docs/               # Platform-specific documentation
```

## Platform GUI Module Interface

Each platform must provide a `gui.py` module with three functions:

```python
def create_setup_tab(parent, tk_vars):
    \"\"\"Render Setup tab content (authentication, configuration)\"\"\"
    pass

def create_scraping_tab(parent, tk_vars):
    \"\"\"Render Scraping tab content (options, controls, logs)\"\"\"
    pass

def create_postprocessing_tab(parent, tk_vars):
    \"\"\"Render Post-Processing tab content (conversion, enrichment)\"\"\"
    pass
```

### Tab Responsibilities

**Setup Tab:**
- Authentication workflow (generate/delete auth.json)
- Configuration options
- Status display

**Scraping Tab:**
- Scraping options and parameters
- Start/Stop controls
- Progress tracking
- Log output

**Post-Processing Tab:**
- Data conversion (e.g., HTML → Markdown)
- Metadata enrichment
- Validation

## Available Platforms

### Fab (Epic Marketplace)

**Location:** `platforms/fab/`

**Features:**
- Browser-based authentication
- Parallel scraping (1-10 workers)
- Captcha mitigation strategies
- HTML to Markdown conversion
- Bandwidth measurement

**Scripts:**
- `setup/generate_fab_auth.py` - Interactive authentication
- `scraping/scrape_fab_metadata.py` - Main scraper
- `post_processing/convert_html_to_markdown.py` - HTML conversion

See `platforms/fab/README.md` for detailed documentation.

### Unity Asset Store

**Location:** `platforms/unity/`

**Features:**
- Browser-based authentication
- Modal-based navigation for pagination
- Asset metadata extraction

**Scripts:**
- `setup/generate_unity_auth.py` - Interactive authentication
- `scraping/scrape_unity_metadata.py` - Main scraper

See `platforms/unity/README.md` for detailed documentation.

## Adding a New Platform

To add support for a new marketplace:

### 1. Create Platform Directory

```bash
mkdir -p platforms/<platform_id>/{setup,scraping,post_processing,output,docs}
```

### 2. Implement GUI Module

Create `platforms/<platform_id>/gui.py` with the three required functions:

```python
def create_setup_tab(parent, tk_vars):
    # Implement authentication UI
    pass

def create_scraping_tab(parent, tk_vars):
    # Implement scraping UI
    pass

def create_postprocessing_tab(parent, tk_vars):
    # Implement post-processing UI
    pass
```

### 3. Add to Platform Manifest

Edit `platforms.json`:

```json
{
  "platforms": [
    ...existing platforms...,
    {
      "id": "your_platform",
      "name": "Your Platform Name",
      "gui_module": "platforms.your_platform.gui",
      "enabled": true
    }
  ]
}
```

### 4. Implement Scripts

- `setup/generate_auth.py` - Authentication script
- `scraping/scrape_metadata.py` - Main scraper
- `post_processing/` - Any post-processing scripts

### 5. Document

Create `platforms/<platform_id>/README.md` with platform-specific documentation.

## Design Principles

### Separation of Concerns

- **Core GUI** (`asset_scraper.py`) handles window management and tab orchestration
- **Platform modules** (`gui.py`) handle platform-specific UI and logic
- **Scripts** handle actual scraping/processing work

### Consistent UX

All platforms have the same 3-tab structure:
1. **Setup** - Authentication and configuration
2. **Scraping** - Main scraping interface
3. **Post-Processing** - Data conversion and enrichment

### Modularity

- New platforms are added by creating a directory and implementing three functions
- No changes to core code required
- Platforms can be disabled via `platforms.json`

### Extensibility

The manifest-based approach allows:
- Easy addition of new platforms
- Platform-specific feature sets
- Independent versioning per platform

## Dependencies

See `requirements.txt` for required packages:

- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing
- `html2text` - HTML to Markdown conversion
- `requests` - HTTP requests

## Troubleshooting

### Platform Not Loading

- Check `platforms.json` for correct module path
- Ensure platform directory exists at `platforms/<platform_id>/`
- Verify `gui.py` exists and has required functions

### Authentication Issues

- Run the Setup tab's authentication workflow
- Check for `auth.json` in the platform's `setup/` directory
- Regenerate authentication if expired

### Script Errors

- Check platform-specific documentation in `platforms/<platform_id>/README.md`
- Review logs in the respective tab's log output area
- Ensure all required dependencies are installed

## License

See the main project README for license information.
