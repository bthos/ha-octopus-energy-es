# Running Tests Locally

## Quick Start

For local testing without full Home Assistant installation, use the test runner script:

```bash
python run_tests.py tests/ -v
```

Or run specific tests:

```bash
python run_tests.py tests/test_config_flow.py::test_user_step_initial -v
```

## Requirements

Install test dependencies:

```bash
pip install pytest pytest-asyncio pytest-mock voluptuous
```

## How It Works

The `run_tests.py` script automatically injects Home Assistant mocks before running tests, allowing you to test the integration without installing the full Home Assistant package.

## CI Testing

Tests run automatically in CI (GitHub Actions) with full Home Assistant dependencies installed via `pytest-homeassistant-custom-component`.

## Mock Structure

- `tests/mocks/homeassistant.py` - Mock Home Assistant modules
- `tests/mocks/sitecustomize.py` - Early injection of mocks
- `tests/conftest.py` - Test fixtures and configuration
