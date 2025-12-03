# Debug Scripts

This directory contains debug scripts for testing and debugging the disaster polling task locally.

## ⚠️ Important: Pydantic Compatibility Issue

There's a known compatibility issue between `langsmith` and Pydantic v2 when using Python 3.12. The debug scripts automatically disable langsmith tracing to work around this.

**If you still get errors when debugging in Cursor IDE:**

1. **Verify you're using the venv Python**: The debugger should use `${workspaceFolder}/venv/bin/python`
2. **Check environment variables**: Make sure `LANGCHAIN_TRACING_V2=false` is set in your launch.json
3. **Run from command line first**: Test with `python debug/task_direct.py` to verify it works

## Debug Configurations

### 1. Railway Local (Full Stack) ⭐ **Recommended for Production-Like Debugging**
Mimics Railway's exact startup process: starts Celery worker with beat scheduler, then FastAPI server. Both run simultaneously and are fully debuggable.

**Best for**: Debugging the complete application stack as it runs in Railway

**Features**:
- ✅ Celery worker with beat scheduler (runs in background, debuggable)
- ✅ FastAPI server (runs in foreground, debuggable)
- ✅ Exact same startup sequence as Railway
- ✅ Both services can be debugged simultaneously
- ✅ Celery beat automatically schedules tasks every 5 minutes

**Usage in Cursor IDE**: Select "Debug: Railway Local (Full Stack)" from the debug configurations

**Usage from command line**:
```bash
# Make sure venv is activated
source venv/bin/activate
python debug/railway_local.py
```

**What it does**:
1. Starts Celery worker with beat scheduler (background process)
2. Waits 3 seconds for Celery to initialize
3. Verifies Celery started successfully
4. Starts FastAPI server on port 8000 (foreground process)
5. Streams Celery logs to console with `[CELERY]` prefix
6. Both processes are debuggable with breakpoints

**Note**: This matches Railway's `railway_startup.sh` exactly, so you can debug issues that only appear in production.

### 2. Disaster Polling Task (Direct)
Runs the disaster polling task directly without Celery. This is the simplest way to debug task logic.

**Best for**: Debugging crew execution, tools, and business logic

**Usage in Cursor IDE**: Select "Debug: Disaster Polling Task (Direct)" from the debug configurations

**Usage from command line**:
```bash
# Make sure venv is activated
source venv/bin/activate
python debug/task_direct.py
```

### 3. FastAPI Server
Starts the FastAPI server with hot-reload enabled.

**Usage in Cursor IDE**: Select "Debug: FastAPI Server" from the debug configurations

**Usage from command line**:
```bash
hypercorn main:app --reload --bind 0.0.0.0:8000
```

### 4. Celery Worker with Auto Task
Queues the disaster polling task and waits for a Celery worker to process it. You'll need to start a Celery worker separately in another terminal.

**Best for**: Testing full Celery task execution with worker processing

**Usage in Cursor IDE**: 
1. Select "Debug: Celery Worker with Auto Task" - this will queue the task
2. In a separate terminal, start the worker: `celery -A app.celery_app worker --loglevel=info --pool=solo`
3. The debugger will wait for the task to complete

**Usage from command line**:
```bash
python debug/celery_with_task.py
# Then in another terminal:
celery -A app.celery_app worker --loglevel=info --pool=solo
```

## Additional Scripts

### `test_setup.py`
Verifies that all imports and configurations are correct before debugging.

**Usage**:
```bash
python debug/test_setup.py
```

## Debugging in Cursor IDE

1. **Open the Debug Panel**: Press `Cmd+Shift+D` (Mac) or `Ctrl+Shift+D` (Windows/Linux)
2. **Select a Configuration**: Choose from the dropdown at the top
3. **Set Breakpoints**: Click in the gutter (left of line numbers) to set breakpoints
4. **Start Debugging**: Press `F5` or click the green play button
5. **Step Through Code**: 
   - `F10` (Step Over): Execute current line
   - `F11` (Step Into): Enter function calls
   - `Shift+F11` (Step Out): Exit current function
   - `F5` (Continue): Resume until next breakpoint

## Troubleshooting

### Pydantic Compatibility Error
If you see `TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'`:

1. **Verify venv is being used**: Check that launch.json uses `${workspaceFolder}/venv/bin/python`
2. **Check environment variables**: Ensure `LANGCHAIN_TRACING_V2=false` is set in launch.json
3. **Test from command line**: Run `python debug/task_direct.py` - if it works, the issue is with the debugger configuration
4. **Reinstall packages**: Try `pip install --upgrade langsmith langchain-core` in your venv

### Module Not Found
- Ensure your virtual environment is activated
- Check that `PYTHONPATH` includes the project root
- Run `python debug/test_setup.py` to verify setup

### Redis Connection Issues
- Make sure Redis is running: `docker-compose up -d`
- Check Redis connection: `redis-cli ping`

### Debugger Using Wrong Python
If the debugger is using system Python instead of venv:

1. Check `.vscode/launch.json` - the `python` field should be `${workspaceFolder}/venv/bin/python`
2. Verify the venv exists: `ls venv/bin/python3`
3. Restart Cursor IDE
4. Check Cursor's Python interpreter setting (bottom right of status bar)

## Tips

- **Start with `task_direct.py`**: It's the simplest and fastest way to debug
- **Set breakpoints early**: In `app/tasks/disaster_polling_task.py` or `app/crews/disaster_polling_agent/executor.py`
- **Use the Variables panel**: Inspect object state during debugging
- **Debug Console**: Evaluate expressions during debugging
- **Test from command line first**: If it works there but not in debugger, it's a debugger config issue

## See Also

- `.vscode/launch.json` - Debug configurations for Cursor IDE
- `README.md` - Main project documentation
- `app/crews/disaster_polling_agent/README.md` - Crew architecture details
