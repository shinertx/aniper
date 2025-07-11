# AGENTS.md
────────────────────────────────────────────────────────
MEME-SNIPER POD - GOVERNANCE & WORKFLOW CONSTITUTION
────────────────────────────────────────────────────────

## 0. Scope
This file is **law** for all Coding/Review agents (human or LLM) operating
inside this repository.  Any PR, commit, or merge that violates AGENTS.md
**must** be auto-blocked by CI.

---

## 1. Branch & PR Discipline
| Rule | Requirement |
|------|-------------|
| **Branch naming** | `feat/<short>`, `fix/<short>`, `ops/<short>`, `sec/<short>` |
| **Commit style**  | Conventional Commits; body ≤ 72 chars/line |
| **PR template**   | Must include: _Scope_, _Linked Issue_, _Risk Summary_, _Test Plan_ |
| **Merge gate**    | All mandatory checks green **AND** manual “Approve” by Provisioner |

---

## 2. Mandatory Test Suite
| Layer | Command | Blocking? |
|-------|---------|-----------|
| Rust executor | `cargo test --all --release` | ✅ |
| Python brain  | `pytest -q`                 | ✅ |
| WASM FFI      | `cargo test -p classifier --features wasm` | ✅ |
| Replay harness| `./scripts/replay_harness.sh --dry-run --platforms all`   | ✅ |
| Lint / Format | `cargo fmt --check && ruff check src/`     | ✅ |
| Multi-platform| `./scripts/multi_platform_test.sh`         | ✅ (Tests ingest/executor for pump.fun + LetsBonk) |

CI fails if **any** exit code ≠ 0 or coverage < 85 %.

---

## 3. Red-Team / Audit Checklist (must be in PR description)
1. **Execution-path mutation?**  If yes → show latency diff < 2 ms.
2. **Key handling touched?**      If yes → paste unit test proving no private-key leak.
3. **Model update?**              Attach JS-divergence score + canary ROI ≥ baseline.
4. **Edge-decay analysis**        Demonstrate new heuristic does **not** reduce hit-rate on last 7 d data.
5. **Reg / OFAC impact**          State if new code touches compliance perimeter.
6. **Platform extension?**        If adding/modifying platforms (e.g., LetsBonk), include per-platform metrics (hit-rate, slippage) and confirm program ID integration (e.g., LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj for LetsBonk).
7. **Risk controls changed?**     If yes → attach Monte Carlo sim for ruin probability (<20%) and slippage caps (e.g., max 10% tolerance).
8. **Slippage mitigation?**      Confirm pre-trade pool reserve queries and abort logic for >10% impact.

---

## 4. Evidence & Log Output
Every PR **must attach**:
* `ci_logs.txt` — full test output.
* `bench_latency.json` — p95 before/after (executor).
* `edge_metrics.csv` — hit-rate, slippage, P&L delta on 24 h replay (per-platform if multi).
* `ruin_sim_results.json` — Monte Carlo outputs for risk model (if controls touched).

---

## 5. Manual Review Steps (Provisioner)
1. Read PR description & audit answers.
2. Download `edge_metrics.csv`; spot-check ≥ 3 trades per platform.
3. Verify slippage checks in executor code.
4. If satisfied, comment `LGTM & MERGE OK`.  
   Otherwise, comment `BLOCKED: <reason>`.

---

## 6. Architecture **Invariant Guards**
* **ARCH-BREACH** if any LLM call appears in executor path (`executor/**`).
* **ARCH-BREACH** if WASM classifier replaced by runtime Python.
* **ARCH-BREACH** if multi-platform ingest adds >5 ms latency to single-platform baseline.
* CI greps for `openai` / `async_openai` inside `executor/**` and fails.

---

## 7. Model Governance
* New `model.wasm` lands in `models/candidate/`.
* CI runs `./scripts/canary_test.sh models/candidate/model.wasm --platforms all`.
* If ROI ↑ and JS-divergence ≤ 0.25 → auto-move to `models/prod/`.
* Provisioner final sign-off required in PR.
* For implementation details of runtime LLM agents see docs/AGENTS_GUIDE.md. Platform-specific prompts (e.g., X queries for LetsBonk) must be versioned and tested for reflexivity scoring.

---

## 8. Emergency Procedures
* `make killswitch` — sets Redis `global_halt=1`; executor exits gracefully.
* Hot-fixes during halt **must** follow normal PR flow; only test suite scope
  may be reduced with `HOTFIX_OK=1`.

---

## 9. Contact Matrix
| Area | Slack Channel |
|------|---------------|
| CI fails | `#ops-ci` |
| Latency spike | `#hft-infra` |
| Security incident | `#sec-hot` |
| Platform decay (e.g., LetsBonk share drop) | `#edge-monitor` |

---

*End of AGENTS.md*
