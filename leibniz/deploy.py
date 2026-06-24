"""ADR 0033 Slice 4 — deploy-profile isolation guard.

A friendly, EARLY check that a deploy profile keeps a non-prod instance's state separate
from PROD. It is the operational complement to the runtime write-barrier (ADR 0033 Slice 1):
the write-barrier *fails closed* at the SQLite layer if a UAT run is pointed at the PROD
ledger; this guard catches the same misconfiguration at launch with a clear message, before
any work runs.

It validates a profile (a mapping of env vars), not live trust state — so it is pure and
testable. It never relaxes anything: the write-barrier, publish guard, and provenance still
hold regardless of what this says.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Optional

VALID_INSTANCES = ("prod", "uat", "dev")
# PROD's canonical state directory. A non-prod instance must NOT write here — it must own a
# distinct dir (e.g. .leibniz-uat/). Checked by directory name, so it is checkout-independent.
PROD_STATE_DIR = ".leibniz"
_STATE_KNOBS = ("LEIBNIZ_RUNTIME_DB", "LEIBNIZ_FRONTIER_PATH", "LEIBNIZ_NOTEBOOK_PATH")


def validate_profile(env: Mapping[str, str]) -> list[str]:
    """Return a list of hard problems with the profile (empty == OK).

    - the instance must be one of prod | uat | dev;
    - a NON-prod instance must explicitly set each state knob to a dir other than PROD's
      `.leibniz/` (so it can never inherit or collide with the production ledger);
    - a UAT profile must not point its published-ledger export at the prod Codex;
    - a PROD profile must not point any state knob at a UAT path.
    """
    problems: list[str] = []
    inst = (env.get("LEIBNIZ_INSTANCE") or "").strip().lower()
    if inst not in VALID_INSTANCES:
        problems.append(f"LEIBNIZ_INSTANCE must be one of {VALID_INSTANCES}, got {inst!r}")
        return problems  # nothing else is meaningful without a valid instance

    if inst != "prod":
        for knob in _STATE_KNOBS:
            val = (env.get(knob) or "").strip()
            if not val:
                problems.append(
                    f"{inst}: {knob} must be set — a non-prod instance must own separate state "
                    f"(ADR 0033), not inherit the prod default"
                )
            elif Path(val).parent.name == PROD_STATE_DIR:
                problems.append(
                    f"{inst}: {knob}={val!r} uses the PROD state dir '{PROD_STATE_DIR}/'; point it "
                    f"at a separate dir (e.g. '.leibniz-{inst}/')"
                )
        if inst == "uat":
            led = (env.get("LEIBNIZ_LEDGER") or "").strip()
            if led and "uat" not in led.lower():
                problems.append(
                    f"uat: LEIBNIZ_LEDGER={led!r} is not UAT-scoped — UAT must never publish to the "
                    f"prod Codex (the publish guard also blocks this; keep them separate anyway)"
                )
    else:
        for knob in (*_STATE_KNOBS, "LEIBNIZ_LEDGER"):
            val = (env.get(knob) or "").strip()
            if val and "uat" in val.lower():
                problems.append(
                    f"prod: {knob}={val!r} contains 'uat' — refusing a PROD profile that points at "
                    f"UAT state"
                )
    return problems


def check_env(env: Optional[Mapping[str, str]] = None) -> int:
    """Print a verdict for the active (or given) environment; return a shell exit code.

    Used by `scripts/run_instance.sh` as the early launch guard."""
    env = os.environ if env is None else env
    inst = (env.get("LEIBNIZ_INSTANCE") or "dev").strip().lower()
    problems = validate_profile(env)
    if problems:
        print(f"[deploy] ✗ {inst}: profile has {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"[deploy] ✓ {inst}: profile OK — state isolated from prod (ADR 0033)")
    return 0


if __name__ == "__main__":  # `python3 -m leibniz.deploy`
    raise SystemExit(check_env())
