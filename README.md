# README.md
────────────────────────────────────────────────────────
MEME-SNIPER POD — Turn \$1 000 → \$50 000 in 7 Days
────────────────────────────────────────────────────────

## 1 | Executive Summary
First-minute sniping of Solana/Base memecoin launches using:
* **Rust executor** (sub-slot latency, multi-RPC broadcast)
* **WASM micro-classifier** (offline-trained, in-memory scoring)
* **LLM "brain" agents** (feature mining, narrative scoring, red-team)
* **GCP stack** (GKE Autopilot, Cloud Build, Secret Manager, CloudSQL)

Architecture guarantees **zero LLM calls in the micro-latency path**.

---

## 2 | Repo Structure
.
├── executor/ # Rust HFT engine
├── brain/ # Python agents (LLM calls)
├── models/ # model.wasm (prod / candidate)
├── infra/
│ ├── terraform/ # GCP IaC
│ └── k8s/ # GKE manifests
├── shared/ # Protobuf, schemas, utils
├── scripts/ # replay_harness, canary_test
├── docs/ # PROMPTS.md, ARCHITECTURE.md
└── AGENTS.md # Workflow constitution

bash
Copy
Edit

---

## 3 | Quick Start (GCP Provisioner Only)

```bash
# clone and cd
git clone https://github.com/<you>/meme-sniper.git && cd meme-sniper

# set env (replace placeholders)
export GCP_PROJECT_ID="meme-snipe-01"
export STATIC_IP="35.235.x.x"
export KMS_KEY_RING="sniper-ring"
export KMS_KEY="sniper-key"
export WALLET_CSV_PATH="gs://${GCP_PROJECT_ID}-secrets/wallets.csv"
export REDIS_URL="redis://:password@host:6379/0"
export METRICS_BIND="127.0.0.1:9184"

# bootstrap infra
gcloud auth login
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform apply \
  -var="project_id=${GCP_PROJECT_ID}" \
  -var="exec_static_ip=${STATIC_IP}" \
  -var="kms_key_ring=${KMS_KEY_RING}" \
  -var="kms_key=${KMS_KEY}" \
  -var="wallet_csv_path=${WALLET_CSV_PATH}"
CI/CD pipeline in Cloud Build auto-deploys to GKE after every merge.

4 | Operational Playbook
Phase	Goal	Trigger
Shadow	P&L ≥ -$20 on 1 000 replay trades	Post-deploy
Canary	Live size $5, equity floor $950	Shadow pass
Ramp	Ticket $50, equity floor $300	Canary ROI ≥ 0
Scale	Cross-chain (Base) enabled	Week 2

Use make killswitch to halt instantly.

5 | Telemetry
Prometheus scrape /metrics from executor.
Set `METRICS_BIND` to control the listening address (default `127.0.0.1:9184`).

Key Prometheus counters now exported:

* `killswitch_total{kind="equity_floor|slippage"}` – counts forced shutdowns by guard kind.
* `restarts_total` – monotonically tracks executor (re)starts across pod restarts.

Grafana dashboard dashboards/latency.json.

Cloud Monitoring alerts: p95 > 600 ms, equity < $350, slippage > 5 %.

6 | Security Controls
HSM-backed hot wallets (Cloud KMS).

Nightly key rotation (see scripts/rotate_keys.sh).
└── AGENTS.md            # Workflow constitution
+    docs/AGENTS_GUIDE.md # LLM agent design & guardrails


Supply-chain scan: cargo deny + pip-audit in CI.

Secrets stored only in GCP Secret Manager; never in ENV at runtime.

7 | Model Lifecycle
Brain trains LightGBM nightly → models/candidate/model.wasm.

canary_test.sh replay last 24 h; if ROI ↑ and JS-Div ≤ 0.25 → PR raised.

Provisioner reviews edge_metrics.csv, then merges → promotion to prod.

8 | Contribution Guide
Read AGENTS.md first—merges are impossible without compliance.

Fork → feature branch → PR.

Attach logs & evidence artefacts; wait for Provisioner approval.

9 | License
MIT for code; models and prompts CC-BY-NC-4.0.

10 | Contact
Ops/PagerDuty: ops@meme-sniper.xyz

Security: security@meme-sniper.xyz

End of README.md

yaml
Copy
Edit

---

### Complexity & Confidence  
*Task complexity:* **Medium** (pure documentation).  
*Confidence:* **0.93** – aligns exactly with all earlier specs and Codex-agent workflow guidance.

2/2








