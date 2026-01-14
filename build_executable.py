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

import os
import sys
import platform
import subprocess
import urllib.request
import urllib.error
import tarfile
import zipfile
import shutil
import argparse
from pathlib import Path


# Version constants for external tools
HANDBRAKE_VERSION = '1.7.2'
FFMPEG_VERSION = '6.1'

# Documentation files to include in distribution
DOCS_TO_INCLUDE = ['README.md', 'LICENSE', 'config.yaml.example', 'BUILD.md']


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
        print(f"PyInstaller is already installed (version {PyInstaller.__version__})")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("PyInstaller installed successfully")


def download_file(url, dest_path):
    """Download a file from a URL to dest_path."""
    print(f"Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            with open(dest_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        print(f"Downloaded to {dest_path}")
        return True
    except (urllib.error.URLError, OSError, IOError) as e:
        print(f"Error downloading {url}: {e}")
        return False


def _is_within_directory(directory, target):
    """
    Return True if the target path is inside the given directory.
    Prevents path traversal when extracting archives.
    """
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    prefix = os.path.commonpath([abs_directory])
    return os.path.commonpath([abs_directory, abs_target]) == prefix


def _safe_extract_tar(tar, extract_to):
    """Safely extract members from a tarfile into extract_to."""
    for member in tar.getmembers():
        member_path = os.path.join(extract_to, member.name)
        if not _is_within_directory(extract_to, member_path):
            raise RuntimeError(f"Attempted path traversal in tar archive: {member.name}")
    tar.extractall(extract_to)


def _safe_extract_zip(zip_ref, extract_to):
    """Safely extract members from a zipfile into extract_to."""
    for member in zip_ref.infolist():
        member_path = os.path.join(extract_to, member.filename)
        if not _is_within_directory(extract_to, member_path):
            raise RuntimeError(f"Attempted path traversal in zip archive: {member.filename}")
    zip_ref.extractall(extract_to)


def extract_archive(archive_path, extract_to):
    """Extract tar.gz, zip, or other archive safely."""

    archive_path = str(archive_path)

    print(f"Extracting {archive_path}...")
    if archive_path.endswith('.tar.gz') or archive_path.endswith('.tar.bz2') or archive_path.endswith('.tar.xz'):
        with tarfile.open(archive_path, 'r:*') as tar:
            _safe_extract_tar(tar, extract_to)
    elif archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            _safe_extract_zip(zip_ref, extract_to)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")
    print(f"Extracted to {extract_to}")


def download_handbrake(platform_name, download_dir):
    """Download HandBrakeCLI for the specified platform.
    
    Note: For Linux and macOS, this relies on system installation or manual bundling
    as HandBrake doesn't provide easily extractable binaries for these platforms.
    """
    handbrake_dir = download_dir / 'handbrake'
    handbrake_dir.mkdir(exist_ok=True)
    
    # HandBrake CLI download URLs
    # Note: Only Windows provides a zip with extractable binary
    urls = {
        'windows': f'https://github.com/HandBrake/HandBrake/releases/download/{HANDBRAKE_VERSION}/HandBrakeCLI-{HANDBRAKE_VERSION}-win-x86_64.zip',
        # Linux and macOS: Use system installation via apt/brew
    }
    
    if platform_name not in urls:
        print(f"Warning: HandBrakeCLI auto-download not supported for {platform_name}")
        print("Please ensure HandBrakeCLI is available in the system PATH or bundled manually")
        return None
    
    url = urls[platform_name]
    archive_name = url.split('/')[-1]
    archive_path = handbrake_dir / archive_name
    
    if platform_name == 'windows':
        if not download_file(url, archive_path):
            return None
        extract_archive(archive_path, handbrake_dir)
        # Find HandBrakeCLI.exe
        for root, dirs, files in os.walk(handbrake_dir):
            if 'HandBrakeCLI.exe' in files:
                return Path(root) / 'HandBrakeCLI.exe'
    
    # For Linux/macOS, we'll rely on system installation or manual bundling
    print(f"Note: For {platform_name}, please ensure HandBrakeCLI is installed on the system")
    print("The executable will attempt to find it in PATH at runtime")
    return None


def download_ffmpeg(platform_name, download_dir):
    """Download ffmpeg/ffprobe for the specified platform."""
    ffmpeg_dir = download_dir / 'ffmpeg'
    ffmpeg_dir.mkdir(exist_ok=True)
    
    # FFmpeg download URLs (static builds)
    # Note: Windows and Linux use latest release, macOS uses versioned
    urls = {
        'windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',  # Latest stable
        'linux': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz',  # Latest stable
        'macos': {
            'ffmpeg': f'https://evermeet.cx/ffmpeg/ffmpeg-{FFMPEG_VERSION}.zip',
            'ffprobe': f'https://evermeet.cx/ffmpeg/ffprobe-{FFMPEG_VERSION}.zip'
        }
    }
    
    if platform_name not in urls:
        print(f"Warning: FFmpeg auto-download not supported for {platform_name}")
        return None
    
    exe_suffix = '.exe' if platform_name == 'windows' else ''
    ffmpeg_bin = None
    ffprobe_bin = None
    
    # macOS requires separate downloads for ffmpeg and ffprobe
    if platform_name == 'macos':
        macos_urls = urls[platform_name]
        
        # Download ffmpeg
        ffmpeg_archive = ffmpeg_dir / 'ffmpeg.zip'
        if download_file(macos_urls['ffmpeg'], ffmpeg_archive):
            extract_archive(ffmpeg_archive, ffmpeg_dir / 'ffmpeg_extract')
            for root, dirs, files in os.walk(ffmpeg_dir / 'ffmpeg_extract'):
                if 'ffmpeg' in files:
                    ffmpeg_bin = Path(root) / 'ffmpeg'
                    break
        
        # Download ffprobe
        ffprobe_archive = ffmpeg_dir / 'ffprobe.zip'
        if download_file(macos_urls['ffprobe'], ffprobe_archive):
            extract_archive(ffprobe_archive, ffmpeg_dir / 'ffprobe_extract')
            for root, dirs, files in os.walk(ffmpeg_dir / 'ffprobe_extract'):
                if 'ffprobe' in files:
                    ffprobe_bin = Path(root) / 'ffprobe'
                    break
        
        return {'ffmpeg': ffmpeg_bin, 'ffprobe': ffprobe_bin}
    
    # Windows and Linux have both binaries in one archive
    url = urls[platform_name]
    archive_name = url.split('/')[-1]
    archive_path = ffmpeg_dir / archive_name
    
    if not download_file(url, archive_path):
        return None
    
    extract_archive(archive_path, ffmpeg_dir)
    
    # Find ffmpeg and ffprobe binaries
    for root, dirs, files in os.walk(ffmpeg_dir):
        if f'ffmpeg{exe_suffix}' in files and not ffmpeg_bin:
            ffmpeg_bin = Path(root) / f'ffmpeg{exe_suffix}'
        if f'ffprobe{exe_suffix}' in files and not ffprobe_bin:
            ffprobe_bin = Path(root) / f'ffprobe{exe_suffix}'
    
    return {'ffmpeg': ffmpeg_bin, 'ffprobe': ffprobe_bin}


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
            ffmpeg_binary = ffmpeg_info.get('ffmpeg') if isinstance(ffmpeg_info, dict) else None
            ffprobe_binary = ffmpeg_info.get('ffprobe') if isinstance(ffmpeg_info, dict) else None
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
    
    spec_file = Path(f'{exe_name}.spec')
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print(f"Created spec file: {spec_file}")
    return spec_file


def build_with_pyinstaller(spec_file):
    """Run PyInstaller with the spec file."""
    print(f"Building executable with PyInstaller...")
    try:
        subprocess.check_call([sys.executable, '-m', 'PyInstaller', str(spec_file), '--clean', '--noconfirm'])
        print("Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False


def create_distribution_package(platform_name):
    """Create a distributable archive with the executables and necessary files."""
    dist_dir = Path('dist')
    exe_extension = '.exe' if platform_name == 'windows' else ''
    
    # Check for both executables
    cli_exe_name = f'convert_videos_cli{exe_extension}'
    gui_exe_name = f'convert_videos_gui{exe_extension}'
    cli_exe_path = dist_dir / cli_exe_name
    gui_exe_path = dist_dir / gui_exe_name
    
    if not cli_exe_path.exists():
        print(f"Error: CLI executable not found at {cli_exe_path}")
        return None
    
    # Create package directory
    package_name = f'convert_videos-{platform_name}'
    package_dir = dist_dir / package_name
    package_dir.mkdir(exist_ok=True)
    
    # Copy CLI executable
    shutil.copy2(cli_exe_path, package_dir / cli_exe_name)
    print(f"Packaged CLI executable: {cli_exe_name}")
    
    # Copy GUI executable if it exists
    if gui_exe_path.exists():
        shutil.copy2(gui_exe_path, package_dir / gui_exe_name)
        print(f"Packaged GUI executable: {gui_exe_name}")
    else:
        print(f"GUI executable not found at {gui_exe_path}, skipping")
    
    # Copy documentation files
    for doc in DOCS_TO_INCLUDE:
        if Path(doc).exists():
            shutil.copy2(doc, package_dir / doc)
    
    # Create archive
    archive_name = f"{package_name}"
    if platform_name == 'windows':
        archive_path = dist_dir / f"{archive_name}.zip"
        shutil.make_archive(str(dist_dir / archive_name), 'zip', package_dir)
    else:
        archive_path = dist_dir / f"{archive_name}.tar.gz"
        shutil.make_archive(str(dist_dir / archive_name), 'gztar', package_dir)
    
    print(f"Created distribution package: {archive_path}")
    return archive_path


def main():
    parser = argparse.ArgumentParser(description='Build portable executable for convert_videos')
    parser.add_argument('--platform', choices=['windows', 'linux', 'macos'],
                        help='Target platform (default: auto-detect)')
    
    args = parser.parse_args()
    
    # Determine platform
    target_platform = args.platform if args.platform else get_platform()
    print(f"Building for platform: {target_platform}")
    
    # Install PyInstaller
    install_pyinstaller()
    
    # Always download dependencies
    binaries_data = {}
    download_dir = Path('external_binaries')
    download_dir.mkdir(exist_ok=True)
    
    # Download HandBrakeCLI
    print("\nDownloading HandBrakeCLI...")
    handbrake_bin = download_handbrake(target_platform, download_dir)
    if handbrake_bin:
        binaries_data['handbrake'] = str(handbrake_bin)
    else:
        print("\n[FAILED] HandBrakeCLI download failed!")
        sys.exit(1)
    
    # Download FFmpeg
    print("\nDownloading FFmpeg...")
    ffmpeg_bins = download_ffmpeg(target_platform, download_dir)
    if ffmpeg_bins:
        ffmpeg_data = {}
        ffmpeg_path = ffmpeg_bins.get('ffmpeg')
        if ffmpeg_path is not None:
            ffmpeg_data['ffmpeg'] = str(ffmpeg_path)
        ffprobe_path = ffmpeg_bins.get('ffprobe')
        if ffprobe_path is not None:
            ffmpeg_data['ffprobe'] = str(ffprobe_path)
        if ffmpeg_data:
            binaries_data['ffmpeg'] = ffmpeg_data
        else:
            print("\n[FAILED] FFmpeg download failed - no binaries found!")
            sys.exit(1)
    else:
        print("\n[FAILED] FFmpeg download failed!")
        sys.exit(1)
    
    # Verify we have all required binaries
    if 'handbrake' not in binaries_data:
        print("\n[FAILED] No HandBrakeCLI binary available for bundling")
        sys.exit(1)
    if 'ffmpeg' not in binaries_data:
        print("\n[FAILED] No FFmpeg binaries available for bundling")
        sys.exit(1)
    
    print(f"\n[SUCCESS] All binaries ready for bundling:")
    print(f"  HandBrakeCLI: {binaries_data.get('handbrake')}")
    if isinstance(binaries_data.get('ffmpeg'), dict):
        print(f"  ffmpeg: {binaries_data['ffmpeg'].get('ffmpeg')}")
        print(f"  ffprobe: {binaries_data['ffmpeg'].get('ffprobe')}")
    
    # Create spec files for both CLI and GUI versions
    print("\nCreating PyInstaller spec files...")
    
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
    print("\nBuilding CLI executable...")
    cli_success = build_with_pyinstaller(spec_file_cli)
    
    if not cli_success:
        print("\n[FAILED] CLI build failed!")
        sys.exit(1)
    
    print("\nBuilding GUI executable...")
    gui_success = build_with_pyinstaller(spec_file_gui)
    
    if not gui_success:
        print("\n[WARNING] GUI build failed, but CLI build succeeded")
        print("This might happen if tkinter is not available")
    
    # Create distribution package
    print("\nCreating distribution package...")
    create_distribution_package(target_platform)
    
    print("\n[SUCCESS] Build completed successfully!")
    exe_extension = '.exe' if target_platform == 'windows' else ''
    print(f"\nExecutable locations:")
    print(f"  CLI: dist/convert_videos_cli{exe_extension}")
    if gui_success:
        print(f"  GUI: dist/convert_videos_gui{exe_extension}")
    print(f"Distribution package: dist/convert_videos-{target_platform}.{'zip' if target_platform == 'windows' else 'tar.gz'}")


if __name__ == '__main__':
    main()
