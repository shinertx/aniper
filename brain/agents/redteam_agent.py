from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

import yaml  # type: ignore

# ---------------------------------------------------------------------------
# Core logic ----------------------------------------------------------------
# ---------------------------------------------------------------------------


def suggest_guard_patches(current_filters: Dict[str, Any]) -> Dict[str, Any]:
    """Produce patch suggestions for guard-rules.

    The algorithm is deliberately simple: we look for well-known numeric guard
    rails and tighten/loosen them based on heuristic multipliers.  In
    production this would be the result of an LLM call with context, but the
    placeholder keeps unit-tests deterministic and avoids OpenAI cost.
    """
    patches: list[dict[str, Any]] = []

    # Example rule: adjust max_position by +10 % to widen risk buffer
    if (mp := current_filters.get("max_position")) and isinstance(mp, (int, float)):
        new_val = int(mp * 1.1)
        if new_val != mp:
            patches.append({"path": "/max_position", "operation": "replace", "value": new_val})

    # More rules could be appended here …

    return {"patches": patches}


# ---------------------------------------------------------------------------
# Artifact production -------------------------------------------------------
# ---------------------------------------------------------------------------


def produce(current_filters: Dict[str, Any] | None = None) -> Tuple[str, str]:
    """Return YAML artifact for manager."""
    current_filters = current_filters or {}
    patch_dict = suggest_guard_patches(current_filters)
    yaml_str = yaml.safe_dump(patch_dict, sort_keys=False)
    return "guard_patches.yaml", yaml_str


# ---------------------------------------------------------------------------
# CLI entry-point -----------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    filters_path = os.getenv("FILTERS_JSON")  # optionally read current filter set
    if filters_path and os.path.exists(filters_path):
        with open(filters_path, "r", encoding="utf-8") as fh:
            current = json.load(fh)
    else:
        current = {}

    name, content = produce(current)

    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts"))
    os.makedirs(artifacts_dir, exist_ok=True)
    with open(os.path.join(artifacts_dir, name), "w", encoding="utf-8") as fh:
        fh.write(content)

    print(content)


if __name__ == "__main__":
    main() 