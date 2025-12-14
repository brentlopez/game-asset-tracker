# Game Asset Tracker - Obsidian Plugin

This Obsidian plugin provides asset tracking functionality using SQLite and React.

## Features

- **SQLite Database**: Fast, embedded database for searching thousands of asset files
- **React Dashboard**: Modern UI for importing manifests and viewing statistics
- **Automatic Markdown Generation**: Creates organized notes for each Asset Pack
- **Dual Storage**: SQLite for search, Markdown for human organization

## Setup

### Install Dependencies

```bash
npm install
```

### Development Build

Build and watch for changes:

```bash
npm run dev
```

### Production Build

Build for production:

```bash
npm run build
```

## Installation in Obsidian

1. Build the plugin (see above)
2. Copy the following files to your vault's plugins folder:
   - `main.js`
   - `manifest.json`
   - `styles.css` (if present)
   
   Example:
   ```
   YourVault/.obsidian/plugins/game-asset-tracker/
   ```

3. Enable the plugin in Obsidian Settings → Community Plugins

## Usage

### Opening the Dashboard

- Click the database icon in the left ribbon
- Or use the command palette: "Asset Tracker: Open Dashboard"

### Importing a Manifest

1. Generate a JSON manifest using the Python ingestion script
2. In the dashboard, click "Choose Manifest File"
3. Select your JSON file
4. The plugin will:
   - Import all data into SQLite
   - Create a Markdown note in "Asset Packs" folder
   - Display import statistics

### Testing the Database

Click "Run Test Query" in the dashboard to verify the database is working correctly.

## Architecture

```
src/
├── main.ts              # Plugin entry point, handles lifecycle
├── database.ts          # DatabaseManager with sql.js integration
├── DashboardView.tsx    # React dashboard component
├── types.ts             # TypeScript interfaces for JSON schema
└── utils.ts             # Markdown generation utilities
```

### Key Components

**DatabaseManager** (`database.ts`)
- Initializes sql.js with WASM
- Persists database to `data.db` in plugin directory
- Implements schema from ARCHITECTURE.md
- Provides import and query methods

**DashboardView** (`DashboardView.tsx`)
- React-based UI using Obsidian's ItemView
- File picker for JSON manifest import
- Statistics display (pack count, asset count)
- Test query interface

**Main Plugin** (`main.ts`)
- Registers views and commands
- Coordinates database and markdown operations
- Implements the dual-action import: SQL + Markdown

## Configuration

Settings can be configured in the plugin settings:

- `dbPath`: Location of SQLite database file (default: `.obsidian/plugins/game-asset-tracker/data.db`)
- `notesFolder`: Folder for Asset Pack notes (default: `Asset Packs`)

## Data Flow

```
JSON Manifest (from Python script)
    ↓
importManifest()
    ↓
    ├─→ DatabaseManager.importManifest()
    │      → SQLite tables updated
    │      → data.db saved to disk
    │
    └─→ createPackNote()
           → Markdown note generated
           → File created/updated in vault
```

## Troubleshooting

### Database not initializing

- Check console for errors
- Ensure sql.js WASM file is accessible
- Try deleting `data.db` and reloading plugin

### Import fails

- Validate JSON against schema in ARCHITECTURE.md
- Check console for detailed error messages
- Ensure all required fields are present

### Dashboard not opening

- Check that the view is registered correctly
- Try reloading Obsidian
- Check for conflicting plugins

## Development Notes

### sql.js Integration

The plugin uses sql.js (WASM SQLite) with manual persistence:
- Database is loaded from `data.db` on startup
- Changes are saved after each import
- Binary format allows efficient storage

### React in Obsidian

- Uses `react-dom/client` with `createRoot`
- Styled using Obsidian CSS variables
- Bundled with esbuild

### Schema Validation

Basic validation is performed on import. For strict validation, consider adding JSON Schema validation.

## Future Enhancements

- [ ] Advanced search interface in dashboard
- [ ] Asset preview generation
- [ ] Code block processor for `asset-tracker-view`
- [ ] Settings UI for configuration
- [ ] Export functionality
- [ ] Batch import support

## Related Files

- `/ARCHITECTURE.md` - System architecture and data model
- `/schemas/` - JSON schema reference
- `/ingestion-scripts/` - Python scripts for generating manifests
