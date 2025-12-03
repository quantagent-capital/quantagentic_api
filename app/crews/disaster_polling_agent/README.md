# Disaster Polling Agent

Background worker that polls the National Weather Service (NWS) API and classifies alerts into episodes and events using CrewAI.

## Architecture

- **CrewAI Agent**: `disaster_spotter` - Expert meteorologist agent
- **CeleryBeat**: Runs every 5 minutes
- **Executor**: `DisasterPollingExecutor` with retry logic (5 retries by default)

## Directory Structure

```
disaster_polling_agent/
├── agent.yaml              # Agent role, goal, backstory
├── tasks.yaml              # Task definitions
├── crew.py                 # Crew creation and execution
├── executor.py             # Executor with retry logic
├── tools/                  # Custom CrewAI tools
│   ├── nws_polling_tool.py
│   ├── state_tool.py
│   └── forecast_zone_tool.py
└── utils/                  # Utilities
    ├── vtec.py            # VTEC key generation
    └── polygon.py         # Polygon overlap detection
```

## Custom Tools

1. **NWSPollingTool**: Polls NWS API with If-Modified-Since header support
2. **GetActiveEpisodesAndEventsTool**: Accesses shared state for active episodes/events
3. **GetForecastZoneTool**: Gets forecast zone polygon coordinates from NWS

## Tasks

1. **poll_nws_alerts**: Polls and filters NWS alerts
2. **create_vtec_keys**: Creates unique VTEC keys for each alert
3. **verify_keys**: Validates VTEC key structure
4. **classify_alerts**: Classifies into new/updated events/episodes

## Running the Worker

### Start Celery Worker
```bash
celery -A app.celery_app worker --loglevel=info
```

### Start CeleryBeat Scheduler
```bash
celery -A app.celery_app beat --loglevel=info
```

### Or run both together
```bash
celery -A app.celery_app worker --beat --loglevel=info
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_nws_polling_tool.py
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run tests in verbose mode
```bash
pytest -v
```

### Run tests for GitHub Actions
The tests are configured to run automatically in GitHub Actions on PR commits. The pytest configuration is in `pytest.ini`.

## Configuration

Set these environment variables:
- `GEMINI_MODEL`: Gemini model (default: `gemini/gemini-3-pro-preview`)
- `GEMINI_API_KEY`: Your Gemini API key
- `EXECUTOR_MAX_RETRIES`: Max retries for executor (default: 5)
- `CELERY_BROKER_URL`: Redis broker URL (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND`: Redis result backend (default: `redis://localhost:6379/0`)

## VTEC Key Format

Keys are created using: `Office + Phenomena + Significance + ETN + Year`

Example: `OFFTOW001524` = Office OFF + Phenomena TO + Significance W + ETN 0015 + Year 24

