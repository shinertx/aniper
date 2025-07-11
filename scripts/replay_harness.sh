#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
# Default mock data file if no platform is specified
DEFAULT_MOCK_DATA="tests/data/mock_data.json"

# --- Helper Functions ---
info() {
    echo "[INFO] $1"
}

error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# --- Main Logic ---

# Check for --dry-run flag
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    shift # remove --dry-run from arguments
    info "Dry run mode enabled."
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

# If arguments are provided, treat them as platforms to replay
if [ "$#" -gt 0 ]; then
    for platform in "$@"; do
        platform_data_file="tests/data/mock_data_${platform}.json"
        run_replay "$platform" "$platform_data_file"
    done
    exit 0
fi

# If no arguments, check for PLATFORMS in .env or use default
if [ -f ".env" ]; then
    # Simple parse of PLATFORMS from .env, removing quotes and splitting by comma
    PLATFORMS=$(grep -E '^PLATFORMS=' .env | cut -d '=' -f2 | tr -d '"' | tr ',' ' ')
fi

if [ -n "${PLATFORMS:-}" ]; then
    info "Found platforms in .env: $PLATFORMS"
    for platform in $PLATFORMS; do
        platform_data_file="tests/data/mock_data_${platform}.json"
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
