"""Pytest plugin to inject mocks early."""
import sys
from pathlib import Path

def pytest_configure(config):
    """Configure pytest and inject mocks before any imports."""
    # Inject mocks early, before any homeassistant imports
    if 'homeassistant' not in sys.modules:
        try:
            # Try to import real homeassistant first
            import homeassistant  # noqa: F401
        except ImportError:
            # Inject mocks for local testing
            tests_dir = Path(__file__).parent
            mocks_dir = tests_dir / "mocks"
            if mocks_dir.exists():
                # Add tests directory to path
                if str(tests_dir) not in sys.path:
                    sys.path.insert(0, str(tests_dir))
                try:
                    # Import sitecustomize which injects mocks
                    import mocks.sitecustomize  # noqa: F401
                except ImportError:
                    pass
