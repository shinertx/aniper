#!/usr/bin/env bash
set -euo pipefail
cargo run --release --bin executor -- --replay mock_data.json 