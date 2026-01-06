"""
Build Windows Installer

Creates an MSI installer for Windows using cx_Freeze or PyInstaller + Inno Setup.
"""

import os
import sys
import subprocess
from pathlib import Path

VERSION = "2.0.0"
APP_NAME = "Sponge"
COMPANY = "Sponge Project"


def build_windows_exe():
    """Build Windows executable using PyInstaller"""
    print("Building Windows executable...")

    pyinstaller_cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onefile',
        '--console',  # Use --windowed for GUI app
        '--icon', 'assets/icon.ico',  # You'll need to provide this
        '--add-data', 'src;src',
        '--add-data', 'data;data',
        '--add-data', 'models;models',
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
        print("✓ Windows executable created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create executable: {e}")
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
    """Main build process"""
    print(f"Building {APP_NAME} v{VERSION} for Windows")
    print("=" * 50)

    # Check platform
    if sys.platform != 'win32':
        print("⚠ This script is optimized for Windows")
        print("You can still build the executable, but installer creation may fail")

    # Build executable
    if not build_windows_exe():
        return 1

    # Create installer using Inno Setup
    script_path = create_inno_setup_script()
    inno_success = build_inno_installer(script_path)

    # Alternative: Try cx_Freeze MSI (if Inno Setup not available)
    if not inno_success:
        print("\nTrying alternative MSI installer method...")
        msi_success = create_msi_installer()

        if msi_success:
            print(f"\n✓ Build completed successfully!")
            print(f"\nInstaller created: dist/{APP_NAME}-{VERSION}.msi")
            return 0

    if inno_success:
        print(f"\n✓ Build completed successfully!")
        print(f"\nInstaller created: installers/{APP_NAME}-{VERSION}-setup.exe")
        return 0

    print("\n✗ Build failed")
    print("\nNote: You need either:")
    print("  - Inno Setup: https://jrsoftware.org/isdl.php")
    print("  - cx_Freeze: pip install cx-Freeze")
    return 1


if __name__ == "__main__":
    sys.exit(main())
