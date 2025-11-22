#!/bin/bash
# Test script for web registration

echo "Web Registration Test Script"
echo "=============================="
echo "Started at: $(date)"
echo "This is a test process registered via the web UI"

for i in {1..3}; do
    echo "Iteration $i/3"
    sleep 1
done

echo "Test completed successfully!"
exit 0
