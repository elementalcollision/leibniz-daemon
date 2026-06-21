"""R1 Lean backend — the real Lean 4 kernel, run in an OrbStack/Docker container.

Satisfies ``leibniz.verifiers.LeanBackend`` by shelling out to a pinned Lean
toolchain inside a container (host stays pure-stdlib Python 3.14+; the Lean stack
lives in the container, per ADR 0003). It checks *complete* proofs in batch via
``lake env lean <file>`` and reads the kernel's diagnostics. It deliberately does
NOT step proof states — that interactive capability (LeanDojo) is deferred to R4.

Trust contract (CLAUDE.md invariants 1 & 7):
- This backend only *reports* what the Lean kernel said. It never touches
  ``Demonstratio.kernel_verified`` — ``LeanVerifier.discharge`` remains the sole
  writer.
- ``check_proof`` returns True iff the candidate file elaborates with no
  error-level diagnostics AND uses no ``sorry`` / ``sorryAx`` (a ``sorry`` is the
  Lean axiom of "trust me", which would make a proof unsound).
- The result cache is keyed on the exact source hash and is populated only by a
  real kernel run — a cache hit replays a genuine kernel verdict, never a bare
  boolean (closes the R1 cache-hit hazard from the plan review).
"""
from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from leibniz.propositio import Expressio

DEFAULT_IMAGE = "leibniz-lean:v4.31.0"
# Core-Lean triviality tactics; Mathlib's `aesop` is added with R1b.
DEFAULT_TRIVIAL_TACTICS = ("decide", "simp", "omega", "trivial")


def _join_proof(theorem_src: str, proof_src: str) -> str:
    """Assemble a complete Lean declaration from a statement header + a proof.

    ``Expressio.theorem_src`` is the statement only (e.g. ``theorem t : P``);
    ``proof_src`` is the term/tactic block (e.g. ``by decide``).
    """
    head = theorem_src.rstrip()
    proof = proof_src.strip()
    if ":=" in head:
        return f"{head} {proof}".rstrip() if proof else head
    if not proof:
        return f"{head} := by sorry"
    return f"{head} := {proof}"


@dataclass(frozen=True)
class LeanResult:
    returncode: int
    output: str

    @property
    def has_errors(self) -> bool:
        # Lean prints "error:" for elaboration/kernel failures; a nonzero exit
        # also signals failure.
        return self.returncode != 0 or "error:" in self.output

    @property
    def uses_sorry(self) -> bool:
        return "sorry" in self.output or "sorryAx" in self.output

    @property
    def kernel_ok(self) -> bool:
        """A proof is kernel-verified iff it elaborated cleanly and used no sorry."""
        return (not self.has_errors) and (not self.uses_sorry)


@dataclass
class LeanCliBackend:
    image: str = DEFAULT_IMAGE
    timeout_s: int = 180
    trivial_tactics: tuple[str, ...] = DEFAULT_TRIVIAL_TACTICS
    # (sha256(source) -> LeanResult); only ever populated by a genuine kernel run.
    _cache: dict[str, LeanResult] = field(default_factory=dict, repr=False)

    # --- LeanBackend Protocol -------------------------------------------------
    def compile_statement(self, expr: Expressio) -> bool:
        """Syntactic/elaboration validity: the statement type checks (sorry-allowed)."""
        res = self._run_lean(_join_proof(expr.theorem_src, "by sorry"))
        return res is not None and not res.has_errors

    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        """Kernel verification of the complete proof. The only source of truth for
        whether a Demonstratio holds."""
        res = self._run_lean(_join_proof(expr.theorem_src, proof_src))
        return res is not None and res.kernel_ok

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        """Non-triviality test: does an automated tactic close the statement alone?"""
        for tac in self.trivial_tactics:
            res = self._run_lean(_join_proof(expr.theorem_src, f"by {tac}"))
            if res is not None and res.kernel_ok:
                return True
        return False

    # --- internals ------------------------------------------------------------
    def _run_lean(self, source: str) -> Optional[LeanResult]:
        key = hashlib.sha256(source.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "Thm.lean").write_text(source)
                proc = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "-v", f"{td}:/scratch:ro",
                        "-w", "/work/lean-project",
                        self.image,
                        "lake", "env", "lean", "/scratch/Thm.lean",
                    ],
                    capture_output=True, text=True, timeout=self.timeout_s,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # docker missing or the kernel hung: report "unknown" (None), never a pass.
            return None
        res = LeanResult(proc.returncode, f"{proc.stdout}\n{proc.stderr}")
        self._cache[key] = res
        return res


def available(image: str = DEFAULT_IMAGE) -> bool:
    """True iff docker and the Lean image are usable. Used to skip Lean tests where
    the container is not present (e.g. CI)."""
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
