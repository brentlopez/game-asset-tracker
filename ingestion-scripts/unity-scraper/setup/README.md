# Setup & Authentication

This directory contains scripts and files for authenticating with the Unity Asset Store.

## Files in this Directory

- **`auth.json`** - Playwright storage state containing authentication cookies (gitignored)
- **`generate_unity_auth.py`** - Interactive script to log in and save auth state

## Quick Start

### Generate Authentication

Run the authentication generator:

```bash
cd setup
python3 generate_unity_auth.py
```

This will:
1. Launch a browser window
2. Navigate to Unity Asset Store "My Assets" page
3. Wait for you to log in manually
4. Save your authenticated session to `auth.json`
5. Close when you close the browser window

### Alternative: Playwright Codegen

You can also use Playwright's built-in codegen tool:

```bash
cd setup
python3 -m playwright codegen --save-storage=auth.json https://assetstore.unity.com/account/assets
```

1. Log in manually in the opened browser
2. Once on your "My Assets" page, close the browser
3. Your session will be saved to `auth.json`

## Troubleshooting

### auth.json not working

- Cookies may expire - regenerate `auth.json` if you get auth errors
- Make sure you're fully logged in before closing the browser
- Ensure the file is in JSON format with a `cookies` array

### Browser doesn't open

- Make sure Playwright is installed: `python3 -m playwright install`
- Check Python version (3.7+ required)

### File not found errors

Make sure you're in the `setup/` directory when running the scripts, or use full paths from the project root.
