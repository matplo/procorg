#!/bin/bash
# Start the ProcOrg web interface

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if port 5000 is available, otherwise use 8080
PORT=5000
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port 5000 is in use, using port 8080 instead"
    PORT=8080
fi

# Start the web server
echo "Starting ProcOrg web server on http://localhost:$PORT"
python3 -c "from procorg.web import run_server; run_server(port=$PORT, debug=False)"
