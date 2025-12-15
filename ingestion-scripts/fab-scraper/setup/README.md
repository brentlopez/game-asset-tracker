# Setup & Authentication

This directory contains scripts and files for authenticating with Fab.com and collecting URLs for scraping.

## Files in this Directory

- **`auth.json`** - Playwright storage state containing authentication cookies (gitignored)
- **`generate_fab_auth.py`** - Interactive script to log in and save auth state
- **`convert_cookies.py`** - Alternative: Convert manually-copied cookies to auth.json
- **`extract_urls_console.js`** - Browser console script to extract listing URLs
- **`fab_library_urls.json`** - Collection of listing URLs from the library page

## Quick Start

### Method 1: Automated Login (Recommended)

Use `generate_fab_auth.py` to log in interactively and automatically save your session:

```bash
cd setup
python3 generate_fab_auth.py
```

This will:
1. Launch a browser window
2. Navigate to Fab.com library (redirects to Epic Games login)
3. Wait for you to log in manually
4. Save your authenticated session to `auth.json`
5. Close when you close the browser window

**Note**: The script uses stealth techniques to avoid captcha issues during login.

### Method 2: Manual Cookie Export

If you prefer to manually extract cookies from your browser:

1. Log in to https://www.fab.com in your browser
2. Open DevTools (F12)
3. Go to **Application → Cookies → https://www.fab.com**
4. Copy the entire cookie string
5. Paste it into `convert_cookies.py` (replace the `RAW_COOKIE_STRING` value)
6. Run the script:

```bash
cd setup
python3 convert_cookies.py
```

This will generate `auth.json` from your cookies.

## Collecting Library URLs

If you want to pre-collect all listing URLs before scraping (useful for resuming or parallelization):

1. Log in to https://www.fab.com/library in your browser
2. Scroll to load all your library items
3. Open browser console (F12 → Console tab)
4. Paste and run the contents of `extract_urls_console.js`
5. Copy the JSON array output
6. Save it to `fab_library_urls.json`

You can then use `--skip-library-scrape` flag when scraping to use this pre-collected URL list.

## Troubleshooting

### auth.json not working

- Make sure you're logged in to Fab.com before running scripts
- Cookies may expire - regenerate `auth.json` if you get auth errors
- Ensure the file is in JSON format with a `cookies` array

### Captcha during login

- The `generate_fab_auth.py` script includes anti-detection features
- If captchas persist, try Method 2 (manual cookie export)
- Use a different browser or clear cookies/cache

### File not found errors

Make sure you're in the `setup/` directory when running the scripts, or use full paths from the project root.
