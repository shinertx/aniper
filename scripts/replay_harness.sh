#!/usr/bin/env bash
set -euo pipefail

# --- Helper Functions ---
info() {
    echo "[INFO] $1"
}

error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  info "Loading environment variables from .env file..."
  set -a # automatically export all variables
  source .env
  set +a # stop automatically exporting
fi

# Ignore SIGINT (Ctrl+C) to prevent interruptions from the environment
trap '' INT

# --- Configuration ---
MOCK_DATA_DIR="tests/data"
DEFAULT_MOCK_DATA="$MOCK_DATA_DIR/mock_data.json"

# --- Argument Parsing ---
DRY_RUN=false
PLATFORMS_ARG=""
REPLAY_FILE=""

# Handle named arguments first
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --dry-run)
        DRY_RUN=true
        shift # past argument
        ;;
        --platforms)
        PLATFORMS_ARG="$2"
        shift # past argument
        shift # past value
        ;;
        --replay-file)
        REPLAY_FILE="$2"
        shift # past argument
        shift # past value
        ;;
        *)    # unknown option, assume it's a platform name
        break
        ;;
    esac
done

if [ "$DRY_RUN" = true ]; then
    info "Dry run mode enabled."
fi

# --- Main Logic ---

# If a specific replay file is provided, use it and exit.
if [ -n "$REPLAY_FILE" ]; then
    if [ ! -f "$REPLAY_FILE" ]; then
        error "Replay file not found: $REPLAY_FILE"
    fi
    info "Executing replay with specific file: $REPLAY_FILE"
    cmd="cargo run --release --bin executor -- --replay $REPLAY_FILE"

    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN CMD: $cmd"
    else
        eval "$cmd"
    fi
    exit 0
fi

# Handle historical replay first as it's a special case
if [ "$HISTORICAL" = true ]; then
    info "Executing historical data replay..."
    historical_data_file="tests/data/historical_data.parquet"
    if [ ! -f "$historical_data_file" ]; then
        error "Historical data file not found: $historical_data_file. Please run scripts/ingest_historical_data.py first."
    fi

    info "Using historical data file: $historical_data_file"
    info "NOTE: This simulates the full historical dataset and may take a significant amount of time."

    # Assuming the executor can handle a .parquet file directly for replay
    cmd="cargo run --release --bin executor -- --replay $historical_data_file"

    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN CMD: $cmd"
    else
        eval "$cmd"
    fi
    exit 0
fi


# Function to run replay for a given platform and data file
run_replay() {
    local platform=$1
    local data_file=$2

    if [ ! -f "$data_file" ]; then
        error "Mock data file not found for platform '$platform': $data_file"
    fi

    info "Executing replay harness for platform: $platform"
    info "Using data file: $data_file"

    # The executor's replay command currently only takes a file.
    # We assume the mock data file contains platform-specific events.
    local cmd="cargo run --release --bin executor -- --replay $data_file"

    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN CMD: $cmd"
    else
        eval "$cmd"
    fi
}

# Handle --platforms all
if [[ "$PLATFORMS_ARG" == "all" ]]; then
    info "Processing --platforms all. Finding all mock data files..."
    found_files=false
    for data_file in "$MOCK_DATA_DIR"/mock_data_*.json; do
        if [ -f "$data_file" ]; then
            found_files=true
            # Extract platform name from filename (mock_data_PLATFORM.json)
            platform=$(basename "$data_file" .json | sed 's/mock_data_//')
            run_replay "$platform" "$data_file"
        fi
    done
    if [ "$found_files" = false ]; then
        error "No mock data files found matching '$MOCK_DATA_DIR/mock_data_*.json'"
    fi
    exit 0
fi

# If specific platforms are provided as arguments (e.g., ./script.sh pump.fun)
if [ "$#" -gt 0 ]; then
    info "Processing specific platforms from arguments: $@"
    for platform in "$@"; do
        platform_data_file="$MOCK_DATA_DIR/mock_data_${platform}.json"
        run_replay "$platform" "$platform_data_file"
    done
    exit 0
fi

# If no arguments, check for PLATFORMS in .env or use default
if [ -f ".env" ]; then
    # Simple parse of PLATFORMS from .env, removing quotes and splitting by comma
    PLATFORMS_ENV=$(grep -E '^PLATFORMS=' .env | cut -d '=' -f2 | tr -d '"' | tr ',' ' ')
fi

if [ -n "${PLATFORMS_ENV:-}" ]; then
    info "Found platforms in .env: $PLATFORMS_ENV"
    for platform in $PLATFORMS_ENV; do
        platform_data_file="$MOCK_DATA_DIR/mock_data_${platform}.json"
        if [ -f "$platform_data_file" ]; then
            run_replay "$platform" "$platform_data_file"
        else
            info "Skipping replay for '$platform': mock data file not found at $platform_data_file"
        fi
    done
else
    info "No platforms specified and PLATFORMS not found in .env. Using default mock data."
    if [ -f "$DEFAULT_MOCK_DATA" ]; then
        run_replay "default" "$DEFAULT_MOCK_DATA"
    else
        error "Default mock data file not found: $DEFAULT_MOCK_DATA"
    fi
fi

info "Replay harness finished."
