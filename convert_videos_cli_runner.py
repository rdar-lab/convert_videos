#!/usr/bin/env python3
"""
Wrapper script to run convert_videos_cli from src directory.
"""
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run the CLI
from convert_videos_cli import main

if __name__ == "__main__":
    main()
