import io
import json
import os
from pathlib import Path

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import importlib
import sys

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
FEATURE_STORE = ROOT / "feature_store.parquet"
MODEL_PATH = ROOT / "models" / "candidate" / "model.wasm"


def make_mock_feature_store(n_rows: int = 1000):
    rng = np.random.default_rng(42)
    now = pd.Timestamp.utcnow().timestamp()
    ts = now - rng.uniform(0, 60 * 60 * 24 * 30, size=n_rows)  # within 30 d
    df = pd.DataFrame({
        "timestamp": ts,
        "holders": rng.integers(10, 500, size=n_rows),
        "lp": rng.random(n_rows),
        "roi": rng.uniform(0, 20, size=n_rows),
    })
    df.to_parquet(FEATURE_STORE)


# ---------------------------------------------------------------------------
# Tests ---------------------------------------------------------------------
# ---------------------------------------------------------------------------

def test_heuristic_agent_builds_model(tmp_path, monkeypatch):
    # Work inside isolated tmp dir.
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Replicate repo layout.
        (tmp_path / "models" / "candidate").mkdir(parents=True, exist_ok=True)
        make_mock_feature_store()

        # Ensure brain package can be imported from src checkout.
        sys.path.insert(0, str(ROOT))
        agent_mod = importlib.import_module("brain.agents.heuristic_agent")

        buf = io.StringIO()
        monkeypatch.setattr(agent_mod, "FEATURE_STORE", str(FEATURE_STORE))
        monkeypatch.setattr(agent_mod, "MODEL_DIR", str(Path("models/candidate")))
        monkeypatch.setattr(agent_mod, "MODEL_PATH", str(Path("models/candidate/model.wasm")))

        # Replace train_model with stub to avoid heavy LightGBM install in CI.
        def fake_train(df, y):
            class _Dummy:
                pass
            return _Dummy(), ["holders", "lp"]

        monkeypatch.setattr(agent_mod, "train_model", fake_train)

        # Monkey-patch exporter to emit tiny file.
        def fake_export(model, feats):
            p = Path("models/candidate/model.wasm")
            with open(p, "wb") as f:
                f.write(b"wasm_stub")
            return p

        monkeypatch.setattr(agent_mod, "export_model", fake_export)

        # Run main.
        monkeypatch.setattr(sys, "stdout", buf)
        agent_mod.main()

        # Parse manifest.
        manifest = json.loads(buf.getvalue())
        assert set(manifest.keys()) == {"sha256", "features"}

        model_path = Path("models/candidate/model.wasm")
        assert model_path.exists()
        # File size ≤ 1 MiB.
        assert model_path.stat().st_size <= 1 * 1024 * 1024
        # SHA matches actual file.
        import hashlib
        h = hashlib.sha256()
        with open(model_path, "rb") as f:
            h.update(f.read())
        assert manifest["sha256"] == h.hexdigest()
    finally:
        os.chdir(cwd) 