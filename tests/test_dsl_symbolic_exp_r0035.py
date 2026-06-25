"""ADR 0035 Stage A — the symbolic-exponent DSL invitation is ENV-GATED (default off).

The `base^n % m` prompt invitation is read from LEIBNIZ_DSL_SYMBOLIC_EXP at import, so main's
conjecturer is unchanged until the live calibration arm sets the flag. Tested in a subprocess
because the flag is consumed at module-import time (the production path the calibrate run uses).
"""
from __future__ import annotations

import os
import subprocess
import sys

_SNIPPET = (
    "from leibniz.providers import AUTOFORMALIZE_DSL as d, AUTOFORMALIZE_PROMPTS as p\n"
    "from leibniz.types import Role\n"
    "print('INVITED' if 'base^n % m with a CONSTANT base' in d else 'NOT')\n"
    "print('PROMPT' if 'base^n % m' in p[Role.CONJECTURE] else 'PLAIN')\n"
    "p[Role.CONJECTURE].format(context='x')  # must still .format() cleanly\n"
)


def _run(flag: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != "LEIBNIZ_DSL_SYMBOLIC_EXP"}
    if flag is not None:
        env["LEIBNIZ_DSL_SYMBOLIC_EXP"] = flag
    r = subprocess.run([sys.executable, "-c", _SNIPPET], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_default_off_keeps_variable_exponents_forbidden():
    out = _run(None)
    assert "NOT" in out and "PLAIN" in out


def test_zero_is_off():
    out = _run("0")
    assert "NOT" in out and "PLAIN" in out


def test_flag_on_invites_base_pow_n_mod_m():
    out = _run("1")
    assert "INVITED" in out and "PROMPT" in out
