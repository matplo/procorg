#!/bin/bash
# Start the ProcOrg web interface

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

procorg $@
if [ $? -ne 0 ]; then
    echo "Failed to start ProcOrg. Please check the error messages above."
    exit 1
fi
