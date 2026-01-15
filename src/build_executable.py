#!/usr/bin/env python3
"""
Build script for creating portable executables using PyInstaller.
Supports Windows, Linux, and macOS.

This script will:
1. Install PyInstaller if not present
2. Download HandBrakeCLI and ffmpeg binaries for the target platform
3. Create a standalone executable with all dependencies bundled
4. Package everything into a distributable archive

Usage:
    python build_executable.py --platform [windows|linux|macos]
    
    # Or let it auto-detect:
    python build_executable.py
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import logging

import dependencies_utils
import logging_utils

# Version constants for external tools
HANDBRAKE_VERSION = '1.7.2'
FFMPEG_VERSION = '6.1'

# Documentation files to include in distribution
DOCS_TO_INCLUDE = ['README.md', 'LICENSE', 'config.yaml.example']

logger = logging.getLogger(__name__)

def get_platform():
    """Detect the current platform."""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        logger.info(
            f"PyInstaller is already installed (version {PyInstaller.__version__})")
    except ImportError:
        logger.info("Installing PyInstaller...")
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        logger.info("PyInstaller installed successfully")


def create_spec_file(platform_name, binaries_data, script_name='convert_videos.py',
                     exe_name='convert_videos', console=True):
    """Create PyInstaller spec file for the application.

    Args:
        platform_name: Target platform ('windows', 'linux', 'macos')
        binaries_data: Dict containing binary paths to bundle
        script_name: Python script to build (default: 'convert_videos.py')
        exe_name: Name for the output executable (default: 'convert_videos')
        console: Whether to show console window (default: True for CLI, False for GUI)
    """
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Data files to include
datas = []

# Binary files to include
binaries = []

# Add external binaries if provided
"""

    if binaries_data:
        spec_content += f"# Bundled binaries\n"
        if 'handbrake' in binaries_data and binaries_data['handbrake']:
            handbrake_path = repr(binaries_data['handbrake'])
            spec_content += f"binaries.append(({handbrake_path}, '.'))\n"
        if 'ffmpeg' in binaries_data and binaries_data['ffmpeg']:
            ffmpeg_info = binaries_data['ffmpeg']
            ffmpeg_binary = ffmpeg_info.get(
                'ffmpeg') if isinstance(ffmpeg_info, dict) else None
            ffprobe_binary = ffmpeg_info.get(
                'ffprobe') if isinstance(ffmpeg_info, dict) else None
            if ffmpeg_binary:
                ffmpeg_path = repr(ffmpeg_binary)
                spec_content += f"binaries.append(({ffmpeg_path}, '.'))\n"
            if ffprobe_binary:
                ffprobe_path = repr(ffprobe_binary)
                spec_content += f"binaries.append(({ffprobe_path}, '.'))\n"

    spec_content += f"""
a = Analysis(
    ['{script_name}'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['yaml', 'tkinter', 'imagehash', 'PIL.Image', 'PIL.ImageTk'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
"""

    if platform_name == 'macos':
        spec_content += "    icon=None,\n"
    elif platform_name == 'windows':
        spec_content += "    icon=None,\n"

    spec_content += ")\n"

    # Create spec file in the src directory (where this script is located)
    src_dir = Path(__file__).parent
    spec_file = src_dir / f'{exe_name}.spec'
    with open(spec_file, 'w') as f:
        f.write(spec_content)

    logger.info(f"Created spec file: {spec_file}")
    return spec_file


def build_with_pyinstaller(spec_file):
    """Run PyInstaller with the spec file.
    
    Runs from the src directory so all imports work naturally.
    """
    logger.info(f"Building executable with PyInstaller...")
    try:
        # Get the src directory (where this script is located)
        src_dir = Path(__file__).parent
        # Run PyInstaller from the src directory
        subprocess.check_call(
            [sys.executable, '-m', 'PyInstaller', str(spec_file), '--clean', '--noconfirm'],
            cwd=str(src_dir))
        logger.info("Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Build failed: {e}")
        return False


def create_distribution_package(platform_name):
    """Create a distributable archive with the executables and necessary files."""
    # PyInstaller creates dist directory in src when run from src
    src_dir = Path(__file__).parent
    dist_dir = src_dir / 'dist'
    exe_extension = '.exe' if platform_name == 'windows' else ''

    # Check for both executables
    cli_exe_name = f'convert_videos_cli{exe_extension}'
    gui_exe_name = f'convert_videos_gui{exe_extension}'
    cli_exe_path = dist_dir / cli_exe_name
    gui_exe_path = dist_dir / gui_exe_name

    if not cli_exe_path.exists():
        logger.error(f"Error: CLI executable not found at {cli_exe_path}")
        return None

    # Create package directory
    package_name = f'convert_videos-{platform_name}'
    package_dir = dist_dir / package_name
    package_dir.mkdir(exist_ok=True)

    # Copy CLI executable
    shutil.copy2(cli_exe_path, package_dir / cli_exe_name)
    logger.info(f"Packaged CLI executable: {cli_exe_name}")

    # Copy GUI executable if it exists
    if gui_exe_path.exists():
        shutil.copy2(gui_exe_path, package_dir / gui_exe_name)
        logger.info(f"Packaged GUI executable: {gui_exe_name}")
    else:
        logger.warning(f"GUI executable not found at {gui_exe_path}, skipping")

    # Copy documentation files from repo root
    repo_root = src_dir.parent
    for doc in DOCS_TO_INCLUDE:
        doc_path = repo_root / doc
        if doc_path.exists():
            shutil.copy2(doc_path, package_dir / doc)

    # Create archive
    archive_name = f"{package_name}"
    if platform_name == 'windows':
        archive_path = dist_dir / f"{archive_name}.zip"
        shutil.make_archive(str(dist_dir / archive_name), 'zip', package_dir)
    else:
        archive_path = dist_dir / f"{archive_name}.tar.gz"
        shutil.make_archive(str(dist_dir / archive_name), 'gztar', package_dir)

    logger.info(f"Created distribution package: {archive_path}")
    return archive_path


def main():
    parser = argparse.ArgumentParser(
        description='Build portable executable for convert_videos')
    parser.add_argument('--platform', choices=['windows', 'linux', 'macos'],
                        help='Target platform (default: auto-detect)')

    args = parser.parse_args()

    # Determine platform
    target_platform = args.platform if args.platform else get_platform()
    logging_utils.setup_logging()
    logger.info(f"Building for platform: {target_platform}")

    # Install PyInstaller
    install_pyinstaller()

    # Always download dependencies to repo root
    repo_root = Path(__file__).parent.parent
    binaries_data = {}
    download_dir = repo_root / 'external_binaries'
    download_dir.mkdir(exist_ok=True)

    handbrake_path, ffprobe_path, ffmpeg_path = dependencies_utils.download_dependencies(
        download_dir)
    binaries_data['handbrake'] = handbrake_path
    binaries_data['ffmpeg'] = {
        'ffmpeg': ffmpeg_path,
        'ffprobe': ffprobe_path
    }

    # Verify we have all required binaries
    if not binaries_data['handbrake']:
        logger.error("[FAILED] No HandBrakeCLI binary available for bundling")
        sys.exit(1)
    if not binaries_data['ffmpeg']['ffmpeg'] or not binaries_data['ffmpeg']['ffprobe']:
        logger.error("[FAILED] No FFmpeg/ffprobe binaries available for bundling")
        sys.exit(1)

    logger.info(f"[SUCCESS] All binaries ready for bundling:")
    logger.info(f"  HandBrakeCLI: {binaries_data.get('handbrake')}")
    logger.info(f"  ffmpeg: {binaries_data['ffmpeg'].get('ffmpeg')}")
    logger.info(f"  ffprobe: {binaries_data['ffmpeg'].get('ffprobe')}")

    # Create spec files for both CLI and GUI versions
    logger.info("Creating PyInstaller spec files...")

    # CLI version with console (always runs in background mode)
    spec_file_cli = create_spec_file(
        target_platform,
        binaries_data,
        script_name='convert_videos_cli.py',
        exe_name='convert_videos_cli',
        console=True
    )

    # GUI version without console
    spec_file_gui = create_spec_file(
        target_platform,
        binaries_data,
        script_name='convert_videos_gui.py',
        exe_name='convert_videos_gui',
        console=False
    )

    # Build both executables with PyInstaller
    logger.info("Building CLI executable...")
    cli_success = build_with_pyinstaller(spec_file_cli)

    if not cli_success:
        logger.error("[FAILED] CLI build failed!")
        sys.exit(1)

    logger.info("Building GUI executable...")
    gui_success = build_with_pyinstaller(spec_file_gui)

    if not gui_success:
        logger.error("[WARNING] GUI build failed, but CLI build succeeded, This might happen if tkinter is not available")
        sys.exit(1)

    # Create distribution package
    logger.info("Creating distribution package...")
    create_distribution_package(target_platform)

    logger.info("[SUCCESS] Build completed successfully!")
    exe_extension = '.exe' if target_platform == 'windows' else ''
    logger.info(f"Executable locations:")
    logger.info(f"  CLI: src/dist/convert_videos_cli{exe_extension}")
    if gui_success:
        logger.info(f"  GUI: src/dist/convert_videos_gui{exe_extension}")
    logger.info(
        f"Distribution package: src/dist/convert_videos-{target_platform}.{'zip' if target_platform == 'windows' else 'tar.gz'}")


if __name__ == '__main__':
    main()
