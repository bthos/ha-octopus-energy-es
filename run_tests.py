#!/usr/bin/env python
"""Script to run tests with mocks injected early."""
import sys
from pathlib import Path

# Inject mocks before any imports
tests_dir = Path(__file__).parent / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

try:
    import homeassistant  # noqa: F401
    print("Using real Home Assistant")
except ImportError:
    print("Injecting Home Assistant mocks for local testing...")
    try:
        import mocks.sitecustomize  # noqa: F401
        print("Mocks injected successfully")
    except ImportError as e:
        print(f"Warning: Could not inject mocks: {e}")
        print("Tests may fail without Home Assistant installed")

# Now run pytest
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(sys.argv[1:]))
