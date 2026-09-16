#!/usr/bin/env bash
# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

# E2E Karate Integration Test Suite Runner for El Secretario

set -e

PORT_FILE="app.port"
SERVER_LOG="/tmp/karate_test_server.log"

# Smart Karate JAR discovery: use local developer, test folder, or auto-download on-the-fly
if [ -f "/home/developer/karate.jar" ]; then
    KARATE_JAR="/home/developer/karate.jar"
elif [ -f "tests/integration/karate/karate.jar" ]; then
    KARATE_JAR="tests/integration/karate/karate.jar"
else
    echo "[INFO] Karate standalone JAR not found. Downloading v1.4.1 on-the-fly..."
    mkdir -p tests/integration/karate
    curl -L -o tests/integration/karate/karate.jar https://github.com/karatelabs/karate/releases/download/v1.4.1/karate-1.4.1.jar
    KARATE_JAR="tests/integration/karate/karate.jar"
fi

# Clean up any leftover discovery file
if [ -f "$PORT_FILE" ]; then
    rm -f "$PORT_FILE"
fi

# Smart Python interpreter discovery
if [ -f "./venv/bin/python" ]; then
    PYTHON_EXEC="./venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_EXEC=".venv/bin/python"
else
    PYTHON_EXEC="python"
fi

echo "=========================================================="
echo "🚀 Starting Local REST API Test Server in background..."
echo "=========================================================="
$PYTHON_EXEC tests/integration/karate/start_test_server.py > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

# Wait for app.port to be generated
echo "Waiting for port-discovery file '$PORT_FILE' to be written..."
attempts=0
while [ ! -f "$PORT_FILE" ] && [ $attempts -lt 100 ]; do
    sleep 0.1
    attempts=$((attempts+1))
done

if [ ! -f "$PORT_FILE" ]; then
    echo "[ERROR] Failed to start test server. Log output:"
    cat "$SERVER_LOG"
    kill -9 $SERVER_PID || true
    exit 1
fi

# Parse port and token
PORT=$(grep port "$PORT_FILE" | cut -d= -f2)
TOKEN=$(grep token "$PORT_FILE" | cut -d= -f2)

echo "[INFO] Test Server successfully listening on port: $PORT"
echo "[INFO] Authorized token: $TOKEN"

echo "=========================================================="
echo "🎯 Executing Karate API Contract Tests..."
echo "=========================================================="

# Run Karate standalone JAR
set +e
java -Dkarate.config.dir=tests/integration/karate/ -DapiBaseUrl="http://127.0.0.1:$PORT/api/v1" -DapiToken="$TOKEN" -jar "$KARATE_JAR" tests/integration/karate/local-api.feature
KARATE_EXIT=$?
set -e

echo "=========================================================="
echo "🛑 Shutting down Test Server cleanly..."
echo "=========================================================="
# Force terminate the background process to completely prevent wait hangs in CI/CD pipelines
kill -9 $SERVER_PID || true

# Clean up discovery file manually since server process is force-killed
if [ -f "$PORT_FILE" ]; then
    rm -f "$PORT_FILE"
fi

echo "[INFO] Test execution completed."
if [ $KARATE_EXIT -eq 0 ]; then
    echo "🎉 SUCCESS: All Karate API Contract Tests passed perfectly!"
else
    echo "❌ FAILURE: Some Karate API Contract Tests failed (Exit Code: $KARATE_EXIT)."
fi

exit $KARATE_EXIT
