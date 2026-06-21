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
  error-level diagnostics AND uses no ``sorry`` / ``sorryAx``.
- The result cache is keyed on the exact source hash and is populated only by a
  real kernel run — a cache hit replays a genuine kernel verdict, never a bare bool.

R1c additions:
- ``normalize_statement`` returns an *elaborator-canonical* structural hash (de
  Bruijn indices + fully-qualified constants), so alpha-renamed / notation-different
  statements of the same theorem collide. This is what the R3 novelty corpus keys
  on (textual hashing in ``verifiers.normalize_statement`` is the fallback).
- ``persistent=True`` keeps one container alive and uses ``docker exec`` per check
  (removes ~25% per-check container-churn overhead). Default is stateless
  (``docker run --rm``) so there is nothing to leak.
"""
from __future__ import annotations

import atexit
import hashlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from leibniz.propositio import Expressio

DEFAULT_IMAGE = "leibniz-lean:v4.31.0"
# Triviality tactics. `aesop` needs a Mathlib/Aesop import (R1b) — when absent it
# simply errors and is treated as "did not close", so listing it is always safe.
DEFAULT_TRIVIAL_TACTICS = ("decide", "simp", "omega", "trivial", "aesop")

_NAME_RE = re.compile(r"^(\s*)(theorem|lemma)\s+([^\s({\[:]+)")

# A structural fold over the elaborated type's Expr: de Bruijn indices make it
# alpha-invariant; fully-qualified constant names make it notation/namespace
# invariant. (Validated: `(n:Nat)->n+0=n` and `∀ m:ℕ, m+0=m` produce the same string.)
_CANON_DEF = r"""open Lean in
partial def leibnizCanon : Expr → String
  | .bvar i => s!"b{i}"
  | .fvar _ => "f"
  | .mvar _ => "m"
  | .sort u => s!"S({u})"
  | .const n us => s!"c:{n}/{us.length}"
  | .app f a => s!"@({leibnizCanon f} {leibnizCanon a})"
  | .lam _ t b _ => s!"L({leibnizCanon t} {leibnizCanon b})"
  | .forallE _ t b _ => s!"P({leibnizCanon t} {leibnizCanon b})"
  | .letE _ t v b _ => s!"E({leibnizCanon t} {leibnizCanon v} {leibnizCanon b})"
  | .lit l => match l with | .natVal n => s!"n{n}" | .strVal s => s!"s{s}"
  | .mdata _ e => leibnizCanon e
  | .proj tn i e => s!"j({tn}.{i} {leibnizCanon e})"
"""
_CANON_RUN = r"""open Lean in
run_cmd do
  let env ← getEnv
  let ci := (env.find? `__leibniz_candidate__).get!
  IO.println ("LEIBNIZ_CANON:" ++ leibnizCanon ci.type)
"""


def _join_proof(theorem_src: str, proof_src: str) -> str:
    """Assemble a complete Lean declaration from a statement header + a proof.

    Autoformalizers often emit theorem_src already carrying a proof body
    (``... := by sorry``). Strip any existing ``:=`` tail from the header before
    appending the intended proof, guaranteeing exactly one ``:=`` (binders use
    ``:``; the first ``:=`` is the proof assignment in a Prop statement)."""
    head = theorem_src.rstrip()
    cut = head.find(":=")
    if cut != -1:
        head = head[:cut].rstrip()
    proof = proof_src.strip()
    if not proof:
        return f"{head} := by sorry"
    return f"{head} := {proof}"


def _with_imports(imports, decl: str) -> str:
    """Prepend `import X` lines (from Expressio.imports) to a declaration."""
    lines = "\n".join(f"import {m}" for m in (imports or ()))
    return f"{lines}\n{decl}" if lines else decl


@dataclass(frozen=True)
class LeanResult:
    returncode: int
    output: str

    @property
    def has_errors(self) -> bool:
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
    persistent: bool = False
    _cache: dict[str, LeanResult] = field(default_factory=dict, repr=False)
    _cid: Optional[str] = field(default=None, repr=False)
    _workdir: Optional[str] = field(default=None, repr=False)
    _counter: int = field(default=0, repr=False)

    # --- LeanBackend Protocol -------------------------------------------------
    def compile_statement(self, expr: Expressio) -> bool:
        res = self._run_lean(_with_imports(expr.imports, _join_proof(expr.theorem_src, "by sorry")))
        return res is not None and not res.has_errors

    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        res = self._run_lean(_with_imports(expr.imports, _join_proof(expr.theorem_src, proof_src)))
        return res is not None and res.kernel_ok

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        for tac in self.trivial_tactics:
            res = self._run_lean(_with_imports(expr.imports, _join_proof(expr.theorem_src, f"by {tac}")))
            if res is not None and res.kernel_ok:
                return True
        return False

    # --- R1c: elaborator-canonical structural hash ----------------------------
    def normalize_statement(self, expr: Expressio) -> Optional[str]:
        """A structural, alpha/notation-invariant hash of the statement's elaborated
        type. Returns None if the statement does not elaborate (caller falls back to
        the textual hash)."""
        m = _NAME_RE.match(expr.theorem_src)
        if not m:
            return None
        # Rename the declaration to a fixed private name (avoids clashes like `sq`)
        # and drop any proof body — we only canonicalize the type.
        head = expr.theorem_src[: m.start(3)] + "__leibniz_candidate__" + expr.theorem_src[m.end(3):]
        head = head.split(":=")[0].rstrip()
        script = "\n".join([
            "import Lean",
            "\n".join(f"import {x}" for x in (expr.imports or ())),
            "set_option linter.style.nameCheck false",
            _CANON_DEF,
            f"{head} := sorry",
            _CANON_RUN,
        ])
        res = self._run_lean(script)
        if res is None or res.has_errors:
            return None
        for line in res.output.splitlines():
            if line.startswith("LEIBNIZ_CANON:"):
                canon = line[len("LEIBNIZ_CANON:"):]
                return hashlib.sha256(canon.encode()).hexdigest()[:16]
        return None

    # --- lifecycle (persistent mode) -----------------------------------------
    def close(self) -> None:
        if self._cid:
            subprocess.run(["docker", "rm", "-f", self._cid], capture_output=True)
            self._cid = None
        if self._workdir:
            shutil.rmtree(self._workdir, ignore_errors=True)
            self._workdir = None

    def __enter__(self) -> "LeanCliBackend":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- internals ------------------------------------------------------------
    def _run_lean(self, source: str) -> Optional[LeanResult]:
        key = hashlib.sha256(source.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        res = self._run_persistent(source) if self.persistent else self._run_oneshot(source)
        if res is not None:
            self._cache[key] = res
        return res

    def _run_oneshot(self, source: str) -> Optional[LeanResult]:
        try:
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "Thm.lean").write_text(source)
                proc = subprocess.run(
                    ["docker", "run", "--rm", "-v", f"{td}:/scratch:ro",
                     "-w", "/work/lean-project", self.image,
                     "lake", "env", "lean", "/scratch/Thm.lean"],
                    capture_output=True, text=True, timeout=self.timeout_s,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return LeanResult(proc.returncode, f"{proc.stdout}\n{proc.stderr}")

    def _ensure_container(self) -> None:
        if self._cid:
            return
        self._workdir = tempfile.mkdtemp(prefix="leibniz-lean-")
        try:
            proc = subprocess.run(
                ["docker", "run", "-d", "-v", f"{self._workdir}:/scratch:ro",
                 "-w", "/work/lean-project", self.image, "sleep", "infinity"],
                capture_output=True, text=True, timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._cid = None
            return
        if proc.returncode == 0:
            self._cid = proc.stdout.strip()
            atexit.register(self.close)

    def _run_persistent(self, source: str) -> Optional[LeanResult]:
        self._ensure_container()
        if not self._cid or not self._workdir:
            return self._run_oneshot(source)  # container unavailable -> degrade
        self._counter += 1
        name = f"Thm{self._counter}.lean"
        (Path(self._workdir) / name).write_text(source)
        try:
            proc = subprocess.run(
                ["docker", "exec", self._cid, "lake", "env", "lean", f"/scratch/{name}"],
                capture_output=True, text=True, timeout=self.timeout_s,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return LeanResult(proc.returncode, f"{proc.stdout}\n{proc.stderr}")


def available(image: str = DEFAULT_IMAGE) -> bool:
    """True iff docker and the Lean image are usable (used to skip Lean tests)."""
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
