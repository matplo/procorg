#!/bin/bash
# Example script that demonstrates error handling

echo "This script will generate some errors..."
sleep 1

echo "Writing to stdout: This is normal output"
echo "Writing to stderr: This is an error!" >&2

sleep 1

echo "Attempting something that might fail..."
echo "ERROR: Something went wrong!" >&2

exit 1
