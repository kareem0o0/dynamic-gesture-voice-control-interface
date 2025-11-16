README - Building the SuperClawBot App
=====================================

This document explains how to build a standalone application from this repository using PyInstaller.

Prerequisites
-------------
- Python 3.8+ (this repo has been used with Python 3.10)
- A working virtual environment is recommended
- Install project dependencies and PyInstaller:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
```

Build script
------------
Use the provided script `scripts/build_app.sh` to create a one-folder build.

Make it executable and run it:

```bash
chmod +x scripts/build_app.sh
./scripts/build_app.sh
```

What the script does
--------------------
- Uses `pyinstaller --onedir` to create a folder containing the executable and required files.
- Bundles these directories (if present): `resources`, `models`, `model_mappings`, `saved_configurations`, `ui`, `controllers`, `core`, `utils`.

Why one-folder
---------------
The app stores models and configuration files that may be large or written to at runtime. One-folder keeps these accessible and easier to debug.

Platform notes
--------------
- Linux/macOS: `pyinstaller` accepts `src:dest` for `--add-data` entries (the script uses that by default).
- Windows: the script will use `src;dest` if run under a Windows-like environment.

Troubleshooting
---------------
- Missing imports (PyInstaller fails to find PySide6 modules):
  - Ensure `PySide6` is installed in the build environment (`pip install PySide6`).
  - You may need to add hidden imports by editing the PyInstaller command or using a `.spec` file.
- If resources are not found at runtime:
  - Check that the `--add-data` entries bundled the folders into the output folder.
  - When running the executable, resources are available relative to the executable's folder.

Next steps (optional)
---------------------
- Convert to `--onefile` if you prefer a single executable (may require handling of data extraction at runtime).
- Create OS-specific installer packages (deb, rpm, nsis, dmg) using external tools.

If you want, I can run the build next (requires `pyinstaller` installed); you asked not to push, so I will not push any changes to the remote.
