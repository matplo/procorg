#!/bin/bash
# Example script for ProcOrg

echo "=========================================="
echo "ProcOrg Example Script"
echo "=========================================="
echo ""
echo "Starting at: $(date)"
echo "Running as user: $(whoami)"
echo "Working directory: $(pwd)"
echo ""

# Simulate some work
echo "Processing items..."
for i in {1..5}; do
    echo "  - Processing item $i/5"
    sleep 1
done

echo ""
echo "Checking system info..."
echo "  Hostname: $(hostname)"
echo "  Uptime: $(uptime)"

echo ""
echo "Script completed successfully at: $(date)"
exit 0
