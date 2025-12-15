# Fab Metadata Scraper GUI

A graphical user interface for the Fab metadata scraper that makes it easy to configure and run without using command-line arguments.

## Features

- **Checkbox toggles** for all boolean flags
- **Text inputs** for numeric and file parameters  
- **File browser dialogs** for selecting input/output files
- **Progress bar** showing scraping progress with current/total page count
- **Real-time log display** with color-coded messages
- **Start/Stop controls** to manage the scraping process
- **Thread-safe operation** - GUI remains responsive during scraping
- **Tabbed interface** - Separate tabs for Scraping and Post-Processing

## Installation

The GUI uses Python's built-in Tkinter library, so no additional dependencies are required beyond what's needed for the scraper itself.

```bash
# Install scraper dependencies (if not already installed)
pip install playwright beautifulsoup4
playwright install
```

## Usage

### Launch the GUI

From the project root:

```bash
python3 scraper_gui.py
```

Or make it executable and run directly:

```bash
chmod +x scraper_gui.py
./scraper_gui.py
```

### Scraping Tab

The GUI is organized into sections:

#### Options (Boolean Flags)
- **Headless mode**: Run browser without GUI
- **Clear cache before scraping**: Delete existing output file before starting
- **Test scroll only**: Test infinite scroll without scraping (for debugging)
- **Skip library scrape**: Load URLs from file instead of scraping library page
- **Skip pages with captchas**: Auto-skip captcha pages instead of waiting
- **Force rescrape all URLs**: Re-scrape even if already in output file
- **New browser per page**: Open fresh browser for each URL (helps avoid captchas)
- **Reuse browser**: Reuse one browser per worker (new context per URL)
- **Randomize UA + viewport**: Randomize User-Agent and viewport per context
- **Captcha backoff + retry**: Retry captcha pages once with backoff
- **Block heavy resources**: Block images/media/fonts/analytics for faster loading
- **Measure bytes**: Track bandwidth usage and write JSONL report

#### Parameters (Values)
- **Max scrolls**: Safety limit for scroll attempts (default: 50)
- **Scroll step (px)**: Pixels to scroll per increment (default: 1200)
- **Scroll steps per round**: Number of incremental scrolls per round (default: 8)
- **Parallel workers**: Number of browser instances to run simultaneously (default: 1 = sequential)
  - Set to 2-10 for faster scraping
  - Each worker opens its own browser instance
  - Uses thread-safe file locking for JSON writes
- **Output file**: JSON file to save metadata (default: `output/fab_metadata.json`)
- **URL file**: JSON file with URLs to scrape (for skip-library mode, default: `setup/fab_library_urls.json`)
- **Sleep min/max (ms)**: Delay range between pages
- **Burst size/sleep**: Insert longer delays periodically
- **Proxy list file**: File with proxy URLs (one per line)
- **Measure report**: JSONL file for bandwidth tracking (default: `output/fab_bandwidth_report.jsonl`)

Use the **Browse** buttons to select files via dialog.

#### Running the Scraper

1. Configure your desired options and parameters
2. Click **Start Scraping**
3. Monitor progress:
   - **Progress bar** shows completion percentage
   - **Progress label** shows current/total pages (e.g., "15 / 100 pages scraped")
   - **Log output** displays real-time messages from the scraper
4. Click **Stop** to cancel if needed
   - Sends SIGTERM to all worker processes
   - Waits 3 seconds for graceful shutdown
   - Force kills with SIGKILL if processes don't stop
   - Cleans up any orphaned browser processes

### Post-Processing Tab

#### Conversion Options
- **Input JSON file**: File to convert (default: `output/fab_metadata.json`)
- **Output JSON file**: Where to save converted file (leave empty to overwrite input)
- **Parallel workers**: Number of workers for conversion (default: 4)

#### Running Conversion

1. Set input/output files
2. Adjust workers if desired
3. Click **Convert to Markdown**
4. Monitor progress in conversion log

### Log Output

The log area shows real-time output with color coding:
- **Blue**: Info messages (commands, status)
- **Black**: Standard output
- **Orange**: Warnings and debug messages
- **Red**: Errors
- **Green**: Success messages

Use **Clear Log** to reset the log area.

## Tips

### For First-Time Runs
- Leave "Headless mode" **unchecked** to see the browser (helpful for debugging)
- Consider using "Test scroll only" first to verify scraping works

### To Avoid Captchas
- Enable "New browser per page" - each page gets a fresh browser instance
- Or enable "Skip pages with captchas" - automatically skip problem pages
- Parallel mode (workers > 1) automatically uses fresh browsers per page
- Enable "Randomize UA + viewport" for better stealth

### For Faster Scraping
- Set "Parallel workers" to 2-10 (e.g., 5 workers = 5x faster)
- Higher values may trigger rate limiting or captchas
- Monitor system resources (CPU/memory) with high worker counts
- Parallel mode uses thread-safe file locking to prevent data corruption

### To Resume Interrupted Scraping
- The scraper automatically resumes by checking existing output file
- Disable "Force rescrape" to skip already-scraped URLs
- Enable "Force rescrape" to re-scrape everything

### To Scrape Specific URLs
1. Create a JSON file with URL array (e.g., `my_urls.json`)
2. Enable "Skip library scrape"
3. Set "URL file" to your JSON file
4. Start scraping

## Troubleshooting

### GUI doesn't launch
- Ensure you're using Python 3.7+
- On Linux, install Tkinter: `sudo apt-get install python3-tk`

### \"Script not found\" error
- Make sure files are in correct locations after reorganization
- Check that `scraping/scrape_fab_metadata.py` exists
- Check that `post_processing/convert_html_to_markdown.py` exists

### Process hangs
- Click "Stop" to terminate all processes
- Graceful shutdown attempted first (SIGTERM, 3 second timeout)
- Force kill used if needed (SIGKILL to entire process group)
- Orphaned browser processes are cleaned up automatically

### Captcha blocks all pages
- Enable "New browser per page" to get fresh sessions
- Or use "Skip pages with captchas" and manually scrape blocked pages later
- Try "Randomize UA + viewport" for better stealth

## Technical Details

- Uses Tkinter for cross-platform GUI
- Runs scraper in background thread to keep UI responsive
- Captures stdout/stderr in real-time via subprocess.Popen
- Thread-safe log updates using queue.Queue
- Auto-scrolls log to show latest messages

### Parallel Scraping Implementation
- Uses Python's `ProcessPoolExecutor` for worker management (required for Playwright)
- Each worker process launches its own Playwright browser instance
- File locking (`fcntl.flock`) protects JSON writes across processes
- Append-only writes minimize lock contention
- Results saved as they complete (not batched)
- Worker count is configurable (1 = sequential, >1 = parallel)
- **Note**: Uses multiprocessing, not threading (Playwright sync API requires processes)

## Keyboard Shortcuts

- **Cmd+Q** (Mac) / **Alt+F4** (Windows/Linux): Quit application

## Related Documentation

- [Setup & Authentication](../setup/README.md) - How to authenticate with Fab.com
- [Scraping Guide](../scraping/README.md) - Command-line scraping documentation
- [Post-Processing](../post_processing/README.md) - HTML to Markdown conversion
