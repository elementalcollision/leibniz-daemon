"""Coq / Rocq backend — the real Rocq (Coq) kernel, run in an OrbStack/Docker container (ADR 0048).

A second *proof-edge* decider alongside Lean, built to the contract of ``leibniz.backends.lean_cli``: it shells
out to a pinned Rocq toolchain, **REPORTS** what the kernel said, and never touches
``Demonstratio.kernel_verified`` — ``CoqVerifier.discharge`` (deferred; see ADR 0048 §4.2) is the sole writer.

Trust rule — kernel-driven, name-agnostic. An adversarial review (2026-07-05) showed that a *source-side*
axiom scan is defeatable: a proof can hide an axiom by omitting ``Print Assumptions`` and by using a binder
form (``Definition``/``Goal``/``Instance``/``Fixpoint``/``Let``) a keyword regex doesn't enumerate. So the
audit is instead driven by Rocq's separate library checker **``rocqchk``**, which re-validates the compiled
``.vo`` and prints a CONTEXT SUMMARY of the WHOLE development's axioms and unsafe constructs — independent of
how anything was named. A source is kernel-verified iff:
  (1) ``rocq compile`` succeeds (no ``Error``); AND
  (2) ``rocqchk -o`` reports ``* Axioms: <none>`` (or only operator-approved axioms) AND ``<none>`` for
      type-in-type, unsafe (co)fixpoints, and assumed-positivity inductives; AND
  (3) (defence-in-depth) the source carries no ``Admitted``/``admit``/``Axiom``/``Parameter``/``Hypothesis``/
      ``Variable``/``Context``/``Conjecture`` — ``admit`` leaves a hole; ``Variable``/``Context`` let the
      *stated* theorem secretly rest on a section hypothesis that ``rocqchk`` sees as a sound implication.

Rocq 9.0 replaces ``coqc``/``coqchk`` with ``rocq compile`` / ``rocqchk``. The image is amd64-only, so
``--platform linux/amd64`` (OrbStack under Rosetta). Source is piped on **stdin** into the container's own
writable ``/tmp`` — no host filesystem is exposed, and the container is ``--rm``.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from leibniz.propositio import Expressio

DEFAULT_IMAGE = "rocq/rocq-prover:9.0"
PLATFORM = "linux/amd64"

# Defence-in-depth lexical guard (the load-bearing check is the rocqchk audit below). Whole-word matched.
_FORBIDDEN = ("Admitted", "admit", "Axiom", "Axioms", "Parameter", "Parameters",
              "Hypothesis", "Hypotheses", "Variable", "Variables", "Conjecture", "Context")
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN) + r")\b")
_PLUGIN_RE = re.compile(r"Declare\s+ML\s+Module")   # loading an arbitrary Coq ML plugin
_ERROR_RE = re.compile(r"^Error", re.MULTILINE)
_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)  # Coq comments are inert prose — strip before the scan


def _check_script(nonce: str) -> str:
    """Compile the stdin source to /tmp/m.vo, then re-check it with rocqchk and print its CONTEXT SUMMARY.
    The module's logical name is Top.m (fixed by -R /tmp Top). The `nonce` — a random token the compiled
    source never sees (it is in the bash argv, not in the .v piped on stdin) — delimits the AUTHENTIC rocqchk
    output: a malicious source can print a forged summary to compile stdout, but cannot forge this marker, and
    the parser reads only the LAST (real) block. Closes the adversarial output-injection route (2026-07-05)."""
    return (
        "export PATH=$HOME/.opam/4.14.2+flambda/bin:$PATH; cd /tmp; cat > m.v; "
        "rocq compile -q -R /tmp Top m.v 2>&1; ec=$?; "
        f"printf '\\n%s\\n' '{nonce}'; "
        "if [ $ec -eq 0 ]; then rocqchk -o -R /tmp Top Top.m 2>&1; fi"
    )


# The rocqchk CONTEXT SUMMARY lines that must each read "<none>" for a kernel-clean development.
_SUMMARY_LABELS = (
    "Axioms",
    "Constants/Inductives relying on type-in-type",
    "Constants/Inductives relying on unsafe (co)fixpoints",
    "Inductives whose positivity is assumed",
)


def _section(chk: str, label: str) -> Optional[str]:
    """The content of a `* <label>:` section of the rocqchk summary, up to the next `*` (or end)."""
    m = re.search(re.escape("* " + label) + r"\s*:(.*?)(?=\n\s*\*|\Z)", chk, re.DOTALL)
    return m.group(1).strip() if m is not None else None


@dataclass(frozen=True)
class CoqResult:
    returncode: int
    output: str
    source: str = ""
    nonce: str = ""
    allow_axioms: frozenset = frozenset()

    @property
    def _parts(self) -> tuple[str, str]:
        # rpartition on the unforgeable nonce → the LAST block is rocqchk's authentic output; anything the
        # source printed to compile stdout (incl. a forged marker+summary) stays in the compile prefix.
        compile_out, sep, chk = self.output.rpartition(self.nonce) if self.nonce else (self.output, "", "")
        return (compile_out if sep else self.output), (chk if sep else "")

    @property
    def has_errors(self) -> bool:
        compile_out, _ = self._parts
        return bool(_ERROR_RE.search(compile_out)) or "Error:" in compile_out

    @property
    def audit_ran(self) -> bool:
        _, chk = self._parts
        return "CONTEXT SUMMARY" in chk

    @property
    def opens_axioms(self) -> bool:
        """True iff the rocqchk whole-library audit reports ANY axiom / unsafe construct (or did not run).
        Fail-closed: a missing summary counts as unaudited → not clean."""
        _, chk = self._parts
        if not self.audit_ran:
            return True
        for label in _SUMMARY_LABELS:
            content = _section(chk, label)
            if content is None:                       # section absent → fail closed
                return True
            if content == "<none>":
                continue
            if label == "Axioms":                      # only operator-approved axioms may remain
                names = [ln.strip() for ln in content.splitlines() if ln.strip()]
                if all(n in self.allow_axioms for n in names):
                    continue
            return True
        return False

    @property
    def uses_forbidden(self) -> bool:
        code = _COMMENT_RE.sub(" ", self.source)
        return bool(_FORBIDDEN_RE.search(code)) or bool(_PLUGIN_RE.search(code))

    @property
    def kernel_ok(self) -> bool:
        return (not self.has_errors) and (not self.opens_axioms) and (not self.uses_forbidden)


def _assemble(expr: Expressio, proof_src: str) -> str:
    """Assemble a complete Coq source from a Coq Expressio + a proof. `imports` are Coq library names
    (the Lean default "Mathlib" is skipped); `theorem_src` is a Coq statement header (`Theorem foo : P.`)."""
    reqs = "\n".join(f"Require Import {m}." for m in (expr.imports or ()) if m and m != "Mathlib")
    head = expr.theorem_src.strip()
    proof = (proof_src or "").strip()
    body = f"{head}\n{proof}".strip()
    return (f"{reqs}\n{body}\n" if reqs else f"{body}\n")


@dataclass
class CoqDockerBackend:
    """Report-only Rocq runner. Mirrors LeanCliBackend's method surface so a CoqVerifier can discharge
    through it exactly as LeanVerifier discharges through LeanCliBackend."""

    image: str = DEFAULT_IMAGE
    timeout_s: int = 180
    allow_axioms: frozenset = frozenset()   # operator-approved axiom names (default: none — strictest)
    _cache: dict[str, CoqResult] = field(default_factory=dict, repr=False)

    # --- proof-edge surface (mirrors LeanBackend) -----------------------------
    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        res = self._run(_assemble(expr, proof_src))
        return res is not None and res.kernel_ok

    def check_source(self, source: str) -> Optional[bool]:
        """Report the kernel verdict on a COMPLETE Coq source. True iff it compiles clean, the rocqchk
        whole-library audit is axiom/unsafe-free, and no laundering keyword is present; False if rejected;
        None if the backend is unavailable. Never touches kernel_verified."""
        res = self._run(source)
        return None if res is None else res.kernel_ok

    def check_source_with_detail(self, source: str) -> Optional[dict]:
        """Like check_source, but return the audit breakdown for a verification-amplification report."""
        res = self._run(source)
        if res is None:
            return None
        return {
            "verified": res.kernel_ok,
            "has_errors": res.has_errors,
            "audit_ran": res.audit_ran,
            "opens_axioms": res.opens_axioms,
            "uses_forbidden": res.uses_forbidden,
            "output_tail": "\n".join(res.output.splitlines()[-12:]),
        }

    def compile_statement(self, expr: Expressio) -> bool:
        res = self._run(_assemble(expr, "Proof. Admitted."))
        return res is not None and not res.has_errors

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        for tac in ("reflexivity", "trivial", "auto", "lia", "ring", "discriminate"):
            res = self._run(_assemble(expr, f"Proof. {tac}. Qed."))
            if res is not None and res.kernel_ok:
                return True
        return False

    # --- internals ------------------------------------------------------------
    def _run(self, source: str) -> Optional[CoqResult]:
        key = hashlib.sha256(source.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        nonce = "ROCQCHK_" + secrets.token_hex(16)   # unforgeable delimiter (source never sees the argv)
        try:
            proc = subprocess.run(
                ["docker", "run", "--rm", "-i", "--platform", PLATFORM, self.image,
                 "bash", "-lc", _check_script(nonce)],
                input=source, capture_output=True, text=True, timeout=self.timeout_s,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if proc.returncode == 125 or "Cannot connect to the Docker daemon" in (proc.stderr or ""):
            return None   # docker infra failure (missing image / daemon down) → UNAVAILABLE, not a rejection
        res = CoqResult(proc.returncode, f"{proc.stdout}\n{proc.stderr}", source=source,
                        nonce=nonce, allow_axioms=self.allow_axioms)
        self._cache[key] = res
        return res


def available(image: str = DEFAULT_IMAGE) -> bool:
    """True iff docker and the Rocq image are usable (used to skip Coq tests when Docker is down)."""
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
