#!/bin/bash
set -e

echo "Running tests..."
./run_with_test.sh

echo "Checking for orphaned records..."
./venv/bin/python check_orphans.py

echo "Verification pipeline completed successfully!"
