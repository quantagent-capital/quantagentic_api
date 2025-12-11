# Testing Documentation

This directory contains unit tests for the QuantAgentic API, covering CrewAI tools, service layer methods, and utilities.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures and configuration
├── test_nws_polling_tool.py       # Tests for NWS polling tool
└── test_event_service.py          # Tests for EventService methods
```

## Running Tests

### Prerequisites

Make sure you have installed all dependencies:
```bash
pip install -r requirements.txt
```

### Basic Commands

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run specific test file:**
```bash
pytest tests/test_nws_polling_tool.py
pytest tests/test_event_service.py
```

**Run specific test class:**
```bash
pytest tests/test_nws_polling_tool.py::TestNWSPollingTool
pytest tests/test_event_service.py::TestCreateEventFromAlert
pytest tests/test_event_service.py::TestUpdateEventFromAlert
```

**Run specific test method:**
```bash
pytest tests/test_nws_polling_tool.py::TestNWSPollingTool::test_async_poll_success
pytest tests/test_event_service.py::TestCreateEventFromAlert::test_create_event_from_alert_success
```

### Advanced Options

**Run with coverage report:**
```bash
pytest --cov=app --cov-report=html
```
This generates an HTML coverage report in `htmlcov/index.html`.

**Run with coverage in terminal:**
```bash
pytest --cov=app --cov-report=term
```

**Stop on first failure:**
```bash
pytest -x
```

**Run tests in parallel (requires pytest-xdist):**
```bash
pytest -n auto
```

**Show print statements:**
```bash
pytest -s
```

**Run only tests matching a pattern:**
```bash
pytest -k "polling"      # Run all polling-related tests
pytest -k "event_service"  # Run all event service tests
pytest -k "create"       # Run all tests with "create" in the name
```

## Test Coverage

### Current Test Files

1. **test_nws_polling_tool.py** (10 tests)
   - Tests NWS API polling functionality (`poll()` and `_async_poll()`)
   - Tests successful polling with proper response handling
   - Tests alert filtering by event type
   - Tests 304 Not Modified response handling
   - Tests VTEC field inclusion in filtered alerts
   - Tests empty response handling
   - Tests error handling and RuntimeError propagation
   - Tests warning/watch filtering
   - Tests location extraction from alerts

2. **test_event_service.py** (17 tests)
   - Tests `create_event_from_alert()` method:
     - Successful event creation from alert
     - Handling missing optional dates
     - Conflict error when event already exists
     - Unknown event type handling
     - Field preservation and mapping
   - Tests `update_event_from_alert()` method:
     - Standard update (CON message type) - merges locations and updates fields
     - COR (Correction) message type - replaces entire event
     - UPG (Update) message type - replaces entire event
     - CAN (Cancel) message type - marks event as inactive
     - EXP (Expired) message type - marks event as inactive
     - Location merging without duplicates
     - Previous ID tracking
     - Case-insensitive message type handling
     - Missing expected_end handling
     - NotFoundError handling

**Total: 27 tests** (all passing ✅)

## Test Fixtures

Fixtures are defined in `conftest.py`:

- `mock_state`: Mock state object for testing
- `mock_nws_client`: Mock NWS client for async testing
- `sample_nws_alert`: Sample NWS alert data structure

## Writing New Tests

### Test File Structure

```python
"""
Unit tests for YourTool.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.crews.tools.your_tool import YourTool


class TestYourTool:
    """Test cases for YourTool."""
    
    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return YourTool()
    
    def test_basic_functionality(self, tool):
        """Test basic tool functionality."""
        result = tool._run(param="value")
        assert "expected" in result
    
    @patch('app.crews.tools.your_tool.SomeDependency')
    def test_with_mock(self, mock_dependency, tool):
        """Test with mocked dependencies."""
        mock_dependency.return_value = "mocked"
        result = tool._run()
        assert result == "expected"
```

### Best Practices

1. **Use descriptive test names**: `test_poll_nws_alerts_success` not `test_poll`
2. **One assertion per test**: Focus each test on one behavior
3. **Use fixtures**: Share common setup code via fixtures
4. **Mock external dependencies**: Don't make real API calls in tests
5. **Test edge cases**: Include error conditions and boundary cases
6. **Use async mocks**: For async functions, use `AsyncMock`

## Continuous Integration

Tests are configured to run automatically in GitHub Actions on PR commits.

### Pytest Configuration

The `pytest.ini` file configures:
- Test discovery patterns
- Output verbosity
- Async test mode
- Warning filters

### GitHub Actions Integration

To set up GitHub Actions, create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v
```

## Debugging Tests

### Run with PDB (Python Debugger)

```bash
pytest --pdb
```
Drops into debugger on failure.

### Show local variables on failure

```bash
pytest -l
```

### Run with detailed traceback

```bash
pytest --tb=long
```

### Run with no traceback

```bash
pytest --tb=no
```

## Common Issues

### Import Errors

If you see import errors, make sure:
1. Virtual environment is activated
2. All dependencies are installed: `pip install -r requirements.txt`
3. You're running from the project root directory

### Async Test Issues

For async tests, ensure:
- Using `pytest-asyncio` (included in requirements)
- Using `AsyncMock` for async functions
- Using `@pytest.mark.asyncio` decorator if needed

### Mock Not Working

If mocks aren't working:
- Check the import path matches exactly
- Use `patch` with the full module path
- Ensure you're patching before the import happens

## Test Data

Sample test data is provided in `conftest.py`:
- `sample_nws_alert`: Complete NWS alert structure
- Mock state objects with realistic data

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Aim for >80% code coverage
4. Update this README if adding new test patterns

