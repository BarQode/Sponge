"""
Build Windows Installer - Production Ready

Creates an MSI installer for Windows using cx_Freeze or PyInstaller + Inno Setup.
Includes ML models (Random Forest, Linear Regression) and all dependencies.
"""

import os
import sys
import subprocess
from pathlib import Path

VERSION = "3.0.0"  # Updated for ML-enhanced version
APP_NAME = "Sponge"
COMPANY = "Sponge Project"


def build_windows_exe():
    """Build Windows executable using PyInstaller with ML dependencies"""
    print("Building Windows executable with ML models (Random Forest + Linear Regression)...")

    # Ensure models directory exists
    Path("models").mkdir(exist_ok=True)

    pyinstaller_cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onefile',
        '--console',  # Use --windowed for GUI app
        '--icon', 'assets/icons/icon.ico' if Path('assets/icons/icon.ico').exists() else '',
        '--add-data', 'src;src',
        '--add-data', 'data;data',
        '--add-data', 'models;models',

        # Core ML hidden imports
        '--hidden-import', 'sklearn.ensemble',
        '--hidden-import', 'sklearn.ensemble._forest',
        '--hidden-import', 'sklearn.ensemble._iforest',
        '--hidden-import', 'sklearn.linear_model',
        '--hidden-import', 'sklearn.linear_model._base',
        '--hidden-import', 'sklearn.cluster',
        '--hidden-import', 'sklearn.cluster._dbscan',
        '--hidden-import', 'sklearn.feature_extraction.text',
        '--hidden-import', 'sklearn.preprocessing',
        '--hidden-import', 'sklearn.preprocessing._label',
        '--hidden-import', 'sklearn.preprocessing._data',
        '--hidden-import', 'sklearn.model_selection',
        '--hidden-import', 'sklearn.metrics',

        # sklearn internal dependencies
        '--hidden-import', 'sklearn.utils._cython_blas',
        '--hidden-import', 'sklearn.neighbors.typedefs',
        '--hidden-import', 'sklearn.neighbors.quad_tree',
        '--hidden-import', 'sklearn.tree',
        '--hidden-import', 'sklearn.tree._utils',
        '--hidden-import', 'sklearn.tree._tree',
        '--hidden-import', 'sklearn.utils._typedefs',
        '--hidden-import', 'sklearn.utils._heap',
        '--hidden-import', 'sklearn.utils._sorting',
        '--hidden-import', 'sklearn.utils._vector_sentinel',

        # Model persistence
        '--hidden-import', 'joblib',
        '--hidden-import', 'joblib.externals.loky',

        # Data handling
        '--hidden-import', 'pandas',
        '--hidden-import', 'numpy',
        '--hidden-import', 'numpy.random',
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'openpyxl.cell',
        '--hidden-import', 'openpyxl.styles',

        # Web scraping
        '--hidden-import', 'duckduckgo_search',
        '--hidden-import', 'bs4',
        '--hidden-import', 'lxml',

        # Optional: TensorFlow (if used)
        '--collect-all', 'tensorflow',

        # Exclude large unnecessary packages
        '--exclude-module', 'torch',  # PyTorch not needed
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'IPython',
        '--exclude-module', 'notebook',

        'main.py'
    ]

    # Remove empty icon argument if icon doesn't exist
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]

    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("✓ Windows executable created successfully")
        print(f"  Location: dist/{APP_NAME}.exe")

        # Verify executable
        exe_path = Path(f"dist/{APP_NAME}.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"  Size: {size_mb:.1f} MB")

        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create executable: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PyInstaller is installed: pip install pyinstaller")
        print("  2. Check all dependencies are installed: pip install -r requirements.txt")
        print("  3. Try running with --debug=all flag for more details")
        return False
    except FileNotFoundError:
        print("✗ PyInstaller not found. Install it with: pip install pyinstaller")
        return False


def create_inno_setup_script():
    """Create Inno Setup script for installer"""
    print("Creating Inno Setup script...")

    script_content = f"""
; Inno Setup Script for {APP_NAME}
; Generated automatically

#define MyAppName "{APP_NAME}"
#define MyAppVersion "{VERSION}"
#define MyAppPublisher "{COMPANY}"
#define MyAppURL "https://github.com/BarQode/Sponge"
#define MyAppExeName "{APP_NAME}.exe"

[Setup]
AppId={{{{B5F8C9A0-1234-5678-9ABC-DEF012345678}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
OutputDir=installers
OutputBaseFilename={APP_NAME}-{VERSION}-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\\{{#MyAppExeName}}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{{app}}"; Flags: ignoreversion
; Add other necessary files

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
"""

    script_path = Path("installer_script.iss")
    script_path.write_text(script_content)

    print(f"✓ Inno Setup script created: {script_path}")
    return str(script_path)


def build_inno_installer(script_path):
    """Build installer using Inno Setup"""
    print("Building installer with Inno Setup...")

    # Try to find Inno Setup compiler
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    iscc_path = None
    for path in inno_paths:
        if Path(path).exists():
            iscc_path = path
            break

    if not iscc_path:
        print("✗ Inno Setup not found. Please install from: https://jrsoftware.org/isdl.php")
        print("After installation, run this script again.")
        return False

    try:
        subprocess.run([iscc_path, script_path], check=True)
        print(f"✓ Installer created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create installer: {e}")
        return False


def create_msi_installer():
    """Create MSI installer using cx_Freeze (alternative method)"""
    print("Creating MSI installer with cx_Freeze...")

    # Create setup script for cx_Freeze
    setup_content = f"""
from cx_Freeze import setup, Executable
import sys

build_exe_options = {{
    "packages": ["os", "sys", "numpy", "pandas", "sklearn", "tensorflow", "torch"],
    "includes": ["src"],
    "include_files": [("data", "data"), ("models", "models")],
    "excludes": ["tkinter", "test", "unittest"],
}}

bdist_msi_options = {{
    "upgrade_code": "{{B5F8C9A0-1234-5678-9ABC-DEF012345678}}",
    "add_to_path": True,
    "initial_target_dir": r"[ProgramFilesFolder]\\{APP_NAME}",
}}

base = None
if sys.platform == "win32":
    base = "Console"  # Use "Win32GUI" for windowed app

executables = [
    Executable(
        "main.py",
        base=base,
        target_name="{APP_NAME}.exe",
        icon="assets/icon.ico",
        shortcut_name="{APP_NAME}",
        shortcut_dir="DesktopFolder",
    )
]

setup(
    name="{APP_NAME}",
    version="{VERSION}",
    description="Sponge AI Root Cause Analysis Tool",
    options={{
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    }},
    executables=executables,
)
"""

    setup_path = Path("setup_cx.py")
    setup_path.write_text(setup_content)

    try:
        subprocess.run([sys.executable, "setup_cx.py", "bdist_msi"], check=True)
        print("✓ MSI installer created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create MSI installer: {e}")
        return False


def main():
    """Main build process for production-ready Windows installer"""
    print(f"Building {APP_NAME} v{VERSION} for Windows")
    print("ML-Enhanced: Random Forest + Linear Regression + DBSCAN + Isolation Forest")
    print("=" * 70)

    # Check platform
    if sys.platform != 'win32':
        print("⚠ This script is optimized for Windows")
        print("You can still build the executable, but installer creation may fail")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            return 1

    # Pre-flight checks
    print("\n[1/4] Pre-flight checks...")
    try:
        import sklearn
        import joblib
        import numpy
        import pandas
        print("  ✓ All ML dependencies available")
    except ImportError as e:
        print(f"  ✗ Missing dependency: {e}")
        print("  Install with: pip install -r requirements.txt")
        return 1

    # Build executable
    print("\n[2/4] Building executable...")
    if not build_windows_exe():
        return 1

    # Create installer using Inno Setup
    print("\n[3/4] Creating installer...")
    script_path = create_inno_setup_script()
    inno_success = build_inno_installer(script_path)

    # Alternative: Try cx_Freeze MSI (if Inno Setup not available)
    if not inno_success:
        print("\nTrying alternative MSI installer method...")
        msi_success = create_msi_installer()

        if msi_success:
            print(f"\n✓ Build completed successfully!")
            print(f"\nInstaller created: dist/{APP_NAME}-{VERSION}.msi")
            print("\n📦 Distribution Package:")
            print(f"  - Executable: dist/{APP_NAME}.exe")
            print(f"  - Installer: dist/{APP_NAME}-{VERSION}.msi")
            print("\n🚀 Ready for distribution!")
            return 0

    if inno_success:
        print(f"\n[4/4] Build completed successfully!")
        print(f"\n✓ Installer created: installers/{APP_NAME}-{VERSION}-setup.exe")
        print("\n📦 Distribution Package:")
        print(f"  - Executable: dist/{APP_NAME}.exe")
        print(f"  - Installer: installers/{APP_NAME}-{VERSION}-setup.exe")
        print("\n🚀 Ready for distribution!")
        print("\nTo distribute:")
        print(f"  1. Share installers/{APP_NAME}-{VERSION}-setup.exe with users")
        print("  2. Users run the installer to install on Windows")
        print("  3. ML models will be bundled in the installation")
        return 0

    print("\n✗ Build failed")
    print("\nNote: You need either:")
    print("  - Inno Setup: https://jrsoftware.org/isdl.php")
    print("  - cx_Freeze: pip install cx-Freeze")
    print("\nAlternatively, distribute dist/{APP_NAME}.exe directly (no installer)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
