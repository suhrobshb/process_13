#!/bin/bash

# AutoOps Project Cleanup Script
# ===============================
# This script removes temporary files, logs, and unused assets from the project

echo "🧹 Starting AutoOps project cleanup..."

# Navigate to project root
cd "$(dirname "$0")/.." || exit 1

# Remove temporary files
echo "🗑️  Removing temporary files..."
find . -name "*.tmp" -delete
find . -name "*.temp" -delete
find . -name "*.log" -delete
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete

# Remove Python cache files
echo "🐍 Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

# Remove Node.js cache and build artifacts
echo "📦 Cleaning Node.js artifacts..."
if [ -d "dashboard_ui_v2/node_modules" ]; then
    echo "  - Keeping node_modules (required for development)"
fi

# Remove build artifacts
rm -rf dashboard_ui_v2/dist/
rm -rf dashboard_ui_v2/build/
rm -rf dashboard_ui_v2/.vite/

# Remove test artifacts
echo "🧪 Removing test artifacts..."
rm -rf .pytest_cache/
rm -rf .coverage
rm -rf htmlcov/
rm -rf .tox/

# Remove IDE artifacts
echo "💻 Removing IDE artifacts..."
rm -rf .vscode/
rm -rf .idea/
rm -rf *.swp
rm -rf *.swo

# Remove Docker artifacts
echo "🐳 Cleaning Docker artifacts..."
# Note: We keep docker-compose files as they are part of the project

# Remove SQLite databases (if any)
echo "💾 Removing development databases..."
find . -name "*.db" -not -path "./storage/*" -delete
find . -name "*.sqlite" -not -path "./storage/*" -delete

# Remove backup files
echo "💾 Removing backup files..."
find . -name "*.bak" -delete
find . -name "*.backup" -delete
find . -name "*~" -delete

# Remove OS-specific files
echo "🖥️  Removing OS-specific files..."
find . -name "desktop.ini" -delete
find . -name "folder.conf" -delete

# Clean up empty directories
echo "📁 Removing empty directories..."
find . -type d -empty -delete 2>/dev/null || true

# Show cleanup summary
echo "✅ Cleanup completed successfully!"
echo ""
echo "📊 Project structure after cleanup:"
echo "   - Kept essential source files"
echo "   - Kept configuration files"
echo "   - Kept documentation"
echo "   - Removed temporary files"
echo "   - Removed cache files"
echo "   - Removed build artifacts"
echo ""
echo "🎯 Your project is now clean and ready for production!"