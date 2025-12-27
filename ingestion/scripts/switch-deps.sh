#!/usr/bin/env bash
# Script to switch between local and GitHub dependencies
# Usage: ./scripts/switch-deps.sh [local|github]

set -e

MODE="${1:-local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

load_config() {
    if [[ ! -f "$PYPROJECT_FILE" ]]; then
        error "pyproject.toml not found: $PYPROJECT_FILE"
    fi
    
    # Parse TOML from [tool.dependency-versions] section
    # Extract github user
    GITHUB_USER=$(grep -A 10 "\[tool\.dependency-versions\]" "$PYPROJECT_FILE" | grep "^github-user" | head -1 | sed 's/^[^=]*=[[:space:]]*"\([^"]*\)".*/\1/')
    
    # Extract versions from [tool.dependency-versions]
    FAB_API_CLIENT_VERSION=$(grep -A 10 "\[tool\.dependency-versions\]" "$PYPROJECT_FILE" | grep "^fab-api-client" | head -1 | sed 's/^[^=]*=[[:space:]]*"\([^"]*\)".*/\1/')
    UAS_API_CLIENT_VERSION=$(grep -A 10 "\[tool\.dependency-versions\]" "$PYPROJECT_FILE" | grep "^uas-api-client" | head -1 | sed 's/^[^=]*=[[:space:]]*"\([^"]*\)".*/\1/')
    ASSET_MARKETPLACE_CLIENT_CORE_VERSION=$(grep -A 10 "\[tool\.dependency-versions\]" "$PYPROJECT_FILE" | grep "^asset-marketplace-client-core" | head -1 | sed 's/^[^=]*=[[:space:]]*"\([^"]*\)".*/\1/')
    
    # Validate required variables
    if [[ -z "$FAB_API_CLIENT_VERSION" ]] || [[ -z "$UAS_API_CLIENT_VERSION" ]] || [[ -z "$ASSET_MARKETPLACE_CLIENT_CORE_VERSION" ]]; then
        error "Missing required version variables in [tool.dependency-versions] section of pyproject.toml"
    fi
    
    if [[ -z "$GITHUB_USER" ]]; then
        error "Missing github-user in [tool.dependency-versions] section of pyproject.toml"
    fi
}

# Validate mode
if [[ "$MODE" != "local" && "$MODE" != "github" ]]; then
    error "Invalid mode: $MODE. Use 'local' or 'github'"
fi

cd "$PROJECT_ROOT"

if [[ "$MODE" == "local" ]]; then
    info "Switching to LOCAL path dependencies..."
    
    # Check if local dependencies exist
    LOCAL_DEPS=(
        "../../fab-api-client"
        "../../uas-api-client"
        "../../asset-marketplace-client-core"
    )
    
    for dep in "${LOCAL_DEPS[@]}"; do
        if [[ ! -d "$dep" ]]; then
            warn "Warning: Local dependency not found: $dep"
        fi
    done
    
    # Update pyproject.toml with local paths
    info "Updating pyproject.toml..."
    
    # Backup current pyproject.toml
    cp pyproject.toml pyproject.toml.bak
    
    # Create the new [tool.uv.sources] section
    cat > /tmp/uv-sources.toml << 'EOF'
[tool.uv.sources]
# Local path dependencies (default for development)
fab-api-client = { path = "../../fab-api-client", editable = true }
uas-api-client = { path = "../../uas-api-client", editable = true }
asset-marketplace-client-core = { path = "../../asset-marketplace-client-core", editable = true }
EOF
    
    # Remove old [tool.uv.sources] section and append new one
    if grep -q "\[tool\.uv\.sources\]" pyproject.toml; then
        # Remove from [tool.uv.sources] to the end of file or next section
        sed -i'.tmp' '/^\[tool\.uv\.sources\]/,/^\[/{ /^\[tool\.uv\.sources\]/d; /^\[/!d; }' pyproject.toml
    fi
    
    # Append new section
    echo "" >> pyproject.toml
    cat /tmp/uv-sources.toml >> pyproject.toml
    
    # Cleanup
    rm -f /tmp/uv-sources.toml pyproject.toml.tmp
    
    info "✓ Updated pyproject.toml with local paths"
    
    info "Running uv sync..."
    uv sync
    
    info "✓ Switched to local dependencies"
    info "  - fab-api-client: ../../fab-api-client"
    info "  - uas-api-client: ../../uas-api-client"
    info "  - asset-marketplace-client-core: ../../asset-marketplace-client-core"
    
elif [[ "$MODE" == "github" ]]; then
    info "Switching to GITHUB dependencies..."
    
    # Load version configuration
    load_config
    
    info "Using versions from pyproject.toml [tool.dependency-versions]:"
    info "  - fab-api-client: $FAB_API_CLIENT_VERSION"
    info "  - uas-api-client: $UAS_API_CLIENT_VERSION"
    info "  - asset-marketplace-client-core: $ASSET_MARKETPLACE_CLIENT_CORE_VERSION"
    echo ""
    
    # Backup current pyproject.toml
    cp pyproject.toml pyproject.toml.bak
    
    # Create the new [tool.uv.sources] section
    cat > /tmp/uv-sources.toml << EOF
[tool.uv.sources]
fab-api-client = { git = "https://github.com/${GITHUB_USER}/fab-api-client.git", tag = "${FAB_API_CLIENT_VERSION}" }
uas-api-client = { git = "https://github.com/${GITHUB_USER}/uas-api-client.git", tag = "${UAS_API_CLIENT_VERSION}" }
asset-marketplace-client-core = { git = "https://github.com/${GITHUB_USER}/asset-marketplace-client-core.git", tag = "${ASSET_MARKETPLACE_CLIENT_CORE_VERSION}" }
EOF
    
    # Remove old [tool.uv.sources] section and append new one
    # Find the line number where [tool.uv.sources] starts
    if grep -q "\[tool\.uv\.sources\]" pyproject.toml; then
        # Remove from [tool.uv.sources] to the end of file or next section
        sed -i'.tmp' '/^\[tool\.uv\.sources\]/,/^\[/{ /^\[tool\.uv\.sources\]/d; /^\[/!d; }' pyproject.toml
    fi
    
    # Append new section
    echo "" >> pyproject.toml
    cat /tmp/uv-sources.toml >> pyproject.toml
    
    # Cleanup
    rm -f /tmp/uv-sources.toml pyproject.toml.tmp
    
    info "✓ Updated pyproject.toml with GitHub URLs (versioned)"
    
    info "Running uv sync..."
    uv sync
    
    info "✓ Switched to GitHub dependencies"
    info "  - fab-api-client: github.com/${GITHUB_USER}/fab-api-client @ ${FAB_API_CLIENT_VERSION}"
    info "  - uas-api-client: github.com/${GITHUB_USER}/uas-api-client @ ${UAS_API_CLIENT_VERSION}"
    info "  - asset-marketplace-client-core: github.com/${GITHUB_USER}/asset-marketplace-client-core @ ${ASSET_MARKETPLACE_CLIENT_CORE_VERSION}"
fi

info ""
info "Dependency mode: $MODE"
info "Backup saved to: pyproject.toml.bak"
