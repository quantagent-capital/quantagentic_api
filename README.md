---
title: QuantAgentic API
description: FastAPI server with Redis, CrewAI, and disaster management
tags:
  - fastapi
  - hypercorn
  - python
  - redis
  - crewai
  - celery
---

# QuantAgentic API

A FastAPI-based API for managing disaster events with AI agents powered by CrewAI. Features automated background workers that poll the National Weather Service (NWS) API and intelligently classify alerts into events.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/-NvLj4?referralCode=CRJ8FE)

## ✨ Features

- **FastAPI** with async endpoints
- **Redis** for data persistence and Celery task queue
- **CrewAI** for AI agent orchestration with structured outputs
- **Celery & CeleryBeat** for background task processing
- **Docker Compose** for local Redis setup
- **NWS API Integration** with robust HTTP client
- **Shared state management** for API and agents
- **Disaster Polling Agent** that automatically processes NWS alerts every 5 minutes
- **VTEC Key Generation** for unique alert identification

## 🚀 Getting Started (Mac)

### Prerequisites

- Python 3.9+ (check with `python3 --version`)
- Docker Desktop for Mac (for Redis) - **must be running before starting Redis**
- pip (Python package manager)

### Installation Steps

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <repository-url>
   cd quantagentic_api
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Redis using Docker Compose**:
   
   **Important**: Make sure Docker Desktop is running before executing this command.
   
   ```bash
   docker-compose up -d
   ```
   
   Note: The first time you run this, Docker will download the Redis image, which may take a minute or two.
   
   This will start Redis on `localhost:6379`. To verify it's running:
   ```bash
   docker-compose ps
   ```
   
   If you see an error about Docker daemon not running, start Docker Desktop and wait a few seconds, then try again.

5. **Set up environment variables**:
   
   Create a `.env` file from the example template:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and set your `GEMINI_API_KEY`:
   ```bash
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
   
   The `.env` file is gitignored and will not be committed. All other variables have sensible defaults.
   
   **Required for disaster polling agent**:
   - `GEMINI_API_KEY` - Your Gemini API key
   
   **Optional variables** (with defaults):
   - `REDIS_HOST` - Redis host (default: `localhost`)
   - `REDIS_PORT` - Redis port (default: `6379`)
   - `REDIS_DB` - Redis database number (default: `0`)
   - `REDIS_PASSWORD` - Redis password (default: `None`)
   - `GEMINI_MODEL` - Gemini model (default: `gemini/gemini-3-pro-preview`)
   - `EXECUTOR_MAX_RETRIES` - Max retries for executors (default: `5`)
   - `NWS_USER_AGENT_NAME` - NWS User-Agent name (default: `quantagent_capital`)
   - `NWS_USER_AGENT_EMAIL` - NWS User-Agent email (default: `jacob@quantagent_capital.ai`)

6. **Run the API server**:
   
   Make sure your virtual environment is activated (you should see `(venv)` in your terminal prompt).
   
   ```bash
   hypercorn main:app --reload
   ```
   
   The API will be available at `http://localhost:8000`
   
   You should see output indicating the server is starting. Wait a few seconds for it to fully initialize.

7. **Start the Celery worker** (for background tasks):
   
   In a separate terminal, with the virtual environment activated:
   
   ```bash
   celery -A app.celery_app worker --beat --loglevel=info
   ```
   
   This starts both the Celery worker and the CeleryBeat scheduler. The disaster polling agent will run immediately on startup, then every 5 minutes.
   
   **Viewing Task Output:**
   - The task will log detailed output to the console with `INFO` level logging
   - To see even more detail, use `--loglevel=debug`:
     ```bash
     celery -A app.celery_app worker --beat --loglevel=debug
     ```
   - To manually trigger the task for testing:
     ```bash
     celery -A app.celery_app call app.tasks.disaster_polling_task
     ```
   - To monitor task execution in real-time, use Flower (optional):
     ```bash
     pip install flower
     celery -A app.celery_app flower
     ```
     Then visit `http://localhost:5555` in your browser

   **Debugging in Cursor IDE:**
   - Open the Run and Debug panel (Cmd+Shift+D / Ctrl+Shift+D)
   - Select one of these debug configurations:
     - **Debug: Railway Local (Full Stack)** - Runs both Celery worker and FastAPI server (matches Railway exactly) ⭐ Recommended for production-like debugging
     - **Debug: Disaster Polling Task (Direct)** - Runs the task directly without Celery (best for debugging task logic)
     - **Debug: FastAPI Server** - Starts the FastAPI server with hot-reload
   - Set breakpoints in your code and press F5 to start debugging
   - You can also run debug scripts directly:
     ```bash
     python debug/railway_local.py     # Run full stack (Celery + FastAPI) ⭐ Recommended
     python debug/task_direct.py        # Run task directly (no Celery)
     python debug/test_setup.py         # Verify debug setup
     ```
   - See `debug/README.md` for detailed debugging instructions

8. **Access the API documentation**:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Health Check

Test the API and Redis connection:
```bash
curl http://localhost:8000/health
```

### Stopping Services

- **Stop the API**: Press `Ctrl+C` in the terminal running hypercorn
- **Stop Celery Worker**: Press `Ctrl+C` in the terminal running celery
- **Stop Redis**: `docker-compose down`
- **Stop Redis and remove data**: `docker-compose down -v`

## 📁 Project Structure

```
quantagentic_api/
├── app/
│   ├── __init__.py
│   ├── config.py                    # Configuration settings (Redis, Gemini, Celery)
│   ├── celery_app.py                # Celery application configuration
│   ├── redis_client.py              # Redis client wrapper (quantagent_redis)
│   ├── state.py                     # Shared state object for API and agents
│   ├── schemas/                     # Pydantic models (Location, Event)
│   ├── services/                    # Business logic layer
│   ├── controllers/                 # FastAPI route handlers
│   ├── http_client/                 # HTTP client for external APIs (NWS)
│   ├── crews/                       # CrewAI crews and shared resources
│   │   ├── base_executor.py         # Base executor with retry logic
│   │   ├── tools/                   # Shared CrewAI tools
│   │   │   ├── nws_polling_tool.py
│   │   │   ├── state_tool.py
│   │   │   └── forecast_zone_tool.py
│   │   ├── utils/                   # Shared utilities
│   ├── tasks/                       # Celery tasks
├── debug/                           # Debug scripts for local testing
│   ├── railway_local.py            # Run full stack (Celery + FastAPI) ⭐ Recommended
│   ├── task_direct.py              # Run task directly (no Celery)
│   ├── test_setup.py               # Verify debug setup
│   └── README.md                   # Debugging guide
├── tests/                           # Unit and integration tests
├── .vscode/                         # VS Code/Cursor IDE debug configurations
│   └── launch.json                 # Debug launch configurations
│   │   │   ├── vtec.py              # VTEC key generation
│   │   │   ├── polygon.py           # Polygon overlap detection
│   │   │   └── nws_event_types.py   # NWS event type codes
│   │   └── disaster_polling_agent/  # Disaster polling crew
│   │       ├── config/
│   │       │   ├── agents.yaml      # Agent configuration
│   │       │   └── tasks.yaml       # Task definitions
│   │       ├── crew.py               # Crew definition (@CrewBase)
│   │       ├── executor.py           # Executor with retry logic
│   │       └── models.py             # Structured Pydantic outputs
│   └── tasks/                        # Celery tasks
│       └── disaster_polling_task.py
├── tests/                            # Unit tests (see tests/README.md)
├── main.py                           # FastAPI application entry point
├── requirements.txt                  # Python dependencies
├── docker-compose.yml                # Redis Docker setup
├── pytest.ini                        # Pytest configuration
└── railway.json                      # Railway deployment config
```

## 🔌 API Endpoints

### Events
- `POST /events` - Create a new event
- `GET /events/{event_key}` - Get event by key
- `PUT /events/{event_key}` - Update event

## 🤖 Background Workers

### Disaster Polling Agent

The disaster polling agent is a CrewAI-powered background worker that:

1. **Polls NWS API** every 5 minutes for active alerts
2. **Filters alerts** by severity, urgency, certainty, and event type
3. **Creates VTEC keys** for unique identification
4. **Verifies keys** to ensure data quality
5. **Classifies alerts** into:
   - `new_events` - New warnings to create
   - `updated_events` - Existing warnings to update

**See**: `app/crews/disaster_polling_agent/README.md` for detailed documentation.

## 🛠️ Development

### Running Tests

See `tests/README.md` for comprehensive testing documentation.

Quick start:
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_nws_polling_tool.py
```

### Code Style

This project uses snake_case naming conventions throughout.

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database number | `0` |
| `REDIS_PASSWORD` | Redis password (optional) | `None` |
| `GEMINI_MODEL` | Gemini model to use | `gemini/gemini-3-pro-preview` |
| `GEMINI_API_KEY` | Gemini API key | `test` |
| `EXECUTOR_MAX_RETRIES` | Max retries for crew executors | `5` |
| `NWS_USER_AGENT_NAME` | NWS User-Agent name | `quantagent_capital` |
| `NWS_USER_AGENT_EMAIL` | NWS User-Agent email | `jacob@quantagent_capital.ai` |

**Note**: Celery broker and result backend automatically use the same Redis instance configured above.

## 📝 Notes

- Redis data persists in a Docker volume (`redis_data`)
- The API uses Pydantic models for request/response validation
- All NWS API calls include the required User-Agent header
- The shared state object (`app.state`) is accessible throughout the application
- CrewAI tasks use structured Pydantic outputs for better agent memory and consistency

## 🔗 Useful Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/tutorial/)
- [Hypercorn Documentation](https://hypercorn.readthedocs.io/)
- [Redis Documentation](https://redis.io/docs/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
