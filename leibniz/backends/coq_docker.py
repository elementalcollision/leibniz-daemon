"""Coq / Rocq backend — the real Rocq (Coq) kernel, run in an OrbStack/Docker container (ADR 0048).

A second *proof-edge* decider alongside Lean, built to the exact contract of ``leibniz.backends.lean_cli``:
it shells out to a pinned Rocq toolchain, **REPORTS** what the kernel said, and never touches
``Demonstratio.kernel_verified`` — ``CoqVerifier.discharge`` is the sole writer. Until the operator admits
``"CoqVerifier.discharge"`` to ``trust.KERNEL_PRODUCERS`` (the deferred, PreToolUse-guarded edit; see ADR
0048 §4.2 / ADR 0045 precedent), a Coq proof edge is still rejected structurally at promotion — so this
backend is *live for verification-amplification* (audit tier) but *dormant for promulgation*.

Trust rule — the Coq analogue of Lean's ``#print axioms`` discipline. A Coq proof is kernel-verified iff:
  (1) ``rocq compile`` exits 0 with no ``Error`` diagnostic; AND
  (2) no ``Print Assumptions`` in the source reports open ``Axioms:`` — every audited theorem is
      "Closed under the global context" (or names only an operator-approved axiom); AND
  (3) the source carries no self-laundering construct: ``Admitted`` / ``admit`` / ``Axiom`` / ``Parameter``
      / ``Hypothesis`` / ``Conjecture``.
``Admitted`` is the key laundering vector: it compiles to exit 0, but ``Print Assumptions`` then exposes the
theorem itself as an open axiom (caught by (2)) and the keyword is caught lexically by (3). A cert SHOULD
carry its own ``Print Assumptions <thm>.`` lines, exactly as a Lean cert carries ``#print axioms``.

Rocq 9.0 replaces ``coqc`` with ``rocq compile``. The image is amd64-only, so ``--platform linux/amd64``
(OrbStack runs it under Rosetta). Source is piped on **stdin** into the container's own writable ``/tmp`` —
no host filesystem is exposed, and the container is ``--rm``.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from leibniz.propositio import Expressio

DEFAULT_IMAGE = "rocq/rocq-prover:9.0"
PLATFORM = "linux/amd64"

# Self-laundering / trust-defeating constructs. A source containing any of these cannot earn a kernel
# verdict — they either add an axiom (Admitted/Axiom/Parameter/Hypothesis/Conjecture) or leave a hole
# (admit). Matched as whole words so e.g. `admit` does not spuriously fire inside an identifier.
_FORBIDDEN = ("Admitted", "admit", "Axiom", "Parameter", "Hypothesis", "Conjecture")
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN) + r")\b")
_ERROR_RE = re.compile(r"^Error", re.MULTILINE)
_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)  # Coq comments are inert prose — strip before the scan


@dataclass(frozen=True)
class CoqResult:
    returncode: int
    output: str
    source: str = ""

    @property
    def has_errors(self) -> bool:
        return self.returncode != 0 or bool(_ERROR_RE.search(self.output)) or "Error:" in self.output

    @property
    def opens_axioms(self) -> bool:
        """A `Print Assumptions` that finds open axioms prints an `Axioms:` block; a fully-closed proof
        prints "Closed under the global context"."""
        return "Axioms:" in self.output

    @property
    def uses_forbidden(self) -> bool:
        # Scan CODE only: a keyword mentioned in a comment ("An `Admitted` proof …") is inert. The real
        # anti-laundering guard is `opens_axioms` (Print Assumptions on the kernel's OUTPUT); this lexical
        # scan is a belt-and-suspenders block on an actual Admitted/admit/Axiom in the source.
        return bool(_FORBIDDEN_RE.search(_COMMENT_RE.sub(" ", self.source)))

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
    _cache: dict[str, CoqResult] = field(default_factory=dict, repr=False)

    # --- proof-edge surface (mirrors LeanBackend) -----------------------------
    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        res = self._run(_assemble(expr, proof_src))
        return res is not None and res.kernel_ok

    def check_source(self, source: str) -> Optional[bool]:
        """Report the kernel verdict on a COMPLETE Coq source (already-assembled cert). True iff it
        compiles clean, audits closed, and carries no laundering construct; False if the kernel rejects
        it; None if the backend is unavailable. Never touches kernel_verified."""
        res = self._run(source)
        return None if res is None else res.kernel_ok

    def check_source_with_detail(self, source: str) -> Optional[dict]:
        """Like check_source, but return the audit breakdown for a verification-amplification report."""
        res = self._run(source)
        if res is None:
            return None
        return {
            "verified": res.kernel_ok,
            "returncode": res.returncode,
            "has_errors": res.has_errors,
            "opens_axioms": res.opens_axioms,
            "uses_forbidden": res.uses_forbidden,
            "closed_under_global_context": "Closed under the global context" in res.output,
            "output_tail": "\n".join(res.output.splitlines()[-8:]),
        }

    def compile_statement(self, expr: Expressio) -> bool:
        """Syntactic validity: does the statement type-check with an admitted body? (Uses `Admitted.`,
        which is fine here because we only ask whether the STATEMENT is well-formed, not proven.)"""
        res = self._run(_assemble(expr, "Proof. Admitted."))
        return res is not None and not res.has_errors

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        """Triviality probe: a statement some automatic tactic closes on its own is vacuous."""
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
        try:
            proc = subprocess.run(
                ["docker", "run", "--rm", "-i", "--platform", PLATFORM, self.image,
                 "bash", "-lc", "cat > /tmp/leibniz.v && rocq compile -q /tmp/leibniz.v 2>&1"],
                input=source, capture_output=True, text=True, timeout=self.timeout_s,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        res = CoqResult(proc.returncode, f"{proc.stdout}\n{proc.stderr}", source=source)
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
