#!/bin/bash
# Stop the ProcOrg web interface

cd "$(dirname "$0")"

PID_FILE="procorg.pid"

echo "Stopping ProcOrg web server..."

# Check if PID file exists
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping process $PID..."
        kill "$PID"
        sleep 2

        # Check if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Process didn't stop, forcing..."
            kill -9 "$PID"
        fi

        rm -f "$PID_FILE"
        echo "ProcOrg stopped."
    else
        echo "PID file exists but process $PID is not running."
        rm -f "$PID_FILE"
    fi
else
    echo "No PID file found. Checking for running processes..."
fi

# Also check for any procorg.web processes
if pgrep -f "procorg.web" > /dev/null 2>&1; then
    echo "Found running ProcOrg processes. Stopping them..."
    pkill -f "procorg.web"
    sleep 1

    # Force kill if still running
    if pgrep -f "procorg.web" > /dev/null 2>&1; then
        echo "Forcing shutdown..."
        pkill -9 -f "procorg.web"
    fi
    echo "All ProcOrg processes stopped."
else
    echo "No running ProcOrg processes found."
fi

cd -
