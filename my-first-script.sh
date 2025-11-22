#!/bin/bash
# My first ProcOrg script

echo "Hello from my first script!"
echo "Running at: $(date)"
echo "User: $(whoami)"
echo ""

# Do some work
for i in 1 2 3; do
    echo "Step $i of 3"
    sleep 1
done

echo ""
echo "Script completed successfully!"
