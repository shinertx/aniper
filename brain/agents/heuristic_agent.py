import json
import os
import sys
import hashlib
from datetime import datetime, timedelta

import pandas as pd  # type: ignore

# LightGBM may be absent in minimal CI environment; provide stub so unit tests
# can run (train_model is monkey-patched in tests).
try:
    import lightgbm as lgb  # type: ignore
except ImportError:  # pragma: no cover
    class _LGBStub:  # noqa: D401
        def Dataset(*_a, **_k):  # type: ignore
            raise RuntimeError("LightGBM not available in runtime")

        def train(*_a, **_k):  # type: ignore
            raise RuntimeError("LightGBM not available in runtime")

    lgb = _LGBStub()  # type: ignore

# The wasm_exporter package is expected to be available in the runtime.  The stub
# import allows unit-tests to monkey-patch a minimal API during CI.
try:
    from wasm_exporter import export_model  # type: ignore
except ImportError:  # pragma: no cover
    def export_model(model, feature_names):  # noqa: D401
        """Fallback no-op exporter used in tests when wasm_exporter is absent."""
        import tempfile
        import pickle
        import pathlib
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wasm")
        pickle.dump((model, feature_names), tmp)
        tmp.close()
        return pathlib.Path(tmp.name)

# ---------------------------------------------------------------------------
# Constants / config ---------------------------------------------------------
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEATURE_STORE = os.path.join(ROOT, "feature_store.parquet")
MODEL_DIR = os.path.join(ROOT, "models", "candidate")
MODEL_PATH = os.path.join(MODEL_DIR, "model.wasm")

ROI_THRESHOLD = 10.0  # 10× ROI label boundary
DAYS_BACK = 30  # training window

# ---------------------------------------------------------------------------
# Helper functions -----------------------------------------------------------
# ---------------------------------------------------------------------------

def load_dataset() -> pd.DataFrame:
    """Load feature store and slice the last `DAYS_BACK` days."""
    if not os.path.exists(FEATURE_STORE):
        raise FileNotFoundError(f"feature store not found: {FEATURE_STORE}")
    df = pd.read_parquet(FEATURE_STORE)
    # Expect presence of 'timestamp' column containing seconds since epoch.
    if "timestamp" not in df.columns:
        raise ValueError("feature_store.parquet must contain 'timestamp' column")
    cutoff = datetime.utcnow() - timedelta(days=DAYS_BACK)
    df_time = df[df["timestamp"] >= cutoff.timestamp()].copy()
    if df_time.empty:
        raise ValueError("no data in the last 30 days – aborting retrain")
    return df_time


def build_labels(df: pd.DataFrame) -> pd.Series:
    """Binary label – 1 if ROI >= threshold else 0."""
    if "roi" not in df.columns:
        raise ValueError("dataset missing 'roi' column")
    return (df["roi"] >= ROI_THRESHOLD).astype(int)


def train_model(df: pd.DataFrame, y: pd.Series):
    feature_cols = [c for c in df.columns if c not in {"roi", "timestamp"}]
    X = df[feature_cols]
    dtrain = lgb.Dataset(X, label=y, free_raw_data=True)
    params = {
        "objective": "binary",
        "metric": "auc",
        "verbosity": -1,
        "max_depth": 6,
        "num_leaves": 31,
        "learning_rate": 0.1,
    }
    model = lgb.train(params, dtrain, num_boost_round=100)
    return model, feature_cols


def save_wasm(model, feature_cols):
    os.makedirs(MODEL_DIR, exist_ok=True)
    wasm_path = export_model(model, feature_cols)
    # Ensure we move it to the canonical location.
    os.replace(wasm_path, MODEL_PATH)
    return MODEL_PATH


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Main entry-point -----------------------------------------------------------
# ---------------------------------------------------------------------------

def main():
    df = load_dataset()
    y = build_labels(df)
    model, features = train_model(df, y)
    wasm_path = save_wasm(model, features)
    sha = sha256_of(wasm_path)
    manifest = {"sha256": sha, "features": sorted(features)}
    json.dump(manifest, sys.stdout)
    sys.stdout.write("\n")


def produce() -> tuple[str, str]:
    """Thin wrapper so manager can ingest nightly manifest.

    We reuse `main()` but capture its stdout instead of duplicating logic.
    Returns a tuple of (artifact_name, json_content).
    """
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    content = buf.getvalue().strip()
    return "manifest.json", content


if __name__ == "__main__":
    main() 