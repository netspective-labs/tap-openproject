#!/bin/bash
# Cleanup deprecated files after SDK migration

echo "🧹 Cleaning up deprecated files..."

# Deprecated files that are no longer needed
DEPRECATED_FILES=(
    "setup.py"
    "setup.cfg"
    "tap_openproject/http_client.py"
    "tap_openproject/context.py"
    "tap_openproject/run_with_config.py"
)

# Backup directory
BACKUP_DIR="deprecated_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup in: $BACKUP_DIR"

# Move deprecated files to backup
for file in "${DEPRECATED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  Moving: $file"
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        mv "$file" "$BACKUP_DIR/$file"
    else
        echo "  ⚠️  Not found: $file"
    fi
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "The following files have been moved to backup:"
echo "  - setup.py (replaced by pyproject.toml)"
echo "  - setup.cfg (replaced by pyproject.toml)"
echo "  - tap_openproject/http_client.py (replaced by SDK authenticator)"
echo "  - tap_openproject/context.py (no longer needed)"
echo "  - tap_openproject/run_with_config.py (replaced by SDK CLI)"
echo ""
echo "Backup location: $BACKUP_DIR/"
echo ""
echo "If everything works correctly, you can delete the backup:"
echo "  rm -rf $BACKUP_DIR/"
echo ""
echo "⚠️  Note: Keep config.json.example and examples/ for user reference"
