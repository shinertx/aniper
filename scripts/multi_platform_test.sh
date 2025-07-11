#!/bin/bash
#
# multi_platform_test.sh
#
# Verifies that the executor can correctly ingest and process data from multiple
# platforms (pump.fun and LetsBonk) simultaneously as per AGENTS.md.
#
# This test performs the following steps:
# 1. Sets up a clean environment, forcing the PLATFORMS variable.
# 2. Runs the full replay harness against mock data for both platforms.
# 3. Greps the executor logs for confirmation that trades from BOTH platforms
#    were processed.
# 4. Tears down the environment.
# 5. Exits with a success (0) or failure (1) code.
#

set -e
set -o pipefail

# --- Configuration ---
LOG_FILE="/tmp/multi_platform_test_output.log"
PUMPFUN_CONFIRMATION="Processing trade signal for platform: pump.fun"
LETSBONK_CONFIRMATION="Processing trade signal for platform: LetsBonk"

# --- Test Start ---
echo "🚀 Starting multi-platform integration test..."
echo "   Logs will be streamed to $LOG_FILE"

# Ensure we are in the project root
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: This script must be run from the project root."
    exit 1
fi

# Force PLATFORMS to be set for the test run
export PLATFORMS="pump.fun,LetsBonk"
echo "   - Overriding PLATFORMS to: $PLATFORMS"

# Run the replay harness and capture all output
echo "   - Running replay harness..."
./scripts/replay_harness.sh > "$LOG_FILE" 2>&1

echo "   - Replay finished. Analyzing logs..."

# --- Verification ---
# Check for pump.fun confirmation message
if grep -q "$PUMPFUN_CONFIRMATION" "$LOG_FILE"; then
    echo "✅ pump.fun: Trade processing confirmed."
else
    echo "❌ pump.fun: FAILED. No trade processing message found in logs."
    echo "--- Full Log Output ---"
    cat "$LOG_FILE"
    echo "-----------------------"
    exit 1
fi

# Check for LetsBonk confirmation message
if grep -q "$LETSBONK_CONFIRMATION" "$LOG_FILE"; then
    echo "✅ LetsBonk: Trade processing confirmed."
else
    echo "❌ LetsBonk: FAILED. No trade processing message found in logs."
    echo "--- Full Log Output ---"
    cat "$LOG_FILE"
    echo "-----------------------"
    exit 1
fi

# --- Cleanup ---
rm "$LOG_FILE"
echo "🎉 Test PASSED. Both platforms were processed successfully."
exit 0
