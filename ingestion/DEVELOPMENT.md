# Development Guide

This document provides guidance for developing the `game-asset-tracker-ingestion` package.

## Table of Contents

- [Dependencies](#dependencies)
- [Local vs GitHub Dependencies](#local-vs-github-dependencies)
- [Setup](#setup)
- [Testing](#testing)
- [Dependency Tree](#dependency-tree)

---

## Dependencies

This project has both external and internal dependencies:

**External dependencies** (from PyPI):
- `jsonschema` - JSON schema validation
- `mutagen` - Audio metadata extraction

**Internal dependencies** (marketplace client libraries):
- `fab-api-client` - Fab marketplace API client
- `uas-api-client` - Unity Asset Store API client
- `asset-marketplace-client-core` - Shared base classes for marketplace clients

The internal dependencies can be sourced from either **local paths** (development) or **GitHub** (CI/CD, external contributors).

---

## Local vs GitHub Dependencies

### Default: GitHub Dependencies

By default, this project is configured to use **GitHub dependencies** with pinned versions. This ensures the project works out-of-the-box for all users without requiring local repository clones.

**Configuration** (in `pyproject.toml`):
```toml
[tool.uv.sources]
# GitHub dependencies (default for distribution)
fab-api-client = { git = "https://github.com/brentlopez/fab-api-client.git", tag = "v2.1.0" }
uas-api-client = { git = "https://github.com/brentlopez/uas-api-client.git", tag = "v2.1.0" }
asset-marketplace-client-core = { git = "https://github.com/brentlopez/asset-marketplace-client-core.git", tag = "v0.2.0" }
```

### Switching to Local Dependencies

For active development across multiple repositories, you can switch to local path dependencies. This allows you to work on multiple related packages simultaneously with immediate changes reflected via editable installs.

**Project structure expected:**
```
Projects/
├── game-asset-tracker/
│   └── ingestion/          # This project
├── fab-api-client/          # Local dependency
├── uas-api-client/          # Local dependency
└── asset-marketplace-client-core/  # Local dependency (transitive)
```

**Option 1: Use the helper script**
```bash
# Switch to local dependencies (for development)
./scripts/switch-deps.sh local

# Switch back to GitHub dependencies (default)
./scripts/switch-deps.sh github
```

**Option 2: Manual configuration**

Edit `pyproject.toml` and replace the `[tool.uv.sources]` section:
```toml
[tool.uv.sources]
# Local path dependencies (for development)
fab-api-client = { path = "../../fab-api-client", editable = true }
uas-api-client = { path = "../../uas-api-client", editable = true }
asset-marketplace-client-core = { path = "../../asset-marketplace-client-core", editable = true }
```

Then run:
```bash
uv sync
```

**Note on versions:** The helper script uses pinned version tags (e.g., `v2.1.0`) for GitHub dependencies to ensure stability. Version tags are defined in `pyproject.toml` under `[tool.dependency-versions]`. To update to newer versions:

1. Check latest releases on GitHub
2. Edit the `[tool.dependency-versions]` section in `pyproject.toml` and update version tags
3. Run `./scripts/switch-deps.sh github` to apply changes

Example version configuration in `pyproject.toml`:
```toml
[tool.dependency-versions]
github-user = "brentlopez"
fab-api-client = "v2.1.0"
uas-api-client = "v2.1.0"
asset-marketplace-client-core = "v0.2.0"
```

Alternatively, use `rev` instead of `tag` to pin to a specific commit:
```toml
uas-api-client = { git = "https://github.com/brentlopez/uas-api-client.git", rev = "abc1234" }
```

---

## Setup

### Local Development Setup

1. **Clone all required repositories:**
   ```bash
   cd ~/Projects
   git clone https://github.com/brentlopez/game-asset-tracker.git
   git clone https://github.com/brentlopez/fab-api-client.git
   git clone https://github.com/brentlopez/uas-api-client.git
   git clone https://github.com/brentlopez/asset-marketplace-client-core.git
   ```

2. **Install dependencies:**
   ```bash
   cd game-asset-tracker/ingestion
   uv sync --all-extras
   ```

3. **Verify installation:**
   ```bash
   uv run python -c "from game_asset_tracker_ingestion import SourceRegistry; print(SourceRegistry.list_sources())"
   ```

### CI/CD Setup

For automated testing environments without local repositories:

1. **Switch to GitHub dependencies:**
   ```bash
   ./scripts/switch-deps.sh github
   ```

2. **Install and test:**
   ```bash
   uv sync --all-extras
   uv run pytest
   ```

### External Contributor Setup

If you don't have access to all internal repositories:

1. **Use GitHub dependencies:**
   ```bash
   ./scripts/switch-deps.sh github
   ```

2. **Install with specific extras:**
   ```bash
   # For Fab development only
   uv sync --extra fab
   
   # For UAS development only
   uv sync --extra uas
   
   # For all marketplace platforms
   uv sync --all-extras
   ```

---

## Testing

### Run All Tests
```bash
uv run pytest
```

### Run Specific Platform Tests
```bash
# Test Fab platform
uv run pytest tests/test_fab_platform.py -v

# Test UAS platform
uv run pytest tests/test_uas_platform.py -v

# Test filesystem platform
uv run pytest tests/test_filesystem_source.py -v
```

### Run with Coverage
```bash
uv run pytest --cov=game_asset_tracker_ingestion --cov-report=html
open htmlcov/index.html
```

### Type Checking
```bash
uv run mypy src/
```

### Linting
```bash
uv run ruff check src/ tests/
```

---

## Dependency Tree

### Internal Dependencies

```
game-asset-tracker-ingestion (this project)
├── fab-api-client (optional, --extra fab)
│   └── asset-marketplace-client-core
│       └── requests
├── uas-api-client (optional, --extra uas)
│   └── asset-marketplace-client-core
│       └── requests
└── (core dependencies)
    ├── jsonschema
    └── mutagen
```

### Dependency Details

| Package | Type | Purpose | Source |
|---------|------|---------|--------|
| `fab-api-client` | Internal | Fab marketplace API client | Local / GitHub |
| `uas-api-client` | Internal | Unity Asset Store API client | Local / GitHub |
| `asset-marketplace-client-core` | Internal | Base classes for marketplace clients | Local / GitHub |
| `jsonschema` | External | JSON schema validation | PyPI |
| `mutagen` | External | Audio file metadata | PyPI |
| `requests` | External | HTTP client (transitive via api-clients) | PyPI |

---

## Development Workflow

### Making Changes to Multiple Packages

When developing features that span multiple packages:

1. **Ensure local dependencies are active:**
   ```bash
   ./scripts/switch-deps.sh local
   ```

2. **Make changes in dependency packages:**
   ```bash
   cd ../uas-api-client
   # Make changes...
   
   cd ../asset-marketplace-client-core
   # Make changes...
   ```

3. **Changes are immediately reflected** (editable installs)

4. **Test your changes:**
   ```bash
   cd ../game-asset-tracker/ingestion
   uv run pytest
   ```

### Publishing Workflow

**Automated Release Preparation:**

Use the `prepare-release.sh` script for an automated workflow:

```bash
./scripts/prepare-release.sh v0.2.0
```

This script will:
1. Switch dependencies to GitHub mode
2. Run the full test suite to validate
3. Commit the GitHub dependency configuration
4. Create an annotated git tag
5. Switch back to local mode for development

Then push the release:
```bash
git push origin master
git push origin v0.2.0
```

**Manual Publishing Workflow:**

If you prefer manual control:

1. **Commit and push all dependency changes first:**
   ```bash
   cd ../asset-marketplace-client-core
   git add . && git commit -m "..." && git push
   
   cd ../uas-api-client
   git add . && git commit -m "..." && git push
   ```

2. **Switch to GitHub dependencies and test:**
   ```bash
   cd ../game-asset-tracker/ingestion
   ./scripts/switch-deps.sh github
   uv sync --all-extras
   uv run pytest
   ```

3. **Commit, tag, and push:**
   ```bash
   git add pyproject.toml
   git commit -m "chore: prepare release v0.2.0 - switch to GitHub dependencies"
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin master
   git push origin v0.2.0
   ```

4. **Switch back to local for continued development:**
   ```bash
   ./scripts/switch-deps.sh local
   ```

---

## Troubleshooting

### "Package not found" errors

If you see errors like `Package 'uas-api-client' not found`:

1. Check that local repositories exist:
   ```bash
   ls ../../uas-api-client
   ls ../../fab-api-client
   ls ../../asset-marketplace-client-core
   ```

2. If missing, either:
   - Clone the repositories (see Setup)
   - Switch to GitHub dependencies: `./scripts/switch-deps.sh github`

### "Import failed" when testing platforms

If platform imports fail during tests:

1. Ensure extras are installed:
   ```bash
   uv sync --all-extras
   ```

2. Check that dependencies resolved correctly:
   ```bash
   uv pip list | grep -E "(fab|uas|asset-marketplace)"
   ```

### Transitive dependency conflicts

If you encounter dependency resolution errors:

1. Check that all internal packages have compatible versions of `asset-marketplace-client-core`
2. Update dependencies:
   ```bash
   cd ../asset-marketplace-client-core
   git pull
   
   cd ../fab-api-client
   git pull
   uv sync
   
   cd ../uas-api-client
   git pull
   uv sync
   
   cd ../game-asset-tracker/ingestion
   uv sync --all-extras
   ```

---

## Additional Resources

- [uv documentation](https://docs.astral.sh/uv/)
- [asset-marketplace-client-core](https://github.com/brentlopez/asset-marketplace-client-core) - Architecture documentation
- [fab-api-client](https://github.com/brentlopez/fab-api-client) - Fab API client
- [uas-api-client](https://github.com/brentlopez/uas-api-client) - Unity Asset Store API client
