# Unity Asset Store Metadata Scraping

This directory contains the main scraper for extracting metadata from Unity Asset Store listings in your "My Assets" library.

## Quick Start

### Basic Usage

```bash
cd scraping
python3 scrape_unity_metadata.py
```

This will:
1. Load authentication from `../setup/auth.json`
2. Navigate to your "My Assets" page
3. Iterate through all pages of assets
4. Extract metadata from each asset detail page
5. Save to `../output/unity_metadata.json`

## How It Works

The scraper uses a **modal-based navigation strategy** to avoid losing pagination state:

1. Stay on the main "My Assets" list page
2. Click asset name → opens modal
3. Extract detail URL from "View Full Details" link
4. Open detail URL in new tab/page
5. Scrape metadata (title, description, keywords, license)
6. Close tab
7. Close modal
8. Continue to next asset
9. Handle pagination automatically

This ensures we never navigate away from the paginated list, maintaining our position.

## Configuration

### Headless Mode

To run without opening a visible browser window, edit `scrape_unity_metadata.py`:

```python
browser = p.chromium.launch(headless=True)  # Change False to True
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

- Each asset requires opening a detail page: ~1-2 seconds per asset
- For 100 assets, expect 3-5 minutes of runtime
- The modal-based approach is necessary to maintain pagination state

## Troubleshooting

### "auth.json not found"
- Run setup first: `cd ../setup && python3 generate_unity_auth.py`
- See [../setup/README.md](../setup/README.md)

### "Could not find assets"
- Your `auth.json` may have expired
- Regenerate it using the setup scripts
- Make sure you're logged in to Unity Asset Store

### Script hangs or crashes
- Check your internet connection
- The Unity Asset Store website may have changed its structure
- Try running in non-headless mode to see what's happening
- Check if you have many assets (hundreds) - this will take time

### Slow performance
- This is expected - each asset requires a full page load
- For large libraries, consider running overnight
- Future: GUI with parallel execution support

### Modal won't close
- The scraper tries multiple strategies to close modals
- If problems persist, the website structure may have changed
- Try pressing Escape manually to see if the modal closes

## Technical Details

### Selectors Used

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
- Progress messages logged to stderr

## Integration

This scraper is independent from the main `ingest.py` script. The output can be:
1. Manually reviewed for completeness
2. Merged with filesystem-scanned data (future feature)
3. Used to enrich Asset Pack manifests with Unity-specific metadata

## Future Enhancements

- [ ] Parallel execution support (via GUI)
- [ ] Command-line arguments for headless mode and output path
- [ ] Resume capability (skip already-scraped assets)
- [ ] Progress reporting with counts
- [ ] Retry failed assets
