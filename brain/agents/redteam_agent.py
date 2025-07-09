from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

import openai
import yaml  # type: ignore

# ---------------------------------------------------------------------------
# Core logic ----------------------------------------------------------------
# ---------------------------------------------------------------------------


USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm_call_total = 0  # Prometheus counter placeholder


def suggest_guard_patches(current_filters: Dict[str, Any]) -> Dict[str, Any]:
    """Produce patch suggestions for guard-rules, optionally using LLM."""
    global llm_call_total
    if USE_LLM and OPENAI_API_KEY:
        try:
            openai.api_key = OPENAI_API_KEY
            prompt = f"Suggest YAML patch heuristics for these filters: {json.dumps(current_filters)}. Return a JSON object with a 'patches' key containing a list of patch dicts."
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=256,
            )
            llm_call_total += 1  # Increment Prometheus counter
            result = json.loads(response.choices[0].message.content)
            if "patches" in result:
                return result
        except Exception:
            pass  # Fallback to heuristic below if LLM fails

    # Heuristic rule: adjust max_position by +10 % to widen risk buffer
    patches: list[dict[str, Any]] = []
    if (mp := current_filters.get("max_position")) and isinstance(mp, (int, float)):
        new_val = int(mp * 1.1)
        if new_val != mp:
            patches.append({"path": "/max_position", "operation": "replace", "value": new_val})

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