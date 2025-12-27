# Scripts

This directory contains utility scripts for managing the game-asset-tracker-ingestion project.

## Available Scripts

### `switch-deps.sh`

Switch between local and GitHub dependencies for development vs. distribution.

**Usage:**
```bash
# Switch to local path dependencies (default for development)
./scripts/switch-deps.sh local

# Switch to GitHub dependencies (for CI/CD or external contributors)
./scripts/switch-deps.sh github
```

**What it does:**
- Reads version configuration from `[tool.dependency-versions]` in `pyproject.toml`
- Updates `[tool.uv.sources]` section with appropriate dependency sources
- Runs `uv sync` to update the environment

**When to use:**
- **Local mode**: Active development across multiple repos (editable installs)
- **GitHub mode**: Default for distribution, CI/CD, or working without local repo clones

---

### `prepare-release.sh`

Automated release preparation workflow that ensures GitHub dependencies are properly configured before tagging.

**Usage:**
```bash
./scripts/prepare-release.sh <version>

# Example
./scripts/prepare-release.sh v0.2.0
```

**What it does:**
1. Validates version format (vX.Y.Z)
2. Ensures GitHub dependencies are configured (default)
3. Runs full test suite to validate
4. Commits any pending changes
5. Creates an annotated git tag

**When to use:**
- Before creating a new release
- Ensures tagged commits always use GitHub dependencies
- Automates the release preparation process

**After running:**
```bash
git push origin master
git push origin v0.2.0
```

---

## Workflow Overview

### Day-to-day Development
- Switch to **local mode** for multi-repo development: `./scripts/switch-deps.sh local`
- Work across multiple repos simultaneously
- Changes are immediately reflected via editable installs
- Commit to git keeps GitHub dependencies (don't commit local paths)

### Preparing a Release
1. Ensure all dependency repos are committed and tagged
2. Switch back to GitHub mode if in local: `./scripts/switch-deps.sh github`
3. Run `./scripts/prepare-release.sh v0.2.0`
4. Push the tag: `git push origin v0.2.0`

### CI/CD or External Contributors
- Use GitHub mode (default)
- All dependencies resolve from GitHub at pinned versions
- No local repo clones needed
- Works out-of-the-box with `uv sync`

---

## Version Management

Dependency versions are configured in `pyproject.toml`:

```toml
[tool.dependency-versions]
github-user = "brentlopez"
fab-api-client = "v2.1.0"
uas-api-client = "v2.1.0"
asset-marketplace-client-core = "v0.2.0"
```

To update versions:
1. Edit the `[tool.dependency-versions]` section
2. Run `./scripts/switch-deps.sh github` to apply changes
3. Test thoroughly before releasing

---

## Troubleshooting

**"Config file not found" error:**
- Ensure you're running from the project root or the script directory

**"Missing required version variables" error:**
- Check that `[tool.dependency-versions]` section exists in `pyproject.toml`
- Verify all required fields are present (github-user, fab-api-client, etc.)

**Tests fail in GitHub mode:**
- This likely indicates incompatibilities between versions
- Update version pins in `[tool.dependency-versions]`
- Or fix compatibility issues in the dependency repos

**Can't switch back to local mode:**
- Manually run: `./scripts/switch-deps.sh local`
- Check that local repos exist at expected paths (`../../fab-api-client`, etc.)

---

For more information, see [DEVELOPMENT.md](../DEVELOPMENT.md).
