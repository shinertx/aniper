#!/usr/bin/env bash
# Demo script showing how to use the executor CLI with different Solana URLs

echo "=== Executor CLI Demo ==="
echo

echo "1. Normal execution (uses default devnet URL):"
echo "   cargo run --bin executor"
echo

echo "2. With custom Solana URL via environment variable:"
echo "   SOLANA_RPC_URL=http://localhost:8899 cargo run --bin executor"
echo

echo "3. With custom Solana URL via CLI argument:"
echo "   cargo run --bin executor -- --solana-url http://localhost:8899"
echo

echo "4. Replay mode with custom URL:"
echo "   cargo run --bin executor -- --solana-url http://localhost:8899 replay tests/data/mock_data.json"
echo

echo "5. Show help:"
echo "   cargo run --bin executor -- --help"
echo

echo "=== URL Fallback Chain ==="
echo "1. --solana-url CLI argument (highest priority)"
echo "2. SOLANA_RPC_URL environment variable"
echo "3. SOLANA_URL environment variable"
echo "4. RPC_URL environment variable"
echo "5. Default: https://api.devnet.solana.com (or http://127.0.0.1:8899 in test mode)"