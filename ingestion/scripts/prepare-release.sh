#!/usr/bin/env bash
# Prepare for Release - Automated release workflow
# This script ensures GitHub dependencies are properly set before tagging a release
#
# Usage: ./scripts/prepare-release.sh <version>
# Example: ./scripts/prepare-release.sh v0.2.0

set -e

VERSION="${1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

step() {
    echo -e "${BLUE}==> $1${NC}"
}

# Validate version argument
if [[ -z "$VERSION" ]]; then
    error "Version argument required. Usage: $0 <version>"
fi

# Validate version format (vX.Y.Z)
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Invalid version format. Expected: vX.Y.Z (e.g., v0.2.0)"
fi

cd "$PROJECT_ROOT"

# Check if git working directory is clean
if [[ -n $(git status --porcelain) ]]; then
    warn "Git working directory is not clean. Uncommitted changes:"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Aborted by user"
    fi
fi

echo ""
info "╔════════════════════════════════════════════════════════════╗"
info "║          Prepare Release: $VERSION                      "
info "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Ensure we're using GitHub dependencies (should be default)
step "Step 1: Ensuring GitHub dependencies are configured"

# Check current dependency mode
if grep -q 'path.*=.*"\.\./' pyproject.toml; then
    warn "Currently using local dependencies, switching to GitHub..."
    ./scripts/switch-deps.sh github
    
    if [[ $? -ne 0 ]]; then
        error "Failed to switch to GitHub dependencies"
    fi
else
    info "✓ Already using GitHub dependencies"
fi

echo ""

# Step 2: Run tests to validate everything works
step "Step 2: Running tests with GitHub dependencies"
warn "Running full test suite..."

if ! uv run pytest tests/ -q; then
    error "Tests failed. Fix issues before releasing."
fi

info "✓ All tests passed"
echo ""

# Step 3: Commit any changes if needed
step "Step 3: Committing changes (if any)"

if git diff --quiet && git diff --cached --quiet; then
    info "No changes to commit"
else
    git add -A
    git commit -m "chore: prepare release $VERSION

- Ready for release
- All dependencies use GitHub sources
- Automated by scripts/prepare-release.sh"
    
    info "✓ Committed changes"
fi

echo ""

# Step 4: Create git tag
step "Step 4: Creating git tag: $VERSION"

if git rev-parse "$VERSION" >/dev/null 2>&1; then
    warn "Tag $VERSION already exists"
    read -p "Delete and recreate tag? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$VERSION"
        info "✓ Deleted existing tag"
    else
        error "Aborted - tag already exists"
    fi
fi

git tag -a "$VERSION" -m "Release $VERSION

This release uses GitHub dependencies for all internal packages.
See CHANGELOG.md for details."

info "✓ Created tag: $VERSION"
echo ""

echo ""
info "╭────────────────────────────────────────────────────────────╮"
info "│                  Release Prepared!                          │"
info "╰────────────────────────────────────────────────────────────╯"
echo ""
info "Tag created: $VERSION"
info "To push the release:"
echo ""
echo "  git push origin master"
echo "  git push origin $VERSION"
echo ""
info "Note: Repository uses GitHub dependencies by default"
info "      Run ./scripts/switch-deps.sh local for local development"
