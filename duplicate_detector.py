#!/usr/bin/env python3
"""
Wrapper script to run duplicate_detector from src directory.
"""
import sys
from pathlib import Path
import importlib.util

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Dynamically import duplicate_detector from src to avoid self-import
spec = importlib.util.spec_from_file_location("duplicate_detector_main", src_dir / "duplicate_detector.py")
duplicate_detector_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(duplicate_detector_module)

if __name__ == "__main__":
    duplicate_detector_module.main()
