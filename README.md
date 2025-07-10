# MEME-SNIPER POD — $1,000 → $50,000 IN 7 DAYS

---

## 1 | Executive Summary

Meme-Sniper Pod is a latency-optimized, agent-powered system for sniping first-block Solana/Base memecoin launches.

- **Rust executor:** Ultra-fast, sub-slot, multi-RPC trading engine.
- **WASM classifier:** Nightly-retrained model (hot-swappable, <1ms scoring).
- **Python agent layer:** LLM-driven (feature miner, narrative, red-team, coach).
- **Deployment:** Runs on any Linux VM, server, or Docker—**no Kubernetes or Terraform required**.
- **Zero LLM calls in the latency path.**  
  All models, guardrails, and kill-switches are enforced in-process.

---

## 2 | Repo Structure

```
.
├── executor/         # Rust trading engine (core loop)
│   └── Dockerfile    # Executor Docker image
├── brain/            # Python LLM agent suite (logic/cron)
│   └── Dockerfile    # Brain/agent Docker image
├── models/           # WASM model artifacts (auto-created)
├── scripts/          # replay_harness, canary_test, rotate_keys.sh
├── docs/             # PROMPTS.md, AGENTS_GUIDE.md, run-books
├── AGENTS.md         # Workflow, testing, and audit constitution
├── .github/          # Copilot/CI configs
├── infra/ (optional) # terraform/, k8s/ for advanced infra (optional)
````
> **Note:**  
> `models/` is created automatically by the training agent if missing.  
> `infra/` is only for users who want advanced IaC or Kubernetes.

---

## 3 | Quick Start — Manual/Single-VM/Docker

### **Option A: Native (VM/Bare Metal)**
```bash
# 1. Install dependencies (Ubuntu 22.04 recommended)
sudo apt-get update && sudo apt-get install -y build-essential python3.11 python3.11-venv redis-server

# 2. Clone and build
git clone https://github.com/<your-org>/meme-sniper.git && cd meme-sniper
cd executor && cargo build --release

# 3. Prepare environment variables
cp .env.example .env
nano .env  # fill in all required API keys, RPC URLs, Redis URL, key paths

# 4. Start Redis (localhost bind, password in redis.conf)
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 5. Start executor
source ../.env
./target/release/executor

# 6. Start Python agent manager
cd ../brain
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
source ../.env
python -m brain.manager
````

---

### **Option B: Docker / Docker Compose (Recommended for Most Teams)**

#### 1. Build Docker images

```bash
# In repo root; note corrected Dockerfile paths!
docker build -t meme-executor -f executor/Dockerfile ./executor
docker build -t meme-brain -f brain/Dockerfile ./brain
```

#### 2. Start Redis in Docker (secure, localhost only)

```bash
docker run -d --name redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD=yourpassword \
  redis:alpine --requirepass yourpassword --bind 127.0.0.1
```

> On Mac/Windows, `--network host` may not be available. Use Docker Compose’s bridge network and adjust `REDIS_URL` as needed.

#### 3. Run executor and agents

```bash
docker run --env-file .env --network host meme-executor
docker run --env-file .env --network host meme-brain
```

> On non-Linux, prefer Docker Compose for networking.

#### 4. (Optional) Use Docker Compose for one-command up

```yaml
# docker-compose.yml
version: "3"
services:
  redis:
    image: redis:alpine
    command: ["redis-server", "--requirepass", "yourpassword", "--bind", "0.0.0.0"]
    ports: ["6379:6379"]
  executor:
    build: ./executor
    env_file: .env
    depends_on: [redis]
    ports: ["9184:9184"]  # Exposes metrics, adjust as needed
  brain:
    build: ./brain
    env_file: .env
    depends_on: [redis]
```

```bash
docker compose up --build
```

---

## 4 | Security & Environment

* **Signer key:** Use `load_signer_from_kms()` or securely load a local key (`chmod 600`). Never hard-code keys in images/scripts.
* **Redis:** Must be password protected. Never expose to public internet. Use localhost bind unless behind a VPN/firewall.
* **Prometheus metrics:** Exported by the executor (`/metrics`, default `127.0.0.1:9184`). Expose only as needed; firewall/VPN strongly recommended.
* **OFAC screening:** Compliance checks enforced before swaps (see AGENTS.md).
* **No secrets in repo:** Always load from `.env` (not committed).
* **.env.example** is provided—**keep it up to date** with all required variables.

---

## 5 | Agent & Model Lifecycle

* **Heuristic agent:** Trains LightGBM nightly, exports WASM under `models/candidate/model.wasm` (folder auto-created).
* **LLM agents (brain/):** Narrative, red-team, coach—cron-managed, publish artifacts to Redis.
* **Model governance:** Canary tests, manifest SHA, merge-gate and manual sign-off.

---

## 6 | Operational Playbook

| Phase  | Goal                            | How to run/test                |
| ------ | ------------------------------- | ------------------------------ |
| Shadow | P&L ≥ -$20 on 1,000 replay      | `./scripts/replay_harness.sh`  |
| Canary | Live $5 trades, equity $950     | Manual run with small bankroll |
| Ramp   | Ticket $50, equity $300         | Once canary ROI ≥ 0            |
| Scale  | Add cross-chain/base (optional) | After week 1, if desired       |

* Use `make killswitch` or set `global_halt=1` in Redis to halt instantly.

---

## 7 | Monitoring & Metrics

* **Prometheus:** Scrapes `/metrics` from the **executor** service (see `METRICS_BIND`).
* **Key metrics:** `killswitch_total`, `restarts_total`, `risk_equity_usdc`, `risk_last_slippage`.
* **Alerting:** Trigger on kill-switch activation, equity < $350, or slippage > 5%.
* **Grafana dashboards:** in `docs/dashboards/latency.json`.

---

## 8 | CI/CD & Testing

* All PRs require passing:

  * `cargo fmt --check`
  * `cargo clippy --all-targets --all-features -- -D warnings`
  * `cargo test --all --release`
  * `pytest -q`
  * `./scripts/replay_harness.sh --dry-run`
* All merges require Provisioner sign-off.

---

## 9 | Contribution Guide

* Read `AGENTS.md` and `docs/AGENTS_GUIDE.md` before changes.
* Fork → feature branch → PR (with tests).
* All code/docs must match `.github/copilot-instructions.md`.
* Commit messages: `<scope>: imperative, ≤50 chars summary`.

---

## 10 | License

MIT for code; models and prompts CC-BY-NC-4.0.

---

## 11 | Contact

* **Ops:** [ops@meme-sniper.xyz](mailto:ops@meme-sniper.xyz)
* **Security:** [security@meme-sniper.xyz](mailto:security@meme-sniper.xyz)

---

**No Kubernetes, GKE, or Terraform is required.**
Deploy securely and with full edge on any VM or Docker host.

For advanced automation or HA, see `infra/` (optional).

---

## Running Brain (Python Agent) Tests

To verify the Python agent logic and guardrails:

### A) Local (development)
```bash
cd brain                                # enter agent directory
python3 -m venv .venv                   # create virtualenv
source .venv/bin/activate               # activate environment
pip install -r requirements.txt pytest  # install dependencies + test runner
pytest -q                               # run all agent tests
```

### B) In Docker (test mode)
```bash
# Build production image
docker build -t meme-brain -f brain/Dockerfile brain
# Run tests without modifying Dockerfile by installing pytest at runtime
docker run --rm meme-brain bash -lc "pip install pytest && pytest -q"
```








