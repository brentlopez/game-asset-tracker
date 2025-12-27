# Game Asset Tracking System

A hybrid system for managing game development assets at scale, combining Obsidian for high-level organization with SQLite for granular file-level search.

## Overview

Manage thousands of game assets (3D models, textures, audio, animations) from Unity Asset Store, Epic Marketplace, or your local NAS with a powerful hybrid approach:

- **📝 Obsidian** - High-level Asset Pack organization with linking and tagging
- **🔍 SQLite** - Fast, granular search across individual asset files
- **🐍 Python Library** - Automated manifest generation from multiple sources
- **🔄 JSON-Based Workflow** - Portable, auditable data exchange

## Current Status

🚀 **Ingestion Library**: ✅ Implemented and ready to use  
🚧 **Obsidian Plugin**: Scaffolded, awaiting development

## Quick Start

### Prerequisites

- Python 3.11+ with uv package manager
- Node.js and npm (for plugin development)
- Obsidian (for using the plugin)

### Repository Structure

```
game-asset-tracker/
├── ARCHITECTURE.md          # 📘 Complete system design (READ THIS FIRST)
├── README.md                # This file
├── WARP.md                  # AI assistant guide
│
├── ingestion/               # ✅ Python ingestion library (IMPLEMENTED)
│   ├── src/                 # Multi-source ingestion pipeline
│   ├── examples/            # Runnable example scripts
│   ├── EXTENDING.md         # Guide for implementing custom sources
│   ├── TODO.md              # Planned enhancements
│   └── README.md            # Library documentation
│
├── obsidian-plugin/        # 🚧 TypeScript plugin for Obsidian
│   └── (to be developed)
│
└── schemas/                # Reference schemas and examples
    ├── manifest.schema.json # JSON Schema (Draft 7)
    ├── example-manifest.json
    └── README.md
```

## How It Works

```
1. Run ingestion library on your sources
           ↓
2. Library generates JSON manifests
           ↓
3. Import JSON via Obsidian plugin
           ↓
4. Plugin creates searchable index + Markdown notes
           ↓
5. Browse packs in Obsidian, search files in plugin
```

## Key Features

### 🎯 Hybrid Organization
- **Asset Packs** as Markdown notes in Obsidian (human-readable, linkable)
- **Asset Files** in SQLite database (fast, searchable, scalable)

### 🔌 Plugin Architecture
- Import JSON manifests with one click
- Automatically updates SQLite index
- Generates formatted Markdown notes
- Search thousands of files instantly

### 🐍 Flexible Ingestion
- Multi-source architecture (filesystem, marketplaces, custom)
- Scan local directories or NAS
- Integrate with Fab marketplace, Unity Asset Store
- Extract metadata (dimensions, duration, file size)
- Auto-generate tags from folder structure
- Extensible via `Source` interface - add your own sources

### 📋 Strict Schema
All data flows through a well-defined JSON schema ensuring consistency and portability.

## Use Cases

- **Asset Library Management** - Track your growing collection of purchased or created assets
- **Project Asset Audits** - Find which packs contain specific file types or tags
- **License Tracking** - Keep license info attached to each pack
- **Cross-Project Reuse** - Link Asset Packs to multiple game projects in Obsidian

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system design, workflow, and data model (**start here**)
- **[ingestion/README.md](ingestion/README.md)** - Library usage, installation, CLI reference
- **[ingestion/EXTENDING.md](ingestion/EXTENDING.md)** - Guide for implementing custom sources
- **[ingestion/TODO.md](ingestion/TODO.md)** - Planned future enhancements
- **[schemas/](schemas/)** - JSON Schema, examples, and validation guide
- **obsidian-plugin/README.md** - Plugin installation and usage (to be developed)

## Development Status

### ✅ Completed

1. **Python Ingestion Library**
   - Multi-source architecture (filesystem, Fab marketplace)
   - Extensible via `Source` interface
   - Full test coverage and type safety
   - Example scripts and documentation

2. **JSON Schema & Validation**
   - Formal JSON Schema (Draft 7)
   - Example manifests
   - Validation in Python (jsonschema)

### 🚧 Next Steps

1. Develop Obsidian plugin with SQLite integration
2. Implement Unity Asset Store source (see `ingestion/TODO.md`)
3. Add advanced features: filtering, caching, parallel processing

## Contributing

This is a personal project, but contributions are welcome! Please refer to `ARCHITECTURE.md` for design constraints and the strict JSON schema.

## License

(Add your license here)

## Contact

(Add your contact information here)
