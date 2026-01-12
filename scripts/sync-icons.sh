#!/bin/bash
# Sync icons from shared/icons to both integration and plugin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Syncing icons..."

# Copy to integration
if [ -f "$REPO_ROOT/shared/icons/icon.svg" ]; then
    cp "$REPO_ROOT/shared/icons/icon.svg" "$REPO_ROOT/integration/custom_components/octopus_energy_es/"
    echo "✓ Copied icon.svg to integration"
fi

if [ -f "$REPO_ROOT/shared/icons/logo.svg" ]; then
    cp "$REPO_ROOT/shared/icons/logo.svg" "$REPO_ROOT/integration/custom_components/octopus_energy_es/"
    echo "✓ Copied logo.svg to integration"
fi

# Plugin doesn't need icons (HACS plugins typically don't use icons)
# But if needed in the future, uncomment:
# cp "$REPO_ROOT/shared/icons/icon.svg" "$REPO_ROOT/plugin/" 2>/dev/null || true

echo "Icons synced successfully!"
