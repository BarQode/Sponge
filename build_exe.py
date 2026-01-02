"""
Build script for creating Windows executable using PyInstaller.

Usage:
    python build_exe.py
"""

import PyInstaller.__main__
import sys
from pathlib import Path

def build_executable():
    """Build the Windows executable."""

    # Get the project root directory
    root_dir = Path(__file__).parent

    # PyInstaller arguments
    args = [
        str(root_dir / 'main.py'),  # Main script
        '--noconfirm',               # Don't ask for confirmation
        '--onefile',                 # Create a single executable
        '--console',                 # Console application
        '--name=Sponge-RCA-v1.0',   # Name of the executable
        '--icon=NONE',               # No icon (can be added later)

        # Hidden imports for scikit-learn
        '--hidden-import=sklearn.cluster._dbscan',
        '--hidden-import=sklearn.neighbors._kd_tree',
        '--hidden-import=sklearn.neighbors._ball_tree',
        '--hidden-import=sklearn.utils._cython_blas',
        '--hidden-import=sklearn.neighbors._partition_nodes',

        # Hidden imports for tensorflow
        '--hidden-import=tensorflow',
        '--hidden-import=tensorflow.keras',
        '--hidden-import=tensorflow.keras.layers',

        # Hidden imports for other dependencies
        '--hidden-import=openpyxl',
        '--hidden-import=pandas',
        '--hidden-import=numpy',

        # Collect all submodules
        '--collect-all=sklearn',
        '--collect-all=tensorflow',

        # Add data files
        f'--add-data={root_dir / "LICENSE"}{";." if sys.platform == "win32" else ":"}.',
        f'--add-data={root_dir / "README.md"}{";." if sys.platform == "win32" else ":"}.',

        # Optimization
        '--optimize=2',

        # Clean build
        '--clean',
    ]

    print("Building Windows executable...")
    print(f"Output will be in: {root_dir / 'dist'}")

    try:
        PyInstaller.__main__.run(args)
        print("\n" + "="*70)
        print("✅ Build successful!")
        print(f"Executable location: {root_dir / 'dist' / 'Sponge-RCA-v1.0.exe'}")
        print("="*70)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    build_executable()
