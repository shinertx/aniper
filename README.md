# Aniper - High-Frequency Memecoin Sniper

---

## 1 | Executive Summary

Aniper is a latency-optimized, agent-powered system for sniping first-block memecoin launches on Solana. It is designed for high performance, modularity, and robust risk management.

- **Multi-Platform:** Natively supports both **pump.fun** and **LetsBonk** platforms out-of-the-box.
- **Rust Executor:** Ultra-fast, multi-threaded trading engine built with Tokio for concurrent, non-blocking I/O.
- **WASM Classifier:** Nightly-retrained model for hot-swappable, sub-millisecond scoring of potential trades.
- **Python Agent Layer:** LLM-driven agents for feature mining, narrative analysis, and continuous performance coaching.
- **Dockerized:** Turnkey deployment with Docker Compose.
- **Zero LLM calls in the latency path.** All models, guardrails, and kill-switches are enforced in-process by the Rust executor.

---

## 2 | Repo Structure

```
.
├── executor/         # Rust trading engine (core loop)
│   └── Dockerfile    # Executor Docker image
├── brain/            # Python LLM agent suite (logic/cron)
│   └── Dockerfile    # Brain/agent Docker image
├── scripts/          # replay_harness.sh, and other utility scripts
├── AGENTS.md         # Contributor governance and workflow constitution
├── docker-compose.yml # Main Docker Compose file
├── prometheus.yml    # Prometheus configuration
├── .env              # Local environment configuration (gitignored)
```

---

## 3 | Quick Start with Docker Compose

This project is optimized for a Docker-first workflow.

### **Prerequisites**
- Docker & Docker Compose
- `git`
- A Solana keypair file (e.g., `~/.config/solana/id.json`)

### **Steps**

**1. Clone the repository:**
```bash
git clone https://github.com/<your-org>/aniper.git
cd aniper
```

**2. Create your environment file:**
Copy the example environment file and fill in your details.
```bash
cp .env.example .env
nano .env
```
> **Important:** You must set `HOST_KEYPAIR_PATH` to the absolute path of your Solana wallet file on your host machine. This file is securely mounted into the executor container.

**3. Build and run the stack:**
```bash
docker-compose up --build -d
```
This command will:
- Build the `executor` and `brain` images.
- Start Redis, Prometheus, the executor, and the brain services.
- Mount your wallet read-only into the executor.

**4. Monitor the system:**
- **Logs:** `docker-compose logs -f executor brain`
- **Metrics:** Open Grafana or Prometheus and point it to `http://localhost:9090`.

---

## 4 | Configuration

All configuration is managed via environment variables in the `.env` file.

### **Core Configuration**
| Variable | Description | Example |
|---|---|---|
| `SOLANA_RPC_URL` | Primary Solana RPC endpoint (WebSocket). | `wss://api.mainnet-beta.solana.com` |
| `HELIUS_API_KEY` | Helius API key for enhanced data. | `your-helius-key` |
| `REDIS_URL` | Redis connection string. | `redis://aniper-redis:6379` |
| `HOST_KEYPAIR_PATH`| **Absolute path** to your Solana keypair on the host. | `/home/user/.config/solana/id.json` |
| `PLATFORMS` | Comma-separated list of platforms to snipe. | `pump.fun,LetsBonk` |

### **Risk Management & Trading**
| Variable | Description | Example |
|---|---|---|
| `POSITION_SIZE_PERCENT` | Percent of total portfolio value to allocate per trade. | `2.5` |
| `LIQUIDITY_THRESHOLD` | Minimum USD liquidity a token must have to be considered. | `5000` |
| `AUTO_SELL_PROFIT_MULTIPLIER` | Profit target to trigger auto-sell (e.g., 2.0 = 100% profit). | `2.0` |
| `AUTO_SELL_LOSS_PERCENT` | Loss percentage to trigger auto-sell (stop-loss). | `40.0` |
| `PORTFOLIO_STOP_LOSS_PERCENT` | Max percentage of portfolio drawdown before halting all trades. | `15.0` |

### **Platform Program IDs**
| Variable | Description |
|---|---|
| `PUMPFUN_PROGRAM_ID` | The on-chain program ID for pump.fun. |
| `LETSBONK_PROGRAM_ID` | The on-chain program ID for LetsBonk. |

---

## 5 | Backtesting

The `replay_harness.sh` script provides a powerful way to backtest the system against historical data. It reads the `PLATFORMS` variable from your `.env` file and runs a replay for each configured platform.

**Usage:**
```bash
# Ensure your .env file is configured correctly
./scripts/replay_harness.sh
```

The script uses mock data files located in `tests/data/` (e.g., `mock_data_pumpfun.json`). You can replace these with your own datasets for comprehensive testing.








