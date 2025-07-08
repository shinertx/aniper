#!/usr/bin/env bash
set -euo pipefail
cargo run --release --bin executor -- --replay tests/data/mock_data.json
