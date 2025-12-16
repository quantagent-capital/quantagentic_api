#!/bin/bash
# Start script for Railway deployment
# Runs both FastAPI server and Celery worker

set -e

echo "=========================================="
echo "Starting QuantAgentic API services..."
echo "=========================================="

# Seed counties if SEED_COUNTIES is not set to "false"
# This ensures counties are available before services start
if [ "${SEED_COUNTIES:-true}" != "false" ]; then
    echo "Seeding counties data..."
    if python3 app/seeds/seed_counties.py; then
        echo "County seeding completed successfully"
    else
        echo "WARNING: County seeding failed, but continuing startup..."
        echo "Services will start, but drought sync may not work without county data"
    fi
else
    echo "Skipping county seeding (SEED_COUNTIES=false)"
fi

echo "=========================================="

# Start Celery worker with beat in the background
# Note: Celery will use the logging configuration from app.logging_config
# which outputs structured JSON to stdout (not stderr)
echo "Starting Celery worker with beat scheduler..."
celery -A app.celery_app worker --beat --loglevel=info --logfile=/dev/stdout &
CELERY_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $CELERY_PID 2>/dev/null || true
    exit
}

# Set trap to cleanup on script exit
trap cleanup SIGTERM SIGINT EXIT

# Wait a moment for Celery to start
sleep 3

# Check if Celery started successfully
if ! kill -0 $CELERY_PID 2>/dev/null; then
    echo "ERROR: Celery worker failed to start!"
    exit 1
fi

echo "Celery worker started (PID: $CELERY_PID)"
echo "Starting FastAPI server..."
echo "=========================================="

# Start FastAPI server in the foreground (Railway needs a foreground process)
# This keeps the container alive
exec hypercorn main:app --bind "[::]:${PORT:-8000}"

