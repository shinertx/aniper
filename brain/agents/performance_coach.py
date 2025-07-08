from __future__ import annotations

import os
from typing import Tuple, Dict

import yaml  # type: ignore

try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover – tests monkey-patch
    httpx = None  # type: ignore

# ---------------------------------------------------------------------------
# Constants ------------------------------------------------------------------
# ---------------------------------------------------------------------------

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090/metrics")
BASELINE_TICKET_SIZE = int(os.getenv("BASELINE_TICKET_SIZE", "10"))

# ---------------------------------------------------------------------------
# Metric helpers -------------------------------------------------------------
# ---------------------------------------------------------------------------

def _parse_metrics(text: str) -> Tuple[int, int]:
    """Return (hit, total) counters parsed from Prometheus exposition text."""
    hit = total = 0
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("trade_hit_total"):
            try:
                hit += int(float(line.split()[1]))
            except (IndexError, ValueError):
                pass
        elif line.startswith("trades_submitted_total"):
            try:
                total += int(float(line.split()[1]))
            except (IndexError, ValueError):
                pass
    return hit, total


def _suggest_ticket_size(baseline: int, hit: int, total: int) -> int:
    if total == 0:
        return baseline
    ratio = hit / total
    if ratio > 0.9:
        return int(baseline * 1.1)
    if ratio < 0.5:
        return max(1, int(baseline * 0.9))
    return baseline

# ---------------------------------------------------------------------------
# Artifact production --------------------------------------------------------
# ---------------------------------------------------------------------------

def produce() -> Tuple[str, str]:
    """Return YAML artifact adjusting ticket size based on hit-rate."""
    if httpx is None:
        metrics_txt = ""
    else:
        try:
            resp = httpx.get(PROMETHEUS_URL, timeout=5)
            resp.raise_for_status()
            metrics_txt = resp.text
        except Exception:  # pragma: no cover – network error ignored
            metrics_txt = ""

    hit, total = _parse_metrics(metrics_txt)
    new_size = _suggest_ticket_size(BASELINE_TICKET_SIZE, hit, total)

    data: Dict[str, int] = {
        "ticket_size": new_size,
        "baseline_ticket_size": BASELINE_TICKET_SIZE,
    }
    return "risk_patch.yaml", yaml.safe_dump(data, sort_keys=False)

# ---------------------------------------------------------------------------
# CLI -----------------------------------------------------------------------
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover
    name, content = produce()
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts"))
    os.makedirs(artifacts_dir, exist_ok=True)
    with open(os.path.join(artifacts_dir, name), "w", encoding="utf-8") as fh:
        fh.write(content)
    print(content)

if __name__ == "__main__":
    main() 