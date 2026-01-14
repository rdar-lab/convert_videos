#!/usr/bin/env python3
"""
Subprocess utilities for running external commands with proper Windows support.

This module provides utilities for running subprocesses with appropriate flags
for PyInstaller frozen apps, particularly the CREATE_NO_WINDOW flag on Windows
which prevents subprocess timeouts in GUI applications.
"""

import sys
import subprocess
import logging
import re

logger = logging.getLogger(__name__)


def run_command(command_args, **kwargs):
    """Run a subprocess command and log all details.

    This function wraps subprocess.run with proper Windows support for frozen apps.
    On Windows, when running as a PyInstaller bundle, it automatically adds the
    CREATE_NO_WINDOW flag to prevent subprocess timeouts in GUI applications.

    Args:
        command_args: List of command arguments
        **kwargs: Additional arguments to pass to subprocess.run
                 Note: stdout and stderr will be set to PIPE for logging unless
                       explicitly set to None by the caller

    Returns:
        subprocess.CompletedProcess: Result of the command execution
    """
    # Maximum length for logged output to prevent huge log files
    MAX_OUTPUT_LENGTH = 2000

    logger.info(
        f"Running command: {' '.join(str(arg) for arg in command_args)}")

    # Capture output for logging unless explicitly disabled
    # Allow caller to explicitly set stdout/stderr to None if they don't want capture
    if 'stdout' not in kwargs:
        kwargs['stdout'] = subprocess.PIPE
    if 'stderr' not in kwargs:
        kwargs['stderr'] = subprocess.PIPE
    if 'text' not in kwargs:
        kwargs['text'] = True

    # On Windows frozen apps, add CREATE_NO_WINDOW flag to prevent subprocess timeouts
    # This is critical for GUI apps built with console=False
    if sys.platform == 'win32' and getattr(sys, 'frozen', False):
        CREATE_NO_WINDOW = 0x08000000
        # Ensure CREATE_NO_WINDOW is included alongside any existing creation flags
        kwargs['creationflags'] = kwargs.get(
            'creationflags', 0) | CREATE_NO_WINDOW

    try:
        result = subprocess.run(command_args, **kwargs)

        # Log stdout if present and captured, with truncation for large output
        if result.stdout:
            stdout_stripped = result.stdout.strip()
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.info(
                    f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.info(f"Command stdout: {stdout_stripped}")

        # Log stderr if present and captured, with truncation for large output
        if result.stderr:
            stderr_stripped = result.stderr.strip()
            if result.returncode == 0:
                # Some tools write normal output to stderr
                if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                    logger.info(
                        f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
                else:
                    logger.info(f"Command stderr: {stderr_stripped}")
            else:
                if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                    logger.error(
                        f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
                else:
                    logger.error(f"Command stderr: {stderr_stripped}")

        # Log exit code
        logger.info(f"Command exit code: {result.returncode}")

        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            stdout_stripped = e.stdout.strip()
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.error(
                    f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.error(f"Command stdout: {stdout_stripped}")
        if e.stderr:
            stderr_stripped = e.stderr.strip()
            if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                logger.error(
                    f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
            else:
                logger.error(f"Command stderr: {stderr_stripped}")
        raise
    except Exception as e:
        logger.error(f"Command execution error: {type(e).__name__}: {e}")
        raise


def run_command_with_progress(command_args, progress_callback=None, progress_pattern=None, cancellation_check=None, **kwargs):
    """Run a subprocess command with progress monitoring.

    This function runs a command and monitors its output for progress updates.
    It's designed for long-running commands that report progress (e.g., HandBrakeCLI).

    Args:
        command_args: List of command arguments
        progress_callback: Optional callback function(percentage: float) called with progress updates
        progress_pattern: Optional regex pattern to extract progress percentage from output.
                         The pattern should have a capture group for the percentage number.
                         Default: r'Encoding:.+?([0-9.]+) %' (HandBrakeCLI format)
        cancellation_check: Optional callback function() -> bool that returns True if operation should be cancelled
        **kwargs: Additional arguments to pass to subprocess.Popen

    Returns:
        subprocess.CompletedProcess: Result of the command execution with stdout/stderr captured

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code
        Exception: If cancellation_check returns True during execution
    """
    logger.info(f"Running command with progress: {' '.join(str(arg) for arg in command_args)}")

    # Default progress pattern for HandBrakeCLI
    if progress_pattern is None:
        progress_pattern = re.compile(r'Encoding:.+?([0-9.]+) %')
    elif isinstance(progress_pattern, str):
        progress_pattern = re.compile(progress_pattern)

    # Set up output capture
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT  # Merge stderr into stdout for unified progress monitoring
    kwargs['universal_newlines'] = True
    kwargs['bufsize'] = 1  # Line buffered

    # On Windows frozen apps, add CREATE_NO_WINDOW flag
    if sys.platform == 'win32' and getattr(sys, 'frozen', False):
        CREATE_NO_WINDOW = 0x08000000
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(command_args, **kwargs)
        
        # Collect output for logging
        output_lines = []
        
        # Monitor output for progress
        for line in process.stdout:
            output_lines.append(line)
            
            # Check for cancellation
            if cancellation_check and cancellation_check():
                logger.info("Cancellation requested, terminating process")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise Exception("Operation cancelled by user")
            
            # Extract and report progress
            if progress_callback and progress_pattern:
                match = progress_pattern.search(line)
                if match:
                    try:
                        percentage = float(match.group(1))
                        progress_callback(percentage)
                    except (ValueError, IndexError):
                        pass  # Ignore invalid progress values
        
        # Wait for completion
        return_code = process.wait()
        
        # Combine output
        stdout = ''.join(output_lines)
        
        # Create result object similar to subprocess.run
        result = subprocess.CompletedProcess(
            args=command_args,
            returncode=return_code,
            stdout=stdout,
            stderr=None  # stderr was merged into stdout
        )
        
        # Log results
        MAX_OUTPUT_LENGTH = 2000
        if stdout:
            stdout_stripped = stdout.strip()
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.info(
                    f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.info(f"Command stdout: {stdout_stripped}")
        
        logger.info(f"Command exit code: {return_code}")
        
        # Raise exception if command failed
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command_args, stdout, None)
        
        return result
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            stdout_stripped = e.stdout.strip()
            MAX_OUTPUT_LENGTH = 2000
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.error(
                    f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.error(f"Command stdout: {stdout_stripped}")
        raise
    except Exception as e:
        logger.error(f"Command execution error: {type(e).__name__}: {e}")
        raise
