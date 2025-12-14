# Unity Asset Store Metadata Scraper

This script scrapes metadata from your "My Assets" page on the Unity Asset Store.

## Prerequisites

1. **Python 3.7+** installed
2. **Playwright** and its browser binaries installed
3. **Valid authentication** saved in `auth.json`

## Setup

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
python3 -m playwright install
```

### 3. Generate Authentication File

You must create an `auth.json` file containing valid Unity Asset Store login credentials.

**Run this command to generate `auth.json`:**

```bash
python3 -m playwright codegen --save-storage=auth.json https://assetstore.unity.com/account/assets
```

This will:
1. Open a browser window
2. Navigate to the Unity Asset Store "My Assets" page
3. **You must log in manually** in the browser
4. Once logged in and on the "My Assets" page, **close the browser window**
5. Your authentication cookies will be saved to `auth.json`

**⚠️ Important:** 
- Do NOT commit `auth.json` to version control (it contains your login session)
- `auth.json` expires after some time - regenerate it if the scraper fails with authentication errors

## Usage

### Run the Scraper

```bash
python3 scrape_unity_metadata.py
```

**What it does:**
1. Loads authentication from `auth.json`
2. Navigates to your "My Assets" page
3. Iterates through all pages of assets
4. For each asset:
   - Opens the asset modal
   - Extracts the detail page URL
   - Opens the detail page in a new tab
   - Scrapes metadata (title, description, keywords, license)
   - Closes the tab and modal
5. Handles pagination automatically
6. Outputs results to `unity_metadata.json`

### Output Format

The script generates `unity_metadata.json` containing an array of asset objects:

```json
[
  {
    "asset_store_id": "12345",
    "title": "Fantasy Dragon Pack",
    "description": "High-quality dragon models with animations...",
    "keywords": ["3D", "Characters", "Fantasy", "Dragons"],
    "license_text": "Standard Unity Asset Store License",
    "original_url": "https://assetstore.unity.com/packages/3d/characters/fantasy-dragon-pack-12345"
  },
  ...
]
```

### Headless Mode

To run without opening a visible browser window, edit `scrape_unity_metadata.py`:

```python
browser = p.chromium.launch(headless=True)  # Change False to True
```

## Troubleshooting

### "auth.json not found"
Run the codegen command again to generate a new authentication file.

### "Could not find assets"
Your `auth.json` may have expired. Regenerate it using the codegen command.

### Script hangs or crashes
- Check your internet connection
- The Unity Asset Store website may have changed its structure
- Try running in non-headless mode to see what's happening
- Check if you have many assets (hundreds) - this will take time

### Slow performance
- Each asset requires opening a detail page, which takes 1-2 seconds
- For 100 assets, expect 3-5 minutes of runtime
- This is necessary to avoid losing pagination state

## Technical Details

### Navigation Strategy

The scraper uses a **modal-based approach** to avoid losing pagination state:

1. Stay on the main "My Assets" list page
2. Click asset name → opens modal
3. Extract detail URL from "View Full Details" link (without clicking)
4. Open detail URL in new tab/page
5. Scrape metadata
6. Close tab
7. Close modal
8. Continue to next asset

This ensures we never navigate away from the paginated list.

### Selectors

The script uses multiple fallback strategies for robustness:

- **Asset links:** `[data-test="package-name"]`
- **Modal title:** `#quick-look-title`
- **Description:** `#collapse-panel-description`
- **Keywords:** Heading "Related keywords" + sibling links (with XPath fallback)
- **License:** CSS selector (brittle) with text search fallback
- **Pagination:** `nav[role="navigation"]` button with name "Next"

### Error Handling

- Individual asset failures don't stop the scraper
- Modal close failures trigger Escape key as fallback
- Missing data fields are set to empty strings/arrays
- Progress messages logged to stderr, JSON output to stdout (if redirected)

## Integration with Main Ingestion Pipeline

This scraper is independent from the main `ingest.py` script. The output `unity_metadata.json` can be:

1. Manually reviewed for completeness
2. Merged with filesystem-scanned data (future feature)
3. Used to enrich Asset Pack manifests with Unity-specific metadata

See the main project `ARCHITECTURE.md` for the complete data flow.
