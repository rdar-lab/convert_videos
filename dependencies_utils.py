#!/usr/bin/env python3
"""
Download dependencies
"""
import logging
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
import tempfile

import subprocess_utils

# Version constants for external tools
HANDBRAKE_VERSION = '1.7.2'
FFMPEG_VERSION = '6.1'

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


def get_bundled_path():
    """Get the path to the bundled resources directory when running as a PyInstaller executable.

    Returns:
        Path object pointing to the bundle directory, or None if not running as a bundle
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as a PyInstaller bundle
        return Path(sys._MEIPASS)
    return None


def find_dependency_path(dependency_name, config_path=None):
    """Find the path to a dependency executable.

    Searches in this order:
    1. If config_path is provided and is an absolute path that exists, use it directly
    2. If running as PyInstaller bundle, check sys._MEIPASS directory
    3. Use config_path if provided (for PATH resolution), otherwise use dependency_name

    Args:
        dependency_name: Name of the dependency (e.g., 'HandBrakeCLI', 'ffprobe')
        config_path: Optional path from configuration

    Returns:
        str: Path to the dependency executable
    """
    # If config provides an absolute path that exists, use it directly (highest priority)
    if config_path:
        config_path_obj = Path(config_path)
        if config_path_obj.is_absolute() and config_path_obj.exists():
            logger.info(
                f"Using absolute config path for {dependency_name}: {config_path}")
            return str(config_path)

    # Check if running as PyInstaller bundle
    bundle_dir = get_bundled_path()
    if bundle_dir:
        logger.info(
            f"Running as PyInstaller bundle, checking for {dependency_name} in {bundle_dir}")
        # Look for dependency in bundle directory
        # Check for .exe extension on Windows
        if platform.system() == 'Windows':
            exe_name = dependency_name if dependency_name.endswith(
                '.exe') else f'{dependency_name}.exe'
        else:
            exe_name = dependency_name

        bundled_path = bundle_dir / exe_name
        if bundled_path.exists():
            logger.info(f"Found bundled dependency: {bundled_path}")
            return str(bundled_path)
        else:
            logger.warning(f"Bundled dependency not found: {bundled_path}")
    else:
        logger.debug(
            f"Not running as PyInstaller bundle (frozen={getattr(sys, 'frozen', False)})")

    # Fall back to config_path if provided, otherwise use dependency_name
    # (will be resolved via PATH)
    result = config_path if config_path else dependency_name
    logger.info(f"Using fallback path for {dependency_name}: {result}")
    return result


def validate_dependencies(dependency_paths=None):
    """Check if required dependencies are installed.

    Args:
        dependency_paths: Optional dict with 'handbrake', 'ffprobe' and 'ffmpeg' keys
                         specifying paths to executables. If None, uses default names.

    Note:
        Paths should already be resolved by load_config() to handle PyInstaller bundles.
    """
    if dependency_paths is None:
        dependency_paths = {
            'handbrake': 'HandBrakeCLI',
            'ffprobe': 'ffprobe',
            'ffmpeg': 'ffmpeg'
        }

    dependencies = {
        'ffprobe': dependency_paths.get('ffprobe', 'ffprobe'),
        'ffmpeg': dependency_paths.get('ffmpeg', 'ffmpeg'),
        'HandBrakeCLI': dependency_paths.get('handbrake', 'HandBrakeCLI')
    }
    missing = []

    for name, path in dependencies.items():
        is_valid, _ = check_single_dependency(path)
        if not is_valid:
            missing.append(f"{name} (path: {path})")

    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error(
            "Please install the required dependencies. See WINDOWS_INSTALL.md or README.md for instructions.")

    return not missing


def check_single_dependency(command):
    """Check if a single dependency command is available.

    Args:
        command: Command name or path to check

    Returns:
        tuple: (success: bool, error_message: str or None)
               - (True, None) if command is valid
               - (False, "not_found") if command not found
               - (False, "invalid") if command exists but is not valid
               - (False, "timeout") if command timed out
    """
    # Try both --version (for HandBrakeCLI) and -version (for ffprobe/ffmpeg)
    for version_flag in ['--version', '-version']:
        try:
            command_args = [command, version_flag]
            subprocess_utils.run_command(command_args, check=True, timeout=5)
            return True, None
        except FileNotFoundError:
            return False, "not_found"
        except subprocess.CalledProcessError:
            # Try next version flag
            continue
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception:
            return False, "Unknown Error"

    # If both version flags failed, the executable exists but is invalid
    return False, "invalid"


def download_file(url, dest_path):
    """Download a file from a URL to dest_path."""
    logger.info(f"Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            with open(dest_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        logger.info(f"Downloaded to {dest_path}")
        return True
    except (urllib.error.URLError, OSError, IOError) as e:
        logger.error(f"Error downloading {url}: {repr(e)}")
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


def extract_dmg(dmg_path, extract_to):
    """Extract HandBrakeCLI from a macOS DMG file.
    
    Args:
        dmg_path: Path to the DMG file
        extract_to: Directory to extract the CLI binary to
        
    Returns:
        Path to extracted HandBrakeCLI binary, or None if extraction failed
    """
    mount_point = None
    try:
        # Create a unique temporary mount point
        mount_point = tempfile.mkdtemp(prefix='handbrake_mount_')
        
        # Mount the DMG
        logger.info(f"Mounting DMG: {dmg_path}")
        result = subprocess.run(
            ['hdiutil', 'attach', '-nobrowse', '-mountpoint', mount_point, str(dmg_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to mount DMG: {result.stderr}")
            return None
        
        try:
            # Look for HandBrakeCLI in the mounted app bundle
            app_path = Path(mount_point) / 'HandBrake.app' / 'Contents' / 'MacOS' / 'HandBrakeCLI'
            if app_path.exists():
                dest_path = Path(extract_to) / 'HandBrakeCLI'
                shutil.copy2(app_path, dest_path)
                logger.info(f"Extracted HandBrakeCLI to {dest_path}")
                return dest_path
            else:
                logger.error(f"HandBrakeCLI not found in expected location: {app_path}")
                return None
        finally:
            # Always unmount the DMG
            logger.info("Unmounting DMG...")
            subprocess.run(['hdiutil', 'detach', mount_point], 
                         capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        logger.error("Timeout while processing DMG file")
        return None
    except Exception as e:
        logger.error(f"Error extracting DMG: {repr(e)}")
        return None
    finally:
        # Clean up temporary mount point directory if it exists
        if mount_point and os.path.exists(mount_point):
            try:
                os.rmdir(mount_point)
            except OSError:
                # Directory might not be empty or already removed
                pass


def extract_archive(archive_path, extract_to):
    """Extract tar.gz, zip, dmg, or other archive safely."""

    archive_path = str(archive_path)

    logger.info(f"Extracting {archive_path}...")
    if archive_path.endswith('.tar.gz') or archive_path.endswith('.tar.bz2') or archive_path.endswith('.tar.xz'):
        with tarfile.open(archive_path, 'r:*') as tar:
            _safe_extract_tar(tar, extract_to)
    elif archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            _safe_extract_zip(zip_ref, extract_to)
    elif archive_path.endswith('.dmg'):
        # DMG extraction is handled separately via extract_dmg
        # This case shouldn't normally be hit as download_handbrake handles DMG directly
        raise ValueError(f"DMG files should be processed with extract_dmg(), not extract_archive()")
    elif archive_path.endswith('.flatpak'):
        # Flatpak files require the flatpak runtime and cannot be extracted as simple archives
        raise ValueError(f"Flatpak files are not supported for extraction. Please install HandBrakeCLI via system package manager.")
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")
    logger.info(f"Extracted to {extract_to}")


def download_handbrake(tmpdir, download_dir):
    """Download HandBrakeCLI for the specified platform.
    
    Note: 
    - Windows: Downloads and extracts ZIP archive
    - macOS: Downloads DMG and extracts CLI from app bundle
    - Linux: Auto-download not supported (flatpak requires runtime). 
             Users should install via package manager or manually bundle the binary.
    """
    handbrake_dir = tmpdir / 'handbrake'
    handbrake_dir.mkdir(exist_ok=True)
    
    platform_name = get_platform()
    
    # HandBrake CLI download URLs and handling
    if platform_name == 'windows':
        url = f'https://github.com/HandBrake/HandBrake/releases/download/{HANDBRAKE_VERSION}/HandBrakeCLI-{HANDBRAKE_VERSION}-win-x86_64.zip'
        archive_name = url.split('/')[-1]
        archive_path = handbrake_dir / archive_name
        
        if not download_file(url, archive_path):
            return None
        
        extract_archive(archive_path, handbrake_dir)
        
        # Find HandBrakeCLI.exe in extracted files
        for root, dirs, files in os.walk(handbrake_dir):
            if 'HandBrakeCLI.exe' in files:
                shutil.copy(Path(root) / 'HandBrakeCLI.exe', download_dir / 'HandBrakeCLI.exe')
                return download_dir / 'HandBrakeCLI.exe'
                
    elif platform_name == 'macos':
        url = f"https://github.com/HandBrake/HandBrake/releases/download/{HANDBRAKE_VERSION}/HandBrake-{HANDBRAKE_VERSION}.dmg"
        archive_name = url.split('/')[-1]
        archive_path = handbrake_dir / archive_name
        
        if not download_file(url, archive_path):
            return None
        
        # Extract HandBrakeCLI from DMG
        cli_path = extract_dmg(archive_path, download_dir)
        if cli_path:
            return cli_path
            
    elif platform_name == 'linux':
        # Linux: HandBrake CLI is not available as a simple download
        # The flatpak is for the GUI and requires flatpak runtime
        # Users should install via: apt-get install handbrake-cli
        logger.warning("HandBrakeCLI auto-download not supported on Linux.")
        logger.warning("Please install via package manager: sudo apt-get install handbrake-cli")
        logger.warning("Or manually place HandBrakeCLI binary in the build directory.")
        return None
    else:
        logger.warning(f"Warning: HandBrakeCLI auto-download not supported for {platform_name}")
        return None

    logger.error("Was unable to find HandBrakeCLI executable in binary")
    return None


def download_ffmpeg(tmpdir, download_dir):
    """Download ffmpeg/ffprobe for the specified platform."""
    ffmpeg_dir = tmpdir / 'ffmpeg'
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

    platform_name = get_platform()
    
    if platform_name not in urls:
        print(f"Warning: FFmpeg auto-download not supported for {platform_name}")
        return None, None
    
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
                    shutil.copy(Path(root) / 'ffmpeg', download_dir / 'ffmpeg')
                    ffmpeg_bin = download_dir / 'ffmpeg'
                    break
        
        # Download ffprobe
        ffprobe_archive = ffmpeg_dir / 'ffprobe.zip'
        if download_file(macos_urls['ffprobe'], ffprobe_archive):
            extract_archive(ffprobe_archive, ffmpeg_dir / 'ffprobe_extract')
            for root, dirs, files in os.walk(ffmpeg_dir / 'ffprobe_extract'):
                if 'ffprobe' in files:
                    shutil.copy(Path(root) / 'ffprobe', download_dir / 'ffprobe')
                    ffprobe_bin = download_dir / 'ffprobe'
                    break
        
        return ffmpeg_bin, ffprobe_bin
    
    # Windows and Linux have both binaries in one archive
    url = urls[platform_name]
    archive_name = url.split('/')[-1]
    archive_path = ffmpeg_dir / archive_name
    
    if not download_file(url, archive_path):
        return None, None
    
    extract_archive(archive_path, ffmpeg_dir)
    exe_suffix = '.exe' if platform_name == 'windows' else ''

    # Find ffmpeg and ffprobe binaries
    for root, dirs, files in os.walk(ffmpeg_dir):
        if f'ffmpeg{exe_suffix}' in files and not ffmpeg_bin:
            shutil.copy(Path(root) / f'ffmpeg{exe_suffix}', download_dir / f'ffmpeg{exe_suffix}')
            ffmpeg_bin = download_dir / f'ffmpeg{exe_suffix}'
        if f'ffprobe{exe_suffix}' in files and not ffprobe_bin:
            shutil.copy(Path(root) / f'ffprobe{exe_suffix}', download_dir / f'ffprobe{exe_suffix}')
            ffprobe_bin = download_dir / f'ffprobe{exe_suffix}'
    
    return ffmpeg_bin, ffprobe_bin



def download_dependencies(deps_dir, progress_callback=None):
    """
    Download HandBrakeCLI, ffprobe, and ffmpeg to deps_dir directory.

    Args:
        progress_callback: Optional callback function to report progress.
                          Called with status messages as strings.

    Returns:
        tuple: (handbrake_path, ffprobe_path, ffmpeg_path) as strings, or (None, None, None) on failure
    """
    try:

        system = platform.system()

        # Create dependencies directory
        deps_dir.mkdir(exist_ok=True)

        if progress_callback:
            progress_callback("Detecting platform...")
        logger.info("Detecting platform...")

        # Determine executable names based on platform
        if system == "Windows":
            handbrake_exe = "HandBrakeCLI.exe"
            ffprobe_exe = "ffprobe.exe"
            ffmpeg_exe = "ffmpeg.exe"
        else:
            handbrake_exe = "HandBrakeCLI"
            ffprobe_exe = "ffprobe"
            ffmpeg_exe = "ffmpeg"

        # Check if dependencies already exist
        handbrake_path = deps_dir / handbrake_exe
        ffprobe_path = deps_dir / ffprobe_exe
        ffmpeg_path = deps_dir / ffmpeg_exe

        if handbrake_path.exists() and ffprobe_path.exists() and ffmpeg_path.exists():
            # Validate existing dependencies
            handbrake_valid, _ = check_single_dependency(str(handbrake_path))
            ffprobe_valid, _ = check_single_dependency(str(ffprobe_path))
            ffmpeg_valid, _ = check_single_dependency(str(ffmpeg_path))

            if handbrake_valid and ffprobe_valid and ffmpeg_valid:
                msg = "Dependencies already exist and are valid. Skipping download."
                if progress_callback:
                    progress_callback(msg)
                logger.info(msg)
                return (str(handbrake_path.resolve()), str(ffprobe_path.resolve()), str(ffmpeg_path.resolve()))
            else:
                msg = "Existing dependencies are invalid. Re-downloading..."
                if progress_callback:
                    progress_callback(msg)
                logger.info(msg)

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)

            # Download HandBrakeCLI
            msg = f"Downloading HandBrakeCLI for {system}..."
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)

            handbrake_path = download_handbrake(tmpdir, deps_dir)
            if handbrake_path is None:
                raise Exception('Was unable to download handbrake') 

            # Download ffmpeg (includes ffprobe)
            msg = f"Downloading ffmpeg/ffprobe for {system}..."
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)

            ffmpeg_path,ffprobe_path = download_ffmpeg(tmpdir, deps_dir)
            if ffmpeg_path is None or ffprobe_path is None:
                raise Exception('Was unable to download ffmpeg') 

        # Make executables executable on Unix-like systems
        if system in ["Linux", "Darwin"]:
            os.chmod(handbrake_path, 0o755)
            os.chmod(ffprobe_path, 0o755)
            os.chmod(ffmpeg_path, 0o755)

        msg = f"Dependencies downloaded successfully to {deps_dir}"
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

        return (str(handbrake_path.resolve()), str(ffprobe_path.resolve()), str(ffmpeg_path.resolve()))

    except Exception as e:
        logger.error(f"Download dependencies error: {repr(e)}")
        msg = f"Failed to download dependencies: {repr(e)}"
        if progress_callback:
            progress_callback(msg)
        return (None, None, None)
