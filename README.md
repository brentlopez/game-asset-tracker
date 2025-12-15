# Game Asset Tracking System

A hybrid system for managing game development assets at scale, combining Obsidian for high-level organization with SQLite for granular file-level search.

## Overview

Manage thousands of game assets (3D models, textures, audio, animations) from Unity Asset Store, Epic Marketplace, or your local NAS with a powerful hybrid approach:

- **📝 Obsidian** - High-level Asset Pack organization with linking and tagging
- **🔍 SQLite** - Fast, granular search across individual asset files
- **🐍 Python Scripts** - Automated ingestion from your asset directories
- **🔄 JSON-Based Workflow** - Portable, auditable data exchange

## Quick Start

### Prerequisites

- Python 3.x
- Node.js and npm (for plugin development)
- Obsidian (for using the plugin)

### Repository Structure

```
game-asset-tracker/
├── ARCHITECTURE.md          # 📘 Complete system design (READ THIS FIRST)
├── README.md                # This file
├── .gitignore
│
├── ingestion/               # Python scripts for scanning assets
│   └── (to be developed)
│
├── obsidian-plugin/        # TypeScript plugin for Obsidian
│   └── (to be developed)
│
└── schemas/                # Reference schemas and examples
    └── (to be developed)
```

## How It Works

```
1. Run Python script on your asset folders
           ↓
2. Script generates JSON manifest
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
- Scan local directories or NAS
- Extract metadata (dimensions, duration, file size)
- Auto-generate tags from folder structure
- Support for Unity, Epic, custom sources

### 📋 Strict Schema
All data flows through a well-defined JSON schema ensuring consistency and portability.

## Use Cases

- **Asset Library Management** - Track your growing collection of purchased or created assets
- **Project Asset Audits** - Find which packs contain specific file types or tags
- **License Tracking** - Keep license info attached to each pack
- **Cross-Project Reuse** - Link Asset Packs to multiple game projects in Obsidian

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system design, workflow, and data model (**start here**)
- **ingestion/README.md** - Guide for ingestion systems (filesystem scanning and marketplace scraping)
- **obsidian-plugin/README.md** - Plugin installation and usage (to be developed)
- **schemas/** - Reference schemas and examples (to be developed)

## Development Status

🚧 **Project Scaffolded** - Core architecture defined, ready for development.

### Next Steps

1. Implement Python ingestion script
2. Develop Obsidian plugin with SQLite integration
3. Create JSON Schema validation
4. Add example manifests and test data

## Contributing

This is a personal project, but contributions are welcome! Please refer to `ARCHITECTURE.md` for design constraints and the strict JSON schema.

## License

(Add your license here)

## Contact

(Add your contact information here)
