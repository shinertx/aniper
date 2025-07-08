"""Stub manager that will later schedule sub-agents."""
import asyncio
import importlib
import json
import os
import time
import hashlib
from typing import Callable, Dict, Tuple, Any

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover – runtime env may inject
    redis = None  # type: ignore

# Hard-fail early if Redis client missing to avoid silent degradation
if redis is None:
    raise SystemExit("Redis Python package missing – abort")

# ---------------------------------------------------------------------------
# Task registry --------------------------------------------------------------
# ---------------------------------------------------------------------------

AgentProduce = Callable[[], Tuple[str, str]]  # returns (artifact_name, content)

AGENTS: Dict[str, Dict[str, Any]] = {
    "narrative": {
        "interval": 600,  # 10 min
        "module": "brain.agents.narrative_agent",
    },
    "redteam": {
        "interval": 6 * 60 * 60,  # 6 h
        "module": "brain.agents.redteam_agent",
    },
    "performance_coach": {
        "interval": 15 * 60,  # 15 min
        "module": "brain.agents.performance_coach",
    },
    "heuristic": {
        "interval": 24 * 60 * 60,  # nightly
        "module": "brain.agents.heuristic_agent",
    },
}

if "REDIS_URL" not in os.environ:
    raise SystemExit("REDIS_URL environment variable required")
REDIS_URL = os.environ["REDIS_URL"]

# ---------------------------------------------------------------------------
# Helpers --------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _import_producer(module_path: str, attr: str | None = None) -> AgentProduce:
    """Import module and retrieve produce callable.

    Attr defaults to `produce`; retained parameter for fwd-compat.
    """
    mod = importlib.import_module(module_path)
    return getattr(mod, attr or "produce")  # type: ignore[return-value]


async def _run_once(agent_name: str, redis_cli) -> None:  # pragma: no cover – scheduling tests separate
    cfg = AGENTS[agent_name]
    produce: AgentProduce = _import_producer(cfg["module"], None)  # type: ignore[arg-type]

    # The produce function may be blocking → run in thread pool
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, produce)

    # If agent prints to stdout but returns None (e.g., heuristic_agent.main)
    # we skip Redis publishing.  Future work: capture stdout.
    if result is None:
        return

    artifact_name, content = result

    sha = hashlib.sha256(content.encode()).hexdigest()
    payload = {
        "agent": agent_name,
        "artifact": artifact_name,
        "sha256": sha,
        "content": content,
    }

    if redis_cli is not None:
        redis_cli.publish("config_updates", json.dumps(payload))


async def main() -> None:  # pragma: no cover
    last_run: Dict[str, float] = {k: 0.0 for k in AGENTS}

    redis_cli = None
    if redis is not None:
        try:
            redis_cli = redis.Redis.from_url(REDIS_URL)
        except Exception:
            redis_cli = None

    while True:
        now = time.time()
        tasks = []
        for name, cfg in AGENTS.items():
            interval = float(cfg.get("interval", 0))
            if now - last_run[name] >= interval:
                tasks.append(_run_once(name, redis_cli))
                last_run[name] = now
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main()) 