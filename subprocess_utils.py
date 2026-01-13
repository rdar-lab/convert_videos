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
    
    logger.info(f"Running command: {' '.join(str(arg) for arg in command_args)}")
    
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
        if 'creationflags' not in kwargs:
            CREATE_NO_WINDOW = 0x08000000
            kwargs['creationflags'] = CREATE_NO_WINDOW
        else:
            # Merge with existing creation flags
            CREATE_NO_WINDOW = 0x08000000
            kwargs['creationflags'] = kwargs['creationflags'] | CREATE_NO_WINDOW
    
    try:
        result = subprocess.run(command_args, **kwargs)
        
        # Log stdout if present and captured, with truncation for large output
        if result.stdout:
            stdout_stripped = result.stdout.strip()
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.info(f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.info(f"Command stdout: {stdout_stripped}")
        
        # Log stderr if present and captured, with truncation for large output
        if result.stderr:
            stderr_stripped = result.stderr.strip()
            if result.returncode == 0:
                # Some tools write normal output to stderr
                if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                    logger.info(f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
                else:
                    logger.info(f"Command stderr: {stderr_stripped}")
            else:
                if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                    logger.error(f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
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
                logger.error(f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.error(f"Command stdout: {stdout_stripped}")
        if e.stderr:
            stderr_stripped = e.stderr.strip()
            if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                logger.error(f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
            else:
                logger.error(f"Command stderr: {stderr_stripped}")
        raise
    except Exception as e:
        logger.error(f"Command execution error: {type(e).__name__}: {e}")
        raise
