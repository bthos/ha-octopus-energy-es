#!/bin/bash
# Sync version from shared/version.txt to all components

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION_FILE="$REPO_ROOT/shared/version.txt"

if [ ! -f "$VERSION_FILE" ]; then
    echo "Error: $VERSION_FILE not found"
    exit 1
fi

VERSION=$(cat "$VERSION_FILE")
echo "Syncing version: $VERSION"

# Update integration manifest.json
if [ -f "$REPO_ROOT/integration/custom_components/octopus_energy_es/manifest.json" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$REPO_ROOT/integration/custom_components/octopus_energy_es/manifest.json"
    else
        # Linux
        sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$REPO_ROOT/integration/custom_components/octopus_energy_es/manifest.json"
    fi
    echo "✓ Updated integration manifest.json"
fi

# Update frontend package.json
if [ -f "$REPO_ROOT/frontend/package.json" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\",/" "$REPO_ROOT/frontend/package.json"
    else
        # Linux
        sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\",/" "$REPO_ROOT/frontend/package.json"
    fi
    echo "✓ Updated frontend package.json"
fi

echo "Version synced successfully!"
