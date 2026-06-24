"""ADR 0033 Slice 4: deploy-profile isolation guard.

The launch-time complement to the runtime write-barrier: it refuses a profile that would let a
non-prod instance write PROD's state, or a prod profile pointed at UAT state. Pure/testable —
it never relaxes the in-code guards (write-barrier, publish guard, provenance), which still hold.
CI-safe; NOT in test_invariants.py (the trust floor is frozen).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from leibniz.deploy import check_env, validate_profile

_PROFILES = Path(__file__).resolve().parent.parent / "deploy" / "profiles"


def _parse_env_example(path: Path) -> dict:
    """Minimal KEY=value reader (ignores blanks + #-comments) for an .env.example template."""
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def _ok_uat() -> dict:
    return {
        "LEIBNIZ_INSTANCE": "uat",
        "LEIBNIZ_RUNTIME_DB": ".leibniz-uat/memory.db",
        "LEIBNIZ_FRONTIER_PATH": ".leibniz-uat/frontier.json",
        "LEIBNIZ_NOTEBOOK_PATH": ".leibniz-uat/notebook.json",
    }


def test_clean_uat_profile_passes():
    assert validate_profile(_ok_uat()) == []
    assert check_env(_ok_uat()) == 0


def test_clean_prod_profile_passes():
    env = {
        "LEIBNIZ_INSTANCE": "prod",
        "LEIBNIZ_RUNTIME_DB": ".leibniz/memory.db",
        "LEIBNIZ_FRONTIER_PATH": ".leibniz/frontier.json",
        "LEIBNIZ_NOTEBOOK_PATH": ".leibniz/notebook.json",
        "LEIBNIZ_LEDGER": "../codex-calculemus",
    }
    assert validate_profile(env) == []


def test_unknown_instance_is_refused():
    probs = validate_profile({"LEIBNIZ_INSTANCE": "staging"})
    assert probs and "LEIBNIZ_INSTANCE" in probs[0]


def test_uat_pointed_at_prod_state_dir_is_refused():
    env = _ok_uat()
    env["LEIBNIZ_RUNTIME_DB"] = ".leibniz/memory.db"  # the PROD dir — the dangerous case
    probs = validate_profile(env)
    assert any("PROD state dir" in p and "LEIBNIZ_RUNTIME_DB" in p for p in probs)
    assert check_env(env) == 1


def test_non_prod_must_set_state_explicitly():
    env = {"LEIBNIZ_INSTANCE": "uat"}  # no state knobs at all
    probs = validate_profile(env)
    # all three state knobs flagged as unset
    assert len(probs) == 3 and all("must be set" in p for p in probs)


def test_uat_ledger_must_be_uat_scoped():
    env = _ok_uat()
    env["LEIBNIZ_LEDGER"] = "../codex-calculemus"  # the PROD Codex — UAT must not publish there
    probs = validate_profile(env)
    assert any("LEIBNIZ_LEDGER" in p and "UAT-scoped" in p for p in probs)


def test_uat_scoped_ledger_is_fine():
    env = _ok_uat()
    env["LEIBNIZ_LEDGER"] = "../codex-calculemus-uat"
    assert validate_profile(env) == []


def test_prod_pointed_at_uat_state_is_refused():
    env = {
        "LEIBNIZ_INSTANCE": "prod",
        "LEIBNIZ_RUNTIME_DB": ".leibniz-uat/memory.db",  # a prod profile aimed at UAT state
        "LEIBNIZ_FRONTIER_PATH": ".leibniz/frontier.json",
        "LEIBNIZ_NOTEBOOK_PATH": ".leibniz/notebook.json",
    }
    probs = validate_profile(env)
    assert any("contains 'uat'" in p for p in probs)


def test_dev_profile_uses_its_own_dir():
    env = {
        "LEIBNIZ_INSTANCE": "dev",
        "LEIBNIZ_RUNTIME_DB": ".leibniz-dev/memory.db",
        "LEIBNIZ_FRONTIER_PATH": ".leibniz-dev/frontier.json",
        "LEIBNIZ_NOTEBOOK_PATH": ".leibniz-dev/notebook.json",
    }
    assert validate_profile(env) == []


@pytest.mark.parametrize("name", ["prod", "uat", "dev"])
def test_shipped_example_profiles_validate(name):
    # The templates we ship must themselves pass the guard, so an operator who copies one
    # verbatim starts from a clean, isolated profile.
    env = _parse_env_example(_PROFILES / f"{name}.env.example")
    assert env.get("LEIBNIZ_INSTANCE") == name
    assert validate_profile(env) == []
