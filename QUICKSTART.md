# ProcOrg Quick Start

## Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
```

## Try the Examples

```bash
# Register the example processes (already done if you followed setup)
procorg register example examples/example-script.sh --description "Simple example"
procorg register scheduled examples/example-script.sh --cron "*/10 * * * *"
procorg register error-demo examples/error-script.sh --description "Error handling demo"

# List all processes
procorg list

# Run a process manually
procorg run example

# View the logs
procorg logs example
procorg logs error-demo --stderr

# Check status
procorg status example
```

## Start the Web Interface

```bash
# Option 1: Use the startup script
./start-web.sh

# Option 2: Run directly
source venv/bin/activate
python3 -m procorg.web

# Then open: http://localhost:9777
# (If port 5000 is in use, the server will fail - use port 9778 instead)
```

### Web UI Features

- **Add Process**: Click the "+ Add Process" button to register new scripts
- **Run/Stop**: Control processes with one click
- **View Logs**: See real-time stdout/stderr output
- **Delete**: Remove processes you no longer need
- **Scheduler**: Control the cron-based scheduler

## Using the Scheduler

```bash
# Start the scheduler (runs in foreground)
source venv/bin/activate
procorg scheduler-start

# View scheduler info
procorg scheduler-info
```

## Register Your Own Scripts

```bash
# Without scheduling (manual execution only)
procorg register my-task /path/to/script.sh --description "My task"

# With cron schedule
procorg register backup /path/to/backup.sh --cron "0 2 * * *" --description "Nightly backup"

# Run it
procorg run my-task

# Follow logs in real-time
procorg logs my-task --follow
```

## Common Cron Patterns

- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 9 * * *` - Every day at 9 AM
- `0 0 * * 0` - Every Sunday at midnight
- `0 2 * * 1-5` - Weekdays at 2 AM

## Project Structure

```
procorg/
├── data/
│   ├── processes.json      # Process registry
│   └── logs/               # Execution logs
├── examples/               # Example scripts
├── procorg/                # Source code
└── venv/                   # Python virtual environment
```

Enjoy using ProcOrg!
