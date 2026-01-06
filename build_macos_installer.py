"""
Build MacOS Installer Package

Creates a .app bundle and .dmg installer for MacOS.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

VERSION = "2.0.0"
APP_NAME = "Sponge"
BUNDLE_ID = "com.sponge.rca"


def build_macos_app():
    """Build MacOS .app bundle"""
    print("Building MacOS app bundle...")

    # Use PyInstaller to create the app bundle
    pyinstaller_cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--windowed',
        '--onefile',
        '--icon', 'assets/icon.icns',  # You'll need to provide this
        '--add-data', 'src:src',
        '--add-data', 'data:data',
        '--add-data', 'models:models',
        '--hidden-import', 'sklearn.utils._cython_blas',
        '--hidden-import', 'sklearn.neighbors.typedefs',
        '--hidden-import', 'sklearn.neighbors.quad_tree',
        '--hidden-import', 'sklearn.tree._utils',
        '--hidden-import', 'pandas',
        '--hidden-import', 'numpy',
        '--hidden-import', 'openpyxl',
        '--collect-all', 'tensorflow',
        '--collect-all', 'torch',
        'main.py'
    ]

    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("✓ App bundle created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create app bundle: {e}")
        return False


def create_dmg():
    """Create DMG installer"""
    print("Creating DMG installer...")

    dmg_name = f"{APP_NAME}-{VERSION}.dmg"
    app_path = f"dist/{APP_NAME}.app"

    if not Path(app_path).exists():
        print(f"✗ App bundle not found: {app_path}")
        return False

    # Create DMG using create-dmg (install with: brew install create-dmg)
    dmg_cmd = [
        'create-dmg',
        '--volname', f'{APP_NAME} {VERSION}',
        '--volicon', 'assets/icon.icns',
        '--window-pos', '200', '120',
        '--window-size', '800', '400',
        '--icon-size', '100',
        '--icon', f'{APP_NAME}.app', '200', '190',
        '--hide-extension', f'{APP_NAME}.app',
        '--app-drop-link', '600', '185',
        dmg_name,
        'dist/'
    ]

    try:
        subprocess.run(dmg_cmd, check=True)
        print(f"✓ DMG installer created: {dmg_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create DMG: {e}")
        print("Note: Install create-dmg with: brew install create-dmg")
        return False
    except FileNotFoundError:
        print("✗ create-dmg not found. Install with: brew install create-dmg")
        return False


def create_pkg():
    """Create PKG installer (alternative to DMG)"""
    print("Creating PKG installer...")

    pkg_name = f"{APP_NAME}-{VERSION}.pkg"
    app_path = f"dist/{APP_NAME}.app"

    if not Path(app_path).exists():
        print(f"✗ App bundle not found: {app_path}")
        return False

    # Create component package
    component_plist = "component.plist"

    pkg_cmd = [
        'pkgbuild',
        '--root', 'dist',
        '--identifier', BUNDLE_ID,
        '--version', VERSION,
        '--install-location', '/Applications',
        pkg_name
    ]

    try:
        subprocess.run(pkg_cmd, check=True)
        print(f"✓ PKG installer created: {pkg_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create PKG: {e}")
        return False


def main():
    """Main build process"""
    print(f"Building {APP_NAME} v{VERSION} for MacOS")
    print("=" * 50)

    # Check platform
    if sys.platform != 'darwin':
        print("✗ This script must be run on MacOS")
        return 1

    # Build app bundle
    if not build_macos_app():
        return 1

    # Create DMG installer
    dmg_success = create_dmg()

    # Create PKG installer as alternative
    pkg_success = create_pkg()

    if dmg_success or pkg_success:
        print("\n✓ Build completed successfully!")
        print(f"\nInstallers created in current directory:")
        if dmg_success:
            print(f"  - {APP_NAME}-{VERSION}.dmg")
        if pkg_success:
            print(f"  - {APP_NAME}-{VERSION}.pkg")
        return 0
    else:
        print("\n✗ Build failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
