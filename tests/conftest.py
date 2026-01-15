"""
Pytest configuration file to set up test environment.

This file adds the src directory to Python's sys.path to allow tests
to import source modules directly. This approach is suitable for this
project's simple structure.

Alternative approaches for more complex projects:
- Use 'pip install -e .' to install the package in development mode
- Set PYTHONPATH environment variable
- Use pytest's pythonpath configuration option
"""
import sys
from pathlib import Path

# Add the src directory to Python path so tests can import modules
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))
