# AGENTS GUIDE — Fully Autonomous Intelligence Layer

*(Derived from "A Practical Guide to Building Agents" and tailored to the Meme‑Sniper Pod)*

---

## 0  Purpose

This guide codifies how every LLM‑powered **agent** in the repo must be designed, instrumented, and deployed.  It operationalises the brain/reflex split: all agents live **outside** the low‑latency path and deliver artifacts (WASM, JSON, YAML) that the Rust executor consumes.

---

## 1  Agent Catalog (v0.1)

| Agent Name              | Role                                                | Cadence   | Outputs                      | Owner             |
| ----------------------- | --------------------------------------------------- | --------- | ---------------------------- | ----------------- |
| **Heuristic‑Discovery** | Mine new survival features, produce LightGBM → WASM | Nightly   | `model.wasm`, `filters.json` | Quant Strategist  |
| **Narrative‑Engine**    | Score emergent metas via social/chain data          | 10 min    | `narrative_scores.json`      | Narrative Analyst |
| **Red‑Team**            | Propose new attack vectors, patch guard rules       | 6 h       | `guard_patches.yaml`         | Security Lead     |
| **Performance‑Coach**   | Tune pad weights, ticket size via metrics           | 15–30 min | `risk_patch.yaml`            | Risk Officer      |
| **SRE Bot**             | Health probes, kill‑switch trigger                  | 1 min     | Alerts (Slack/Email)         | Infra Engineer    |

> **Note:** Agents can call sub‑agents as tools but **must** respect the guardrails below.

---

## 2  Agent Design Foundations

### 2.1  Model Selection

* Use **GPT‑4o‑32k** for discovery/red‑team tasks; **gpt‑3.5‑turbo** for performance coach.
* Finite‑context tasks → smaller models to reduce cost; switch only after benchmark parity.

### 2.2  Tools

* **`sql_runner`** – query DuckDB feature store.
* **`wasm_exporter`** – compile LightGBM/ONNX to `wasm32-unknown-unknown`.
* **`prometheus_reader`** – fetch recent metrics snapshot.
* **`redis_writer`** – push JSON/YAML to `config_updates` channel.
* **`slack_alert`** – send message to `#ops-ai`.

### 2.3  Instructions Template

```yaml
You are {{role}}. Follow AGENTS_GUIDE guardrails.
Goal: {{task}}.
Required output schema: {{schema}}.
If preconditions fail, output JSON `{"status":"abort","reason":<string>}`.
```

---

## 3  Orchestration Pattern

* **Manager Agent (`brain/manager.py`)** dispatches tasks on cron schedule.
* Sub‑agents registered via `as_tool()`; manager retries failed calls ≤ 3×.
* Outputs written to Redis, versioned by SHA‑256 hash; executor watches for hash changes.

---

## 4  Guardrails

1. **Schema Validation:** every agent response parsed with `pydantic`; invalid → retry once.
2. **Latency Cap:** soft 120 s per call; if hit, manager downgrades model next run.
3. **Content Safety:** OpenAI moderation on text; block if `block` flag true.
4. **Determinism:** Agents may **not** call random functions; use seed passed from manager.
5. **No self‑modifying prompts.** Prompt text loaded from version‑controlled `docs/PROMPTS.md`.
6. **Compliance Fence:** Red‑Team agent scans outputs for restricted jurisdictions before Redis write.

---

## 5  Sample Prompts

### 5.1  Heuristic‑Discovery Agent

```python
SYSTEM: You are Quant Strategist. Ingest `launches.parquet` and `pnl.parquet`.
TASK: Produce top‑10 boolean/numeric features predicting ≥10× ROI.
OUTPUT: JSON {"features": [...], "lightgbm_params": {...}, "rust_code": "<string>"}
GUARDRAILS: max 60 s, JSON schema enforced.
```

### 5.2  Narrative‑Engine Agent

```python
SYSTEM: You monitor social sentiment.
TASK: Score narratives (cat, dog, political, retro) 0‑1 using last 10 min tweets.
OUTPUT: {"cat": 0.85, "dog": 0.45, ...}
```

---

## 6  Autonomy & Human‑in‑loop

* **Canary Stage:** manager routes 10 % flow with new `model.wasm`; if ROI ↑ & latency OK → promote.
* **Provisioner Approval:** model promotion PR automatically generated; merges only after Provisioner’s LGTM.

---

## 7  Failure Handling

* If an agent returns `{"status":"abort"}` manager logs and skips promotion.
* 3 consecutive aborts → Slack `#ops-ai` pager.
* Executor kill‑switch unaffected; independent risk layer.

---

## 8  Versioning

* Agent code in `brain/agents/`; prompts in `docs/PROMPTS.md`.
* Any prompt change requires PR with `prompt_diff.md` showing side‑by‑side before/after.

---

## 9  References

Derived from *A Practical Guide to Building Agents* (OpenAI, 2025‑05) — sections: Design Foundations, Guardrails, Orchestration.

---

*End of AGENTS GUIDE*
