# ProcOrg

A simple process orchestration and management tool for running and monitoring shell scripts. ProcOrg provides both a CLI and web interface for managing your processes.

## Features

- **Process Management**: Register and manage arbitrary shell scripts
- **Scheduling**: Schedule processes using cron expressions
- **Manual Execution**: Run processes manually on demand
- **Real-time Monitoring**: View process status and logs in real-time
- **Dual Interface**: Both CLI and web UI for convenience
- **Log Management**: Capture and display stdout/stderr for each execution
- **Persistent Storage**: File-based storage for process definitions and logs

## Installation

```bash
# Clone or download the repository
cd procorg

# Install dependencies
pip install -r requirements.txt

# Install ProcOrg in development mode
pip install -e .
```

## Quick Start

### 1. Create a test script

```bash
# Create a simple test script
cat > /tmp/test-script.sh << 'EOF'
#!/bin/bash
echo "Hello from ProcOrg!"
echo "Current time: $(date)"
sleep 2
echo "Script completed successfully"
EOF

chmod +x /tmp/test-script.sh
```

### 2. Register the process

```bash
# Register without scheduling (manual execution only)
procorg register my-test-process /tmp/test-script.sh --description "A simple test process"

# Or register with a cron schedule (runs every 5 minutes)
procorg register my-scheduled-process /tmp/test-script.sh --cron "*/5 * * * *" --description "Runs every 5 minutes"
```

### 3. Run and monitor

```bash
# List all registered processes
procorg list

# Run a process manually
procorg run my-test-process

# Check status
procorg status my-test-process

# View logs
procorg logs my-test-process

# Follow logs in real-time
procorg logs my-test-process --follow
```

### 4. Start the scheduler (optional)

For processes with cron expressions:

```bash
# Start the scheduler (runs in foreground)
procorg scheduler-start

# In another terminal, check scheduler info
procorg scheduler-info
```

### 5. Launch the web UI

```bash
# Start the web server
python -m procorg.web

# Or if installed via setup.py:
procorg-web
```

Then open your browser to `http://localhost:5000`

## CLI Commands

### Process Management

- `procorg register <name> <script_path>` - Register a new process
  - `--cron <expression>` - Set cron schedule
  - `--description <text>` - Add description
- `procorg unregister <name>` - Remove a process
- `procorg list` - List all processes
- `procorg run <name>` - Run a process manually
- `procorg stop <name>` - Stop a running process
- `procorg status [name]` - Show process status
- `procorg logs <name>` - View process logs
  - `--stderr` - Show stderr instead of stdout
  - `--lines N` - Number of lines to show
  - `--follow` - Follow log output
- `procorg toggle <name>` - Enable/disable a process
  - `--enable` - Enable the process
  - `--disable` - Disable the process

### Scheduler

- `procorg scheduler-start` - Start the background scheduler
- `procorg scheduler-info` - Show scheduler information

## Web Interface

The web interface provides:

- **Process Registration**: Register new processes directly from the web UI with a user-friendly form
- **Process Management**: Delete processes with confirmation dialogs
- **Real-time Monitoring**: Live process status updates via WebSockets
- **Process Control**: Start and stop processes with one click
- **Live Logs**: View stdout/stderr in real-time with easy switching
- **Scheduler Control**: Start/stop the scheduler and view scheduled processes
- **Modern UI**: Clean, dark theme with visual status indicators

Access the web UI at `http://localhost:9777` (or use port 9778 if 9777 is in use)

## Architecture

```
procorg/
├── procorg/
│   ├── __init__.py
│   ├── storage.py      # File-based persistence layer
│   ├── manager.py      # Core process management
│   ├── scheduler.py    # Cron-based scheduling
│   ├── cli.py          # Command-line interface
│   ├── web.py          # Flask web server
│   └── templates/
│       └── index.html  # Web UI
├── data/
│   ├── processes.json  # Process registry
│   └── logs/           # Process execution logs
├── requirements.txt
├── setup.py
└── README.md
```

## Cron Expression Examples

```
*/5 * * * *     # Every 5 minutes
0 * * * *       # Every hour
0 9 * * *       # Every day at 9:00 AM
0 9 * * 1       # Every Monday at 9:00 AM
0 0 1 * *       # First day of every month at midnight
*/15 9-17 * * * # Every 15 minutes between 9 AM and 5 PM
```

## Storage

ProcOrg uses a simple file-based storage system:

- Process definitions are stored in `data/processes.json`
- Logs are stored in `data/logs/<process_name>/<execution_id>.<stream>.log`
- All data persists between restarts

## Process Lifecycle

1. **Register**: Add a process to the registry
2. **Schedule** (optional): Set a cron expression for automatic execution
3. **Execute**: Process runs (manually or via scheduler)
4. **Monitor**: View status and logs in real-time
5. **Complete**: Process finishes, logs are preserved

## Use Cases

- **Backup Scripts**: Schedule regular backups
- **Data Processing**: Run ETL jobs on a schedule
- **Monitoring**: Execute health checks periodically
- **Maintenance**: Automate cleanup and maintenance tasks
- **Development**: Quick script execution and log monitoring

## Requirements

- Python 3.8+
- Linux/macOS (uses bash for script execution)

## License

MIT

## Contributing

Contributions are welcome! Feel free to submit issues and pull requests.
