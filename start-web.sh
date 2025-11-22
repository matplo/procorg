#!/bin/bash
# Start the ProcOrg web interface

cd "$(dirname "$0")"

PID_FILE="procorg.pid"
PORT=9777
LOG_FILE="logs/procorg-web.log"
MAX_LOG_SIZE=10485760  # 10MB in bytes

# Create logs directory if it doesn't exist
mkdir -p logs

# Rotate log file if it's too large
rotate_log() {
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
        if [ "$LOG_SIZE" -gt "$MAX_LOG_SIZE" ]; then
            echo "Rotating log file (size: $LOG_SIZE bytes)..."
            mv "$LOG_FILE" "$LOG_FILE.old"
            # Keep only the last backup
            [ -f "$LOG_FILE.old.1" ] && rm "$LOG_FILE.old.1"
        fi
    fi
}

# Function to check if ProcOrg is already running
check_running() {
    # Check if there's a running process with procorg.web
    if pgrep -f "procorg.web" > /dev/null 2>&1; then
        echo "ERROR: ProcOrg web server is already running!"
        echo ""
        echo "To view running instances:"
        echo "  ps aux | grep procorg.web"
        echo ""
        echo "To stop the server:"
        echo "  pkill -f procorg.web"
        echo "  or use: ./stop-web.sh"
        return 0  # Already running
    fi

    # Check if PID file exists and process is alive
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "ERROR: ProcOrg is already running with PID $OLD_PID"
            return 0  # Already running
        else
            echo "Cleaning up stale PID file..."
            rm -f "$PID_FILE"
        fi
    fi

    # Check if port is in use
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "ERROR: Port $PORT is already in use by another process"
        echo ""
        echo "Process using port $PORT:"
        lsof -Pi :$PORT -sTCP:LISTEN
        return 0  # Port in use
    fi

    return 1  # Not running
}

# launch browser if on a mac using the open command
launch_browser() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:$1"
    fi
    # if linux, try xdg-open
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "http://localhost:$1" 2>/dev/null || echo "Could not open browser automatically. Please navigate to http://localhost:$1"
    fi
}

# Check if already running
if check_running; then
    launch_browser "$PORT"
    exit 1
fi

# Rotate log if needed
rotate_log

# Check if running as root (recommended for multi-user support)
if [ "$EUID" -ne 0 ]; then
    echo "WARNING: Not running as root."
    echo "For full multi-user support with PAM authentication and setuid/setgid,"
    echo "please run with sudo: sudo ./start-web.sh"
    echo ""
    echo "Continuing anyway (authentication will use development mode)..."
    echo ""
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create session directory if it doesn't exist
mkdir -p data/flask_session

# Start the web server
echo "Starting ProcOrg web server on http://localhost:$PORT"
echo "Log file: $LOG_FILE"
echo ""
echo "To view logs in real-time:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To stop the server:"
echo "  ./stop-web.sh"
echo ""

# Start server and save PID, redirect all output to log file
{
    echo "=== ProcOrg Web Server Started: $(date) ==="
    echo "Port: $PORT"
    echo "User: $(whoami)"
    echo "==========================================="
    echo ""
    python3 -c "from procorg.web import run_server; run_server(port=$PORT, debug=False)"
} >> "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "Server started with PID $SERVER_PID"
echo "Access the web interface at http://localhost:$PORT"
echo ""
echo "Server is running in the background."
launch_browser "$PORT"

cd -