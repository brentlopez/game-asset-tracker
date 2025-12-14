# GUI Features Summary

## What's Included

### 1. **Organized Sections**

#### Options Section
7 checkbox toggles for boolean flags:
- Headless mode
- Clear cache before scraping
- Test scroll only (no scraping)
- Skip library scrape (use URL file)
- Skip pages with captchas
- Force rescrape all URLs
- New browser per page (avoid captchas)

#### Parameters Section
5 configurable parameters with text inputs:
- Max scrolls (default: 50)
- Scroll step in pixels (default: 1200)
- Scroll steps per round (default: 8)
- Output file (default: fab_metadata.json)
- URL file (default: fab_library_urls.json)

Each file parameter has a **Browse** button for easy file selection.

### 2. **Control Buttons**
- **Start Scraping** - Begins the scraping process
- **Stop** - Terminates the running process (force-kills after 5 sec timeout)
- **Clear Log** - Resets the log output area
- **Status indicator** - Shows current state (Ready/Running/Completed/Failed/Stopped)

### 3. **Progress Tracking**

#### Progress Bar
- Visual bar showing completion percentage (0-100%)
- Updates in real-time as pages are scraped

#### Progress Label
- Text display: "X / Y pages scraped"
- Updates automatically based on scraper output

Progress tracking parses these messages from stderr:
- `"Scraping 5/100: https://..."` → Updates current/total count
- `"Collected 42 unique listing URLs."` → Sets total count

### 4. **Real-Time Log Output**

#### Color-Coded Messages
- **Blue** - Info messages (commands, status updates)
- **Black** - Standard output
- **Orange** - Warnings, debug messages, captcha notifications
- **Red** - Error messages
- **Green** - Success messages

#### Features
- Auto-scrolls to show latest messages
- Scrollable text area (20 lines visible)
- Thread-safe updates via queue
- Non-blocking I/O using `select` module

### 5. **Technical Implementation**

#### Thread Safety
- Scraping runs in background daemon thread
- Log updates use `queue.Queue` for thread-safe communication
- UI updates scheduled via `root.after()` to avoid race conditions

#### Non-Blocking I/O
- Uses `select.select()` for efficient stream reading
- Sets stdout/stderr to non-blocking mode with `fcntl`
- Polls every 0.1 seconds for new output
- Reads remaining output when process completes

#### Process Management
- Subprocess started with `Popen` for full control
- Captures both stdout and stderr separately
- Graceful termination with `terminate()`, force-kill with `kill()` after timeout
- Working directory set to script's parent directory

## How It Works

1. **User configures options** via checkboxes and text inputs
2. **Start button clicked** → Validates inputs, builds command, disables UI controls
3. **Background thread spawned** → Runs subprocess, captures output
4. **Output parsing**:
   - stdout → Logged as-is
   - stderr → Parsed for progress info, classified by content, color-coded
5. **Progress updates** → Extracted from stderr messages, updates bar and label
6. **Process completion** → Checks exit code, displays success/failure, re-enables controls

## Command Building

The GUI automatically constructs the full command line:

```bash
python3 scrape_fab_metadata.py \
  [--headless] \
  [--clear-cache] \
  [--test-scroll] \
  [--skip-library-scrape] \
  [--skip-on-captcha] \
  [--force-rescrape] \
  [--new-browser-per-page] \
  --max-scrolls 50 \
  --scroll-step 1200 \
  --scroll-steps 8 \
  --out fab_metadata.json \
  --use-url-file fab_library_urls.json
```

The full command is logged at the start for transparency.

## User Experience Improvements

### Before (Command Line)
```bash
# Hard to remember all flags
python scrape_fab_metadata.py --headless --max-scrolls 50 --scroll-step 1200 ...

# No progress visibility
# Must wait blindly or tail stderr
# Easy to make typos in arguments
```

### After (GUI)
- ✓ Visual checkboxes for all options
- ✓ Real-time progress bar showing X/Y pages
- ✓ Color-coded log output
- ✓ File browser dialogs
- ✓ Stop button to cancel
- ✓ Status indicator at a glance
- ✓ No typing required
- ✓ Input validation (numeric checks)

## Future Enhancement Ideas

- [ ] Save/load configuration presets
- [ ] Export log to file
- [ ] Pause/resume functionality
- [ ] Dark mode theme
- [ ] System tray notifications on completion
- [ ] Estimate time remaining based on scraping rate
- [ ] URL list preview before scraping
- [ ] Retry failed pages automatically
