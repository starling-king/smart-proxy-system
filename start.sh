#!/bin/bash
set -e  # Exit immediately if any command fails

# --- SAFETY: Ensure we are in the script's directory (project root) ---
cd "$(dirname "$0")"

# --- CRITICAL: Add 'backend' to Python path (Prepend is safer) ---
export PYTHONPATH="$(pwd)/backend:${PYTHONPATH}"

echo "========================================"
echo "   🚀 INITIALIZING PROXY SYSTEM "
echo "========================================"

# 1. Run the Data Setup
echo "--- [1/3] Generating Test Data ---"
python backend/setup_test_data.py
echo "✅ Data generated successfully."

# 2. Run the Test Cases
echo "--- [2/3] Running Test Suite ---"
python -m pytest backend/tests -p no:warnings
echo "✅ All tests passed."

# 3. Start the Flask Application
echo "--- [3/3] Starting Web Server ---"
echo "🌐 App is running at: http://localhost:5000"
python backend/app.py