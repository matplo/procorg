#!/bin/bash
# Start the ProcOrg web interface

cd "$(dirname "$0")"

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

# Check if lock file exists
if [ -f "procorg.lock" ]; then
    echo "ProcOrg is already running. Please stop it before starting a new instance."
    exit 1
fi

# Check if port 9777 is available, otherwise use 9778
PORT=9777
if lsof -Pi :9777 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port 9777 is in use, using port 9778 instead"
    PORT=9778
fi

# Start the web server
echo "Starting ProcOrg web server on http://localhost:$PORT"
echo "Access the web interface at http://localhost:$PORT"
echo "Login with your system username and password"
echo ""
touch procorg.lock
python3 -c "from procorg.web import run_server; run_server(port=$PORT, debug=False)"
rm procorg.lock

cd -