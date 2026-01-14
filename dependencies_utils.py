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

import subprocess_utils

logger = logging.getLogger(__name__)


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
        machine = platform.machine().lower()

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

        # Determine URLs based on platform
        if system == "Windows":
            handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-win-x86_64.zip"
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        elif system == "Darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-arm64.dmg"
            else:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-x86_64.dmg"
            ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip"
        elif system == "Linux":
            if "arm" in machine or "aarch64" in machine:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-aarch64.flatpak"
                ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
            else:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-x86_64.flatpak"
                ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        else:
            raise Exception(f"Unsupported platform: {system}")

        # Download HandBrakeCLI
        msg = f"Downloading HandBrakeCLI for {system}..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

        handbrake_archive = deps_dir / \
            f"handbrake.{handbrake_url.split('.')[-1]}"

        try:
            urllib.request.urlretrieve(handbrake_url, handbrake_archive)
        except Exception as e:
            raise Exception(f"Failed to download HandBrakeCLI: {repr(e)}")

        # Extract HandBrakeCLI
        msg = "Extracting HandBrakeCLI..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

        try:
            if handbrake_archive.suffix == ".zip":
                with zipfile.ZipFile(handbrake_archive, 'r') as zip_ref:
                    zip_ref.extractall(deps_dir / "handbrake_temp")
                # Find HandBrakeCLI executable in extracted files
                handbrake_found = False
                for root, dirs, files in os.walk(deps_dir / "handbrake_temp"):
                    if handbrake_exe in files:
                        shutil.copy2(Path(root) / handbrake_exe,
                                     deps_dir / handbrake_exe)
                        handbrake_found = True
                        break
                if not handbrake_found:
                    raise Exception(
                        f"Could not find {handbrake_exe} in downloaded archive")
                shutil.rmtree(deps_dir / "handbrake_temp")
            elif handbrake_archive.suffix in [".tar", ".xz", ".gz"]:
                with tarfile.open(handbrake_archive, 'r:*') as tar_ref:
                    tar_ref.extractall(deps_dir / "handbrake_temp")
                # Find HandBrakeCLI executable
                handbrake_found = False
                for root, dirs, files in os.walk(deps_dir / "handbrake_temp"):
                    if handbrake_exe in files:
                        shutil.copy2(Path(root) / handbrake_exe,
                                     deps_dir / handbrake_exe)
                        handbrake_found = True
                        break
                if not handbrake_found:
                    raise Exception(
                        f"Could not find {handbrake_exe} in downloaded archive")
                temp_dir = deps_dir / "handbrake_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            else:
                # For formats like .dmg or .flatpak, just inform user
                raise Exception(
                    f"HandBrakeCLI format {handbrake_archive.suffix} requires manual installation on {system}")
        except Exception as e:
            logger.error(f"HandBrakeCLI extraction error: {repr(e)}")
            msg = f"HandBrakeCLI extraction failed: {repr(e)}"
            if progress_callback:
                progress_callback(msg)
            return (None, None, None)
        finally:
            if handbrake_archive.exists():
                handbrake_archive.unlink()

        # Download ffmpeg (includes ffprobe)
        msg = f"Downloading ffmpeg for {system}..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

        ffmpeg_archive = deps_dir / f"ffmpeg.{ffmpeg_url.split('.')[-1]}"

        try:
            urllib.request.urlretrieve(ffmpeg_url, ffmpeg_archive)
        except Exception as e:
            raise Exception(f"Failed to download ffmpeg: {repr(e)}")

        # Extract ffmpeg/ffprobe
        msg = "Extracting ffmpeg..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

        try:
            if ffmpeg_archive.suffix == ".zip":
                with zipfile.ZipFile(ffmpeg_archive, 'r') as zip_ref:
                    zip_ref.extractall(deps_dir / "ffmpeg_temp")
                # Find ffprobe and ffmpeg executables (often in bin subdirectory)
                ffprobe_found = False
                ffmpeg_found = False
                for root, dirs, files in os.walk(deps_dir / "ffmpeg_temp"):
                    if ffprobe_exe in files and not ffprobe_found:
                        shutil.copy2(Path(root) / ffprobe_exe,
                                     deps_dir / ffprobe_exe)
                        ffprobe_found = True
                    if ffmpeg_exe in files and not ffmpeg_found:
                        shutil.copy2(Path(root) / ffmpeg_exe,
                                     deps_dir / ffmpeg_exe)
                        ffmpeg_found = True
                    if ffprobe_found and ffmpeg_found:
                        break
                if not ffprobe_found:
                    raise Exception(
                        f"Could not find {ffprobe_exe} in downloaded archive")
                if not ffmpeg_found:
                    raise Exception(
                        f"Could not find {ffmpeg_exe} in downloaded archive")
                temp_dir = deps_dir / "ffmpeg_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            elif ffmpeg_archive.suffix in [".tar", ".xz", ".gz"]:
                with tarfile.open(ffmpeg_archive, 'r:*') as tar_ref:
                    tar_ref.extractall(deps_dir / "ffmpeg_temp")
                # Find ffprobe and ffmpeg executables (often in bin subdirectory)
                ffprobe_found = False
                ffmpeg_found = False
                for root, dirs, files in os.walk(deps_dir / "ffmpeg_temp"):
                    if ffprobe_exe in files and not ffprobe_found:
                        shutil.copy2(Path(root) / ffprobe_exe,
                                     deps_dir / ffprobe_exe)
                        ffprobe_found = True
                    if ffmpeg_exe in files and not ffmpeg_found:
                        shutil.copy2(Path(root) / ffmpeg_exe,
                                     deps_dir / ffmpeg_exe)
                        ffmpeg_found = True
                    if ffprobe_found and ffmpeg_found:
                        break
                if not ffprobe_found:
                    raise Exception(
                        f"Could not find {ffprobe_exe} in downloaded archive")
                if not ffmpeg_found:
                    raise Exception(
                        f"Could not find {ffmpeg_exe} in downloaded archive")
                temp_dir = deps_dir / "ffmpeg_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            else:
                raise Exception(
                    f"ffmpeg format {ffmpeg_archive.suffix} not supported")
        except Exception as e:
            logger.error(f"ffmpeg extraction error: {repr(e)}")
            msg = f"ffmpeg extraction failed: {repr(e)}"
            if progress_callback:
                progress_callback(msg)
            return (None, None, None)
        finally:
            if ffmpeg_archive.exists():
                ffmpeg_archive.unlink()

        # Make executables executable on Unix-like systems
        if system in ["Linux", "Darwin"]:
            if handbrake_path.exists():
                os.chmod(handbrake_path, 0o755)
            if ffprobe_path.exists():
                os.chmod(ffprobe_path, 0o755)
            if ffmpeg_path.exists():
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
