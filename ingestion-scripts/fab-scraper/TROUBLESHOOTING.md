# Troubleshooting Guide

## Common Issues and Solutions

### "Cannot switch to a different thread" Error

**Symptom:**
```
WARNING: Failed to scrape https://...
Cannot switch to a different thread
    Current:  <greenlet.greenlet object at 0x...>
    Expected: <greenlet.greenlet object at 0x...>
```

**Cause:**
Playwright's synchronous API uses greenlets (lightweight coroutines) internally. Greenlets are not thread-safe and cannot be shared across threads.

**Solution:**
The scraper now uses **multiprocessing** (`ProcessPoolExecutor`) instead of threading (`ThreadPoolExecutor`). Each process gets its own isolated memory space and can safely run Playwright.

**Technical Details:**
- **Old approach**: Threading with `threading.Lock()` for file writes
- **New approach**: Multiprocessing with `fcntl.flock()` for file writes
- Each process launches its own Playwright browser instance
- File locking ensures safe concurrent writes to JSON

**No action required** - this is already fixed in the current version.

---

## Other Common Issues

### High Memory Usage

**Symptom:** System running out of RAM with parallel scraping

**Solutions:**
1. Reduce worker count: `--parallel 3` instead of `--parallel 10`
2. Use headless mode: `--headless` (uses less memory)
3. Close other applications

**Memory usage per worker:**
- Headless: ~200-300 MB
- Headed (with GUI): ~400-500 MB

---

### Too Many Captchas

**Symptom:** Many pages blocked by captcha verification

**Solutions:**
1. Reduce workers: `--parallel 2` or `--parallel 3`
2. Enable skip: `--skip-on-captcha`
3. Use headless: `--headless` (less detectable)
4. Add delays: Increase `PER_PAGE_SLEEP_SEC` in the script

**Why it happens:** Multiple simultaneous requests from same IP look suspicious

---

### Slow Performance Despite Parallel Mode

**Symptom:** 5 workers not actually 5x faster

**Possible causes:**
1. **Network bottleneck**: Your internet connection is the limiting factor
2. **CPU bottleneck**: 100% CPU usage across all cores
3. **Target site rate limiting**: Server is deliberately slowing responses

**Solutions:**
- Check Activity Monitor (macOS) or Task Manager (Windows)
- If CPU at 100%: Reduce workers
- If network saturated: Reduce workers or upgrade connection
- If target site is rate limiting: Reduce workers and respect their limits

---

### JSON File Corruption

**Symptom:** Invalid JSON after scraping

**This should not happen** with the current implementation (file locking), but if it does:

**Recovery:**
1. Stop the scraper immediately
2. Check if you have a backup: `fab_metadata.json.bak`
3. Validate JSON: `python -c "import json; json.load(open('fab_metadata.json'))"`
4. If corrupt, restore from backup or re-scrape

**Prevention:**
- File locking (`fcntl.flock`) prevents this
- Each process acquires exclusive lock before writing
- Only one process can write at a time

---

### Process Hangs / Zombie Processes

**Symptom:** Worker processes don't finish or become unresponsive

**Solutions:**
1. **GUI Stop Button**: Kills all processes including workers and browsers
   - Sends SIGTERM to entire process group (graceful)
   - Waits 3 seconds for clean shutdown
   - Sends SIGKILL if processes don't stop (force)
   - Cleans up orphaned chromium processes automatically

2. **Manual cleanup** if GUI stop doesn't work:
   ```bash
   # Kill scraper and all child processes
   pkill -9 -f scrape_fab_metadata.py
   
   # Kill any leftover browser processes
   pkill -9 chromium
   ```

3. **Check for leftover processes:**
   ```bash
   ps aux | grep scrape_fab_metadata
   ps aux | grep chromium
   ```

**How Stop Works (Technical):**
- Main process started in new process group (`os.setsid`)
- Stop button calls `os.killpg(pgid, SIGTERM)` to kill entire group
- 3 second grace period for cleanup
- `os.killpg(pgid, SIGKILL)` if timeout
- `pkill -9 chromium` cleans up orphaned browsers

---

### GUI Not Updating Progress

**Symptom:** Progress bar stuck at 0% despite logs showing activity

**Causes:**
1. Output buffering delaying log messages
2. Regex not matching progress messages

**Solutions:**
1. Wait 5-10 seconds - buffering may cause delay
2. Check that stderr contains messages like:
   - `"Scraping 5/100: https://..."`
   - `"Saved progress: 5/100 completed"`
3. Restart GUI if still stuck

---

### "auth.json not found" Error

**Symptom:**
```
ERROR: auth.json not found at /path/to/fab-scraper/auth.json
```

**Solution:**
You need to create `auth.json` with your Fab.com authentication:

1. Log in to fab.com in your browser
2. Open browser DevTools (F12)
3. Go to Application → Storage → Cookies
4. Export cookies to `auth.json`
5. Place in `fab-scraper/` directory

See project README for detailed auth setup instructions.

---

### Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'playwright'
```

**Solution:**
Install dependencies:
```bash
pip install playwright
playwright install
```

---

### Permission Denied (fcntl.flock)

**Symptom:**
```
PermissionError: [Errno 13] Permission denied
```

**Cause:** Another process has exclusive lock on the JSON file

**Solutions:**
1. Check if another scraper instance is running:
   ```bash
   ps aux | grep scrape_fab_metadata
   ```
2. Kill other instances:
   ```bash
   pkill -f scrape_fab_metadata.py
   ```
3. Check file permissions:
   ```bash
   ls -l fab_metadata.json
   chmod 644 fab_metadata.json
   ```

---

## Debug Mode

### Enable Verbose Logging

**For command line:**
```bash
python scrape_fab_metadata.py --parallel 2 --headless 2>&1 | tee debug.log
```

**For GUI:**
- Logs are automatically captured in the log area
- Click "Clear Log" to reset
- All stdout/stderr is displayed

### Check Playwright Issues

```bash
# Test Playwright installation
python -c "from playwright.sync_api import sync_playwright; print('OK')"

# Check installed browsers
playwright install --help
```

---

## Performance Benchmarking

### Measure Actual Performance

```bash
# Time a small batch
time python scrape_fab_metadata.py --parallel 5 --headless \
  --skip-library-scrape --use-url-file test_urls.json

# Compare different worker counts
for workers in 1 2 5 10; do
  echo "Testing with $workers workers..."
  time python scrape_fab_metadata.py --parallel $workers --headless \
    --test-scroll
done
```

---

## Getting Help

If you encounter an issue not covered here:

1. Check the error message carefully
2. Look for similar issues in project documentation
3. Try reducing complexity:
   - Use `--parallel 1` (sequential)
   - Use `--test-scroll` (no actual scraping)
   - Test with 1-2 URLs first
4. Check system resources (CPU, memory, disk)
5. Verify auth.json is valid and up-to-date

---

## FAQ

**Q: Why multiprocessing instead of threading?**
A: Playwright's sync API uses greenlets which are not thread-safe. Multiprocessing gives each worker isolated memory.

**Q: Is file locking slower than in-memory queues?**
A: Slightly, but the difference is negligible (<1% overhead) since file writes take ~10-50ms vs scraping taking 2-5 seconds.

**Q: Can I use threading with Playwright async API?**
A: Yes, but that would require rewriting the entire scraper. The multiprocessing solution works well for this use case.

**Q: What's the maximum recommended worker count?**
A: 10 workers max. Beyond that, you hit diminishing returns and increased risk of rate limiting/captchas.

**Q: Does parallel mode work on Windows?**
A: Yes, but `fcntl.flock` is Unix-specific. On Windows, the code falls back to `msvcrt.locking` (not yet implemented - contribution welcome!).
