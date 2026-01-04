# Game Asset Tracker - Desktop App

Tauri 2.0 macOS application for configuring and running the ingestion pipeline.

## Requirements

- Node.js 18+
- Rust (latest stable)
- Python 3.11+ with uv

## Development

```bash
npm install
npm run tauri dev
```

## Build

```bash
npm run tauri build
```

## Features

- Configure filesystem ingestion (folder, pack name, tags, license)
- Real-time log streaming during ingestion
- View generated manifest summaries
- Persistent settings for ingestion paths

## Architecture

- **Frontend**: React 18 + TypeScript
- **Backend**: Rust (Tauri 2.0)
- **Ingestion**: Spawns `uv run ingest` subprocess
- **Plugins**: tauri-plugin-shell (subprocess), tauri-plugin-dialog (file picker)
