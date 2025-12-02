---
title: QuantAgentic API
description: FastAPI server with Redis, CrewAI, and disaster management
tags:
  - fastapi
  - hypercorn
  - python
  - redis
  - crewai
---

# QuantAgentic API

A FastAPI-based API for managing disaster episodes and events with AI agents powered by CrewAI.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/-NvLj4?referralCode=CRJ8FE)

## ✨ Features

- FastAPI with async endpoints
- Redis for data persistence
- CrewAI for AI agent orchestration
- Docker Compose for local Redis setup
- Robust HTTP client for external API integration (NWS)
- Shared state management for API and agents

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

5. **Set environment variables** (optional, defaults work for local development):
   ```bash
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   export REDIS_DB=0
   ```

6. **Run the API server**:
   
   Make sure your virtual environment is activated (you should see `(venv)` in your terminal prompt).
   
   ```bash
   hypercorn main:app --reload
   ```
   
   The API will be available at `http://localhost:8000`
   
   You should see output indicating the server is starting. Wait a few seconds for it to fully initialize.

7. **Access the API documentation**:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Health Check

Test the API and Redis connection:
```bash
curl http://localhost:8000/health
```

### Stopping Services

- **Stop the API**: Press `Ctrl+C` in the terminal running hypercorn
- **Stop Redis**: `docker-compose down`
- **Stop Redis and remove data**: `docker-compose down -v`

## 📁 Project Structure

```
quantagentic_api/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration settings
│   ├── redis_client.py        # Redis client wrapper (quantagent_redis)
│   ├── state.py               # Shared state object
│   ├── schemas/               # Pydantic models (Location, Episode, Event)
│   ├── services/              # Business logic layer
│   ├── controllers/           # FastAPI route handlers
│   └── http_client/           # HTTP client for external APIs
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Redis Docker setup
└── railway.json              # Railway deployment config
```

## 🔌 API Endpoints

### Episodes
- `POST /episodes` - Create a new episode
- `GET /episodes/{episode_id}` - Get episode by ID
- `PUT /episodes/{episode_id}` - Update episode

### Events
- `POST /events` - Create a new event
- `GET /events/{event_key}` - Get event by key
- `PUT /events/{event_key}` - Update event
- `GET /events/{event_key}/has_episode` - Check if event has episode

## 🛠️ Development

### Running Tests

(Add test commands here when tests are implemented)

### Code Style

This project uses snake_case naming conventions throughout.

## 📝 Notes

- Redis data persists in a Docker volume (`redis_data`)
- The API uses Pydantic models for request/response validation
- All NWS API calls include the required User-Agent header
- The shared state object (`app.state`) is accessible throughout the application

## 🔗 Useful Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/tutorial/)
- [Hypercorn Documentation](https://hypercorn.readthedocs.io/)
- [Redis Documentation](https://redis.io/docs/)
- [CrewAI Documentation](https://docs.crewai.com/)
