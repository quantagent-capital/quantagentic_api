#!/usr/bin/env python3
"""
Quick test to verify debug setup is working.
Run this to ensure all imports and paths are correct.

Usage:
	python debug/test_setup.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing debug setup...")
print("=" * 60)

# Test 1: Import task
try:
	from app.tasks.disaster_polling_task import disaster_polling_task
	print("✓ Task import successful")
except Exception as e:
	print(f"✗ Task import failed: {e}")
	sys.exit(1)

# Test 2: Import executor
try:
	from app.crews.disaster_polling_agent.executor import DisasterPollingExecutor
	print("✓ Executor import successful")
except Exception as e:
	print(f"✗ Executor import failed: {e}")
	sys.exit(1)

# Test 3: Import crew
try:
	from app.crews.disaster_polling_agent.crew import DisasterPollingCrew
	print("✓ Crew import successful")
except Exception as e:
	print(f"✗ Crew import failed: {e}")
	sys.exit(1)

# Test 4: Check Celery app
try:
	from app.celery_app import celery_app
	task_registered = 'app.tasks.disaster_polling_task' in celery_app.tasks
	print(f"✓ Celery app loaded, task registered: {task_registered}")
except Exception as e:
	print(f"✗ Celery app failed: {e}")
	sys.exit(1)

# Test 5: Check config
try:
	from app.config import settings
	print(f"✓ Config loaded, Redis: {settings.redis_host}:{settings.redis_port}")
except Exception as e:
	print(f"✗ Config failed: {e}")
	sys.exit(1)

print("=" * 60)
print("✓ All imports successful! Debug setup is ready.")
print("\nNext steps:")
print("1. Open Run and Debug panel (Cmd+Shift+D)")
print("2. Select 'Debug: Disaster Polling Task (Direct)'")
print("3. Set breakpoints in your code")
print("4. Press F5 to start debugging")

