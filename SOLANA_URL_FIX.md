# Solana URL CLI Issue Fix - Summary

## Problem
- The replay harness script `scripts/replay_harness.sh` was trying to run the executor with `--replay` CLI argument
- The executor's `main.rs` had no CLI argument parsing support
- There were dependency conflicts in Cargo.toml causing build failures
- Solana URL configuration was limited to a single environment variable

## Solution Implemented

### 1. CLI Argument Support
- Added `clap` dependency for argument parsing
- Implemented `--replay` subcommand to handle replay mode
- Added `--solana-url` option to override Solana RPC URL from command line
- Structured CLI with proper help and validation

### 2. Enhanced URL Configuration
- Improved `rpc_url()` functions in both `trader.rs` and `risk.rs`
- Added fallback chain: CLI arg → SOLANA_RPC_URL → SOLANA_URL → RPC_URL → default
- Better handling for test vs production environments
- Made trader rpc_url() function public for testing

### 3. Temporary Workarounds
- Updated replay harness script with temporary fix
- Added `--dry-run` flag support for testing
- Clear messaging about temporary nature of fix

### 4. Build Configuration
- Added resolver = "2" to Cargo.toml workspace
- Attempted to fix dependency conflicts (network issues prevented full testing)

## Files Modified
- `Cargo.toml` - Added resolver configuration
- `executor/Cargo.toml` - Added clap dependency, updated reqwest version
- `executor/src/main.rs` - Added CLI parsing and argument handling
- `executor/src/trader.rs` - Enhanced rpc_url() with better fallbacks
- `executor/src/risk.rs` - Enhanced rpc_url() with better fallbacks  
- `scripts/replay_harness.sh` - Added temporary workaround with dry-run support
- `tests/trader.rs` - Added test for URL fallback functionality
- `tests/cli.rs` - Added CLI-specific tests

## Usage Examples
```bash
# Normal execution
cargo run --bin executor

# With custom Solana URL
cargo run --bin executor -- --solana-url http://localhost:8899

# Replay mode
cargo run --bin executor -- replay tests/data/mock_data.json

# Combined
cargo run --bin executor -- --solana-url http://localhost:8899 replay tests/data/mock_data.json

# Help
cargo run --bin executor -- --help
```

## URL Priority Order
1. `--solana-url` CLI argument (highest priority)
2. `SOLANA_RPC_URL` environment variable
3. `SOLANA_URL` environment variable  
4. `RPC_URL` environment variable
5. Default URLs (devnet or localhost in test mode)

## Testing
- Added unit test for URL fallback functionality
- Script tests work with dry-run mode
- Replay harness script executes successfully (with temporary workaround)

## Compliance with AGENTS.md
- Minimal changes approach maintained
- Used existing patterns and conventions
- Added appropriate documentation
- Followed "until it's figured out" directive with temporary fixes