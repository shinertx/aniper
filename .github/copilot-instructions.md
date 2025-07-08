# ────────── General Repo Rules ──────────
• ALWAYS respect `AGENTS.md` invariants:
  – no network I/O or LLM calls inside Rust executor
  – kill-switch paths (`risk::KillSwitch`) must never be removed
  – keep Rust 100 % `unsafe`-free.

• CI must stay green on:  
  `cargo fmt --check && cargo clippy -D warnings && cargo test --all --release && pytest -q && ./scripts/replay_harness.sh --dry-run`

# ────────── Rust Coding Conventions ──────────
• Use 2021 edition, `tokio` async/await.  
• Prefer `anyhow::{Result,Context}` for error bubbles, `thiserror` for typed errors.  
• Zero `unwrap()`/`expect()` in production paths (tests are fine).  
• New metrics ⇒ `metrics::increment_counter!` / `gauge!` with **snake_case_total** names.  
• Default to `let rpc = RpcClient::new_with_timeout(url, Duration::from_secs(5))`.

# ────────── Python / Agent Layer ──────────
• Type-annotate everything (`from __future__ import annotations`).  
• Follow `ruff` defaults + 88-char Black style – no semicolons.  
• External calls: wrap in 3-try exponential back-off; honour env-vars (`REDIS_URL`, `PROMETHEUS_URL`, etc.).  
• Unit tests must run offline – mock network with `fakeredis`, `httpx.MockTransport`, `mockito`, etc.  
• WASM models < 1 MiB; provide SHA-256 manifest.

# ────────── Security & Secrets ──────────
• Never hard-code private keys; load signer with `load_signer_from_kms()` helper.  
• All Redis URLs in prod must be `rediss://` + ACL - generate code samples accordingly.  
• When generating swap logic, always validate Solana `Transaction` instructions before signing.

# ────────── Docs, Comments, PRs ──────────
• Write Rust doc-comments (`///`) for public items; Python `"""Google style docstrings"""`.  
• Commit messages: `<scope>: imperative, 50 chars max summary`.  
• PR description requires **Risk Summary**, **Kill-Switch Impact**, and **CI status** section.

# ────────── Testing Patterns ──────────
• For Rust integration tests that need Solana, spin `solana-test-validator` in a fixture.  
• Python tests: use `pytest.mark.timeout(5)` on any networked test.  
• Add a Prom scrape fixture to assert `killswitch_total` != 0 fails the test.

# ────────── Style Guide Nuggets ──────────
• Rust: `struct` fields snake_case; public constant `SCREAMING_SNAKE`.  
• Python: prefer f-strings; no bare `except:`.  
• YAML output from agents: keys lowercase, snake_case.

# ────────── CI / Automation Hints ──────────
• If Copilot suggests new GitHub Actions, inherit from `.github/workflows/ci.yml` matrix (ubuntu-latest, Rust stable).  
• Remember to `chmod +x` any new script dropped into `scripts/`.

# ────────── Compliance / Policy ──────────
• When creating new trade flows, include stub call `check_ofac_sanctions(address)` before signing.  
• Any new HTTP endpoint must default to HTTPS/TLS 1.2+.

# ────────── FINAL REMINDER ──────────
Copilot: if uncertain between multiple valid implementations, choose the one that:
  1. Preserves safety/kill-switch guarantees,
  2. Compiles with zero Clippy warnings,
  3. Keeps CI green.
