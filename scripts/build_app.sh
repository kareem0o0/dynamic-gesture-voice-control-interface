#!/usr/bin/env bash
set -euo pipefail

# Build script for SuperClawBot using PyInstaller
# Usage: ./scripts/build_app.sh

APP_NAME="SuperClawBot"
ENTRY="main.py"
DIST_DIR="dist"

# Detect python/pyinstaller command
PYINSTALLER_CMD="pyinstaller"
if ! command -v "$PYINSTALLER_CMD" >/dev/null 2>&1; then
  echo "pyinstaller not found. Install it with: pip install pyinstaller"
  exit 1
fi

echo "Building ${APP_NAME} (entry: ${ENTRY})..."

# Collect --add-data args for folders we want bundled (format: src:dest)
ADD_DATA=()
FOLDERS=("resources" "models" "model_mappings" "saved_configurations" "ui" "controllers" "core" "utils")
for f in "${FOLDERS[@]}"; do
  if [ -e "$f" ]; then
    # PyInstaller on Linux/macOS uses src:dest, on Windows needs src;dest
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
      ADD_DATA+=("$f;$f")
    else
      ADD_DATA+=("$f:$f")
    fi
  fi
done

# Build the argument string
ADD_DATA_ARGS=()
for d in "${ADD_DATA[@]}"; do
  ADD_DATA_ARGS+=("--add-data" "$d")
done

# Run PyInstaller in one-folder mode to preserve writable config/ model files
"$PYINSTALLER_CMD" --noconfirm --clean --onedir --name "$APP_NAME" "${ADD_DATA_ARGS[@]}" "$ENTRY"

echo "Build finished. See ${DIST_DIR}/${APP_NAME} for the output." 

echo "Note: Make sure you test the app by running the executable in the dist folder." 
