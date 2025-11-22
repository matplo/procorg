#!/bin/bash
# Start the ProcOrg web interface

cd "$(dirname "$0")"

PORT=9777
if [ ! -z "$1" ]; then
    PORT=$1
fi

# if $1 is stop identify the process and kill it
if [ "$1" == "stop" ]; then
    if [ -f "procorg.lock" ]; then
        read LOCK_PID LOCK_PORT < procorg.lock
        if kill -0 "$LOCK_PID" 2>/dev/null; then
            echo "Stopping ProcOrg (PID $LOCK_PID)..."
            kill "$LOCK_PID"
            rm procorg.lock
            echo "ProcOrg stopped."
        else
            echo "No running ProcOrg process found. Removing stale lock file..."
            rm procorg.lock
        fi
    else
        echo "ProcOrg is not running."
    fi
    exit 0
fi

# launch browser if on a mac using the open command
launch_browser() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:$1"
    fi
}

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if lock file exists
if [ -f "procorg.lock" ]; then
    echo "ProcOrg is already running. Please stop it before starting a new instance."
    # Read PID and PORT from lock file
    read LOCK_PID LOCK_PORT < procorg.lock
    
    # Check if the process is still running
    if kill -0 "$LOCK_PID" 2>/dev/null; then
        read -p "Process (PID $LOCK_PID) is running. Kill it? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill "$LOCK_PID"
            rm procorg.lock
            echo "Process killed. Restarting..."
        else
            launch_browser "$LOCK_PORT"
            exit 1
        fi
    else
        # Stale lock file
        echo "Removing stale lock file..."
        rm procorg.lock
    fi
fi

# Start the web server
echo "Starting ProcOrg web server on http://localhost:$PORT"
python3 -m procorg.web > /dev/null 2>&1 &
WEB_PID=$!
echo "$WEB_PID $PORT" > procorg.lock
sleep 2
launch_browser "$PORT"

cd - > /dev/null