# Fab Metadata Scraping

This directory contains the main scraper for extracting metadata from Fab.com listings.

## Quick Start

### Basic Usage

```bash
cd scraping
python3 scrape_fab_metadata.py --headless
```

This will:
1. Load authentication from `../setup/auth.json`
2. Scrape the Fab.com library page
3. Collect all listing URLs
4. Extract metadata from each listing
5. Save to `../output/fab_metadata.json`

### Common Options

```bash
# Sequential scraping with headless browser
python3 scrape_fab_metadata.py --headless

# Skip library scrape and use pre-collected URLs
python3 scrape_fab_metadata.py --skip-library-scrape --headless

# Parallel scraping with 5 workers
python3 scrape_fab_metadata.py --parallel 5 --headless

# Skip captcha pages automatically
python3 scrape_fab_metadata.py --skip-on-captcha --headless
```

## Command-Line Arguments

### Core Options
- `--headless` - Run browser without GUI (recommended for production)
- `--out PATH` - Output JSON file (default: `../output/fab_metadata.json`)
- `--parallel N` - Number of parallel workers (default: 1 = sequential)

### Library Scraping
- `--max-scrolls N` - Safety limit for infinite scroll (default: 50)
- `--scroll-step N` - Pixels per scroll (default: 1200)
- `--scroll-steps N` - Incremental scrolls per round (default: 8)
- `--test-scroll` - Test scrolling without scraping

### URL Management
- `--skip-library-scrape` - Use pre-collected URLs instead of scraping library
- `--use-url-file PATH` - URL file to load (default: `../setup/fab_library_urls.json`)
- `--force-rescrape` - Re-scrape URLs even if already in output file

### Captcha Handling
- `--skip-on-captcha` - Skip pages with captchas instead of waiting
- `--new-browser-per-page` - Fresh browser per page (helps avoid captchas)
- `--reuse-browser` - Reuse browser, fresh context per URL (faster)
- `--randomize-ua` - Randomize User-Agent and viewport
- `--captcha-retry` - Retry captcha pages once with backoff

### Performance
- `--block-heavy` - Block images/media/fonts for faster loading
- `--sleep-min-ms MS` - Minimum delay between pages (default: 300)
- `--sleep-max-ms MS` - Maximum delay between pages (default: 800)
- `--burst-size N` - Insert longer sleep after N pages (default: 5)
- `--burst-sleep-ms MS` - Burst sleep duration (default: 3000)

### Bandwidth Measurement
- `--measure-bytes` - Track bandwidth usage per listing
- `--measure-report PATH` - JSONL report file (default: `../output/fab_bandwidth_report.jsonl`)

### Proxies
- `--proxy URL` - Proxy URL (can be repeated)
- `--proxy-list PATH` - File with one proxy URL per line

## Parallel Scraping

The scraper supports parallel execution for faster scraping of large libraries.

### How It Works

```
Main Process
    ↓
ProcessPoolExecutor (N workers)
    ├─→ Worker 1: Browser 1 → URL 1
    ├─→ Worker 2: Browser 2 → URL 2
    └─→ Worker N: Browser N → URL N
         ↓
    File Lock (thread-safe writes)
         ↓
    Output JSON
```

Each worker runs an independent browser instance and writes results as they complete.

### Performance

| Workers | Time (100 pages) | Speedup |
|---------|------------------|---------|
| 1       | ~50 minutes      | 1x      |
| 2       | ~25 minutes      | 2x      |
| 5       | ~10 minutes      | 5x      |
| 10      | ~5 minutes       | 10x     |

**Resource usage per worker:**
- CPU: 10-20%
- Memory: 200-500 MB
- Network: Scales linearly

### Recommended Settings

```bash
# Good balance (most cases)
python3 scrape_fab_metadata.py --parallel 5 --headless --skip-on-captcha

# Conservative (fewer captchas)
python3 scrape_fab_metadata.py --parallel 3 --headless

# Maximum speed (10 workers)
python3 scrape_fab_metadata.py --parallel 10 --headless --skip-on-captcha
```

### When to Use Parallel Mode

**Use parallel mode when:**
- Scraping 50+ URLs
- Fast, stable network
- Adequate system resources (8+ GB RAM)
- Time is critical

**Use sequential mode when:**
- Scraping <50 URLs
- Slow or unstable network
- Limited system resources
- Avoiding rate limits is critical

## Avoiding Captchas

Captchas are more common with parallel scraping. Mitigation strategies:

1. **Use headless mode** - Less detectable
2. **Enable skip-on-captcha** - Don't block on captchas
3. **Limit workers** - 5 or fewer is safer
4. **Randomize behavior** - Use `--randomize-ua`
5. **Add delays** - Increase sleep times

```bash
# Captcha-friendly configuration
python3 scrape_fab_metadata.py \
  --parallel 3 \
  --headless \
  --skip-on-captcha \
  --randomize-ua \
  --sleep-min-ms 500 \
  --sleep-max-ms 1500
```

## Output Format

The scraper generates JSON with the following structure:

```json
[
  {
    "fab_id": "uuid-string",
    "title": "Asset Pack Name",
    "description": "HTML description",
    "tags": ["tag1", "tag2"],
    "license_text": "License information",
    "original_url": "https://www.fab.com/listings/uuid"
  }
]
```

## Troubleshooting

### Workers hang or timeout
- Reduce worker count: `--parallel 3`
- Check system resources (CPU/memory)

### High memory usage
- Lower workers: `--parallel 3`
- Use headless mode: `--headless`
- Block heavy resources: `--block-heavy`

### Too many captchas
- Reduce workers: `--parallel 2`
- Enable skip: `--skip-on-captcha`
- Randomize UA: `--randomize-ua`
- Increase delays

### auth.json not found
- Make sure you've run setup (see `../setup/README.md`)
- Verify file exists at `../setup/auth.json`

### JSON file corruption
This shouldn't happen due to file locking, but if it does:
1. Stop the scraper
2. Restore from backup
3. Reduce worker count and retry

### Rate limiting / IP ban
- Use fewer workers (1-3)
- Add longer delays
- Use proxy rotation: `--proxy-list`
