# HTML to Markdown Conversion

This document explains how to convert the HTML descriptions in `fab_metadata.json` to clean Markdown format.

## What it Does

The conversion script (`convert_html_to_markdown.py`):
- Reads `fab_metadata.json` with HTML descriptions
- Converts each description from HTML to Markdown
- Moves the original HTML to a new `raw_description` field
- Replaces the `description` field with clean Markdown
- Uses parallel processing for speed (4 workers by default)

## Using the GUI

The easiest way to convert is using the GUI:

1. Run `python3 scraper_gui.py`
2. Click the **Post-Processing** tab
3. Set the input file (defaults to `fab_metadata.json`)
4. Optionally set an output file (leave empty to overwrite input)
5. Adjust parallel workers if desired (more = faster)
6. Click **Convert to Markdown**

The conversion log will show real-time progress.

## Using the Command Line

### Basic Usage (overwrites input file)

```bash
python3 convert_html_to_markdown.py fab_metadata.json
```

### Save to Different File

```bash
python3 convert_html_to_markdown.py fab_metadata.json -o fab_metadata_markdown.json
```

### Adjust Parallel Workers

```bash
python3 convert_html_to_markdown.py fab_metadata.json -w 8
```

### Quiet Mode (no progress messages)

```bash
python3 convert_html_to_markdown.py fab_metadata.json -q
```

## Output Format

### Before Conversion
```json
{
  "fab_id": "...",
  "title": "...",
  "description": "<div>...lots of HTML...</div>",
  "tags": [...],
  "license_text": "...",
  "original_url": "..."
}
```

### After Conversion
```json
{
  "fab_id": "...",
  "title": "...",
  "description": "## Description\n\n**20 Stylized Slashes** with...",
  "raw_description": "<div>...original HTML...</div>",
  "tags": [...],
  "license_text": "...",
  "original_url": "..."
}
```

## Performance

- **Sequential**: ~1-2 seconds per entry
- **Parallel (4 workers)**: ~0.3-0.5 seconds per entry
- **For 154 entries**: ~30-60 seconds with 4 workers

## Dependencies

The script requires:
- `beautifulsoup4` - for HTML parsing

Install with:
```bash
pip install beautifulsoup4
```

## What Gets Converted

The converter extracts:
- Headings (h1-h6) → `# Heading`
- Paragraphs (p) → Plain text
- Lists (ul/ol) → `- item` or `1. item`
- Links (a) → `[text](url)`
- Bold (strong/b) → `**text**`
- Italic (em/i) → `*text*`
- Code (code) → `` `text` ``

It removes:
- Navigation elements (buttons, tabs)
- UI framework classes (fabkit-*)
- Thumbnails and badges
- Screen reader only content

## Reverting

If you need to revert to HTML descriptions:
1. Keep a backup of the original file before conversion
2. Or use the `raw_description` field (which contains the original HTML)

## Troubleshooting

**Error: Input file not found**
- Check that `fab_metadata.json` exists in the current directory
- Use an absolute path: `python3 convert_html_to_markdown.py /full/path/to/file.json`

**Conversion is slow**
- Increase parallel workers: `-w 8` or `-w 12`
- Note: Too many workers (>20) may not help due to Python's GIL

**Some descriptions look weird**
- The HTML structure from FAB can be complex
- Check the `raw_description` field for the original HTML
- Report any systematic issues for improvement
