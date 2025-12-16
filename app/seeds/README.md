# Seed Scripts

The seed scripts in this directory are **critical components of the application state** and **must be run** before the API and poller can function correctly.

## Overview

Seed scripts populate Redis with essential reference data that the application relies on. The `State` class (located in `app/state.py`) reads this data from Redis to provide shared state access for both the API server and background workers (poller).

## Why Seeds Are Required

The application uses a pattern where app state is shared between the following:
- **API endpoints** 
- **Background workers** (E.g., disaster polling agent)
- **State data** (Stored in redis)

Without running the seed scripts, Redis will be empty, and the application will fail when trying to access required reference data.

## Available Seed Scripts

### `seed_counties.py`

Populates Redis with county data from the US Census Bureau. This includes:
- County FIPS codes (5-digit)
- State abbreviations and FIPS codes (2-digit)
- County names
- Geographic centroids (latitude/longitude)

**Data Source**: Official US Census Bureau Gazetteer Files (2025)

**Redis Keys**: `county:{fips_code}` (e.g., `county:01001`)

**Usage**:
```bash
# From the project root directory
python3 app/seeds/seed_counties.py
```

**What it does**:
1. Downloads the latest county data from the Census Bureau
2. Transforms the data into `County` schema objects
3. Stores each county in Redis with the key prefix `county:`

**When to run**:
- **Initial setup**: Before starting the API or poller for the first time
- **After Redis data loss**: If Redis is cleared or reset
- **After deployment**: When deploying to a new environment
- **Periodically**: To update county data with latest Census Bureau information

## Running Seed Scripts

### Prerequisites

1. **Redis must be running**:
   ```bash
   docker-compose up -d
   ```

2. **Environment variables configured**:
   - Ensure `.env` file exists (copy from `.env.example` if needed)
   - Redis connection settings should be configured (defaults work for local development)

3. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

### Execution

Run seed scripts from the project root directory:

```bash
# Seed counties
python3 app/seeds/seed_counties.py
```

You should see logging output indicating:
- Data download progress
- Number of records loaded
- Success confirmation

### Verification

Use redis insights to query for the counties directory. You should see ~3200 counties loaded.
