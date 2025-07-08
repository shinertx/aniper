import subprocess
import sys
from datetime import datetime, timezone

"""Nightly retrain cron entry.

Schedule: 03:30 UTC every day (see Ops infra nomad/cron).  The scheduler shell
invokes `python -m brain.cron_retrain` inside the Brain container.  We run the
heuristic agent and forward its JSON manifest to STDOUT, letting upstream
systems persist the artefact.

Guardrails (AGENTS_GUIDE):
• Must terminate < 10 min (dataset ≤ 1 M rows, LightGBM training ≪ cap).
• Exit code non-zero on failure so cron monitors can alert.
"""

CMD = [sys.executable, "-m", "brain.agents.heuristic_agent"]


def main() -> None:
    start = datetime.now(timezone.utc)
    try:
        result = subprocess.run(CMD, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)
    finally:
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        print(f"retrain duration_sec={duration:.1f}")


if __name__ == "__main__":
    main() 