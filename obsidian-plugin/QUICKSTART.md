# Quick Start Guide

Get the Asset Tracker plugin up and running in 5 minutes.

## 1. Install Dependencies

```bash
npm install
```

This installs:
- TypeScript compiler
- React and React DOM
- sql.js (WASM SQLite)
- esbuild (bundler)
- Obsidian type definitions

## 2. Build the Plugin

For development (with file watching):
```bash
npm run dev
```

For production (single build):
```bash
npm run build
```

This creates `main.js` in the root directory.

## 3. Test in Obsidian

### Option A: Symlink (Recommended for Development)

Link the plugin directory to your test vault:

```bash
# Replace with your vault path
ln -s /Users/brentlopez/Projects/game-asset-tracker/obsidian-plugin ~/path/to/vault/.obsidian/plugins/game-asset-tracker
```

### Option B: Copy Files

Copy these files to your vault:
```
YourVault/.obsidian/plugins/game-asset-tracker/
  ├── main.js
  ├── manifest.json
  └── styles.css (if exists)
```

### Enable the Plugin

1. Open Obsidian
2. Go to Settings → Community Plugins
3. Turn off "Restricted Mode" (if needed)
4. Click "Reload" in Community Plugins
5. Enable "Game Asset Tracker"

## 4. Test the Plugin

### Open the Dashboard

- Click the database icon in the left ribbon
- Or press `Cmd/Ctrl+P` and type "Asset Tracker: Open Dashboard"

You should see:
- Total Packs: 0
- Total Assets: 0
- Import Manifest section
- Database Status section

### Test the Database

1. Click "Run Test Query"
2. You should see: `✓ Database query successful: 0 assets in database`

This confirms the database initialized correctly.

### Import the Example Manifest

1. Click "Choose Manifest File"
2. Select `example-manifest.json` from the plugin directory
3. You should see a success notice
4. Dashboard updates to show:
   - Total Packs: 1
   - Total Assets: 3

5. Check your vault:
   - A new folder "Asset Packs" should exist
   - Inside: `example-asset-pack.md`

### Verify the Markdown Note

Open `Asset Packs/example-asset-pack.md` and you should see:

```markdown
---
pack_id: 550e8400-e29b-41d4-a716-446655440000
source: Test Source
tags: [example, test, 3d-models]
---

# Example Asset Pack

**Root Path:** `/path/to/assets/example-pack`

## Overview

**License:** [View License](https://example.com/license)
**Total Assets:** 3

## Asset Breakdown

- fbx: 1
- png: 1
- wav: 1

## Asset View

\`\`\`asset-tracker-view
pack_id: 550e8400-e29b-41d4-a716-446655440000
\`\`\`
```

### Verify the Database

1. Click "Run Test Query" again
2. Should show: `✓ Database query successful: 3 assets in database`

## 5. Check the Data Persistence

1. Close Obsidian
2. Reopen Obsidian
3. Open the Asset Tracker Dashboard
4. Click "Run Test Query"

Should still show 3 assets! This proves the database persists to disk correctly.

## Troubleshooting

### "Database not initialized" error

Check the developer console (View → Toggle Developer Tools):
- Look for sql.js WASM loading errors
- Ensure internet connection (WASM loaded from CDN)

### Import fails

- Validate your JSON matches the schema
- Required fields: `pack_id`, `pack_name`, `root_path`, `source`, `assets`
- Each asset needs: `relative_path`, `file_type`, `size_bytes`

### Dashboard won't open

- Reload the plugin: Settings → Community Plugins → Reload
- Check for JavaScript errors in console
- Try disabling/re-enabling the plugin

## Next Steps

### Create Your Own Manifest

Use the Python ingestion script (coming soon) to generate manifests from your actual asset directories.

### Explore the Code

- `src/main.ts` - Plugin entry point
- `src/database.ts` - SQLite operations
- `src/DashboardView.tsx` - React UI
- `src/utils.ts` - Markdown generation

### Customize

- Change the notes folder: Edit `DEFAULT_SETTINGS` in `src/main.ts`
- Modify the note template: Edit functions in `src/utils.ts`
- Add new dashboard features: Modify `src/DashboardView.tsx`

## Development Tips

### Watch Mode

Keep `npm run dev` running while developing. Changes rebuild automatically.

### Reload in Obsidian

After rebuilding:
1. Open Command Palette (`Cmd/Ctrl+P`)
2. Type "Reload app without saving"
3. Or: Settings → Community Plugins → Reload

### Check Logs

Always keep the Developer Console open:
- View → Toggle Developer Tools
- Look for `Asset Tracker:` prefixed logs

### Database Location

The database is stored at:
```
YourVault/.obsidian/plugins/game-asset-tracker/data.db
```

You can delete this file to reset the database.

## Success Checklist

- [x] Dependencies installed
- [x] Plugin builds without errors
- [x] Dashboard opens in Obsidian
- [x] Test query returns success
- [x] Example manifest imports successfully
- [x] Markdown note is created
- [x] Database persists after restart

You're ready to build! 🚀
