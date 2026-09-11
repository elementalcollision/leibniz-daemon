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
  error-level diagnostics, uses no ``sorry`` / ``sorryAx``, AND has an axiom
  footprint inside ``STD_AXIOMS`` (ADR 0097). The footprint is not optional and
  not a caller's responsibility: ``#print axioms`` goes into the same file the
  kernel checks. Before ADR 0097 this returned True for a ``native_decide``
  proof — the compiled evaluator deciding, not the kernel — which on the pinned
  4.31 is enough to derive ``False`` from the Trail of Bits
  ``String.Pos.Raw.extract`` bug.
- Why an allowlist and not a ``_FORBIDDEN`` keyword scan like the Coq/Isabelle
  backends: those scan the SOURCE for laundering keywords because they have no
  cheap footprint to read. Lean prints the real closure, so the allowlist is
  strictly stronger — it catches an axiom no keyword list anticipated, including
  the auto-generated per-computation native axioms Lean has emitted since 4.29,
  whose names are derived from the theorem and match no fixed denylist.
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
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from leibniz.backends.lean_axioms import (
    _axiom_complaint,
    _report_re,
    axiom_report_text,
    _parse_axcheck,
    closes_more_than_it_opens,
    declaration_name,
    defeats_the_kernel,
    declaration_source,
    fresh_probe_name,
    import_is_safe,
    mentions_sorry,
    probe_source,
    smuggles_top_level,
    statement_head,
    statement_is_single_declaration,
)
from leibniz.propositio import Expressio

#: The pinned Lean toolchain, and the SINGLE source of truth for it. Must match
#: `lean-project/lean-toolchain` and the Mathlib `rev` in `lean-project/lakefile.toml`.
#: Everything that names a version -- image tags, Newton folios, tests -- derives from
#: this, so a pin move cannot leave a stale literal behind (ADR 0095).
KERNEL_VERSION = "v4.34.0-rc2"
DEFAULT_IMAGE = f"leibniz-lean:{KERNEL_VERSION}"
#: ADR 0097 — the kernel image plus the compiled axiom reporter (docker/lean-axcheck.Dockerfile).
#: ADR 0098 — the kernel image plus BOTH verifiers: the axiom reporter and the kernel replay
#: (docker/lean-axcheck.Dockerfile, then docker/lean4checker.Dockerfile).
VERIFY_IMAGE = f"leibniz-lean-verify:{KERNEL_VERSION}"
# Triviality tactics. A statement any of these closes ON ITS OWN is vacuous and must
# NOT be promulgated. `ring`/`nlinarith` were added (ADR 0025) after a calibration
# promulgated 32 polynomial identities (e.g. (m+3)(m+5)+1=(m+4)^2) that `ring` closes
# instantly — they slipped through because the set lacked a (non)linear-arithmetic
# decision procedure. Each tactic needs a Mathlib import; when absent it simply errors
# and is treated as "did not close", so listing it is always safe.
DEFAULT_TRIVIAL_TACTICS = ("decide", "simp", "omega", "trivial", "aesop", "ring", "nlinarith")

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


def _join_proof(theorem_src: str, proof_src: str, preamble: str = "") -> str:
    """Assemble a complete Lean declaration from a statement header + a proof.

    Autoformalizers often emit theorem_src already carrying a proof body
    (``... := by sorry``). Strip any existing ``:=`` tail from the header before
    appending the intended proof, guaranteeing exactly one ``:=`` (binders use
    ``:``; the first ``:=`` is the proof assignment in a Prop statement).

    ADR 0062: an optional operator-authored ``preamble`` (top-level defs/set_options) is prepended
    BEFORE the declaration, so a legible multi-definition amplification law discharges as ONE source.
    Empty for the discovery path (byte-identical, single-declaration ADR 0027 shape)."""
    head = statement_head(theorem_src)
    proof = proof_src.strip()
    body = f"{head} := by sorry" if not proof else f"{head} := {proof}"
    return f"{preamble.rstrip()}\n{body}" if preamble.strip() else body


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
        # BROAD by design (ADR 0097 round 2). Narrowing this to Lean's warning wording made
        # `check_source("theorem t : 2 + 2 = 5 := by sorry")` return True -- Lean writes the
        # warning with BACKTICKS, so the narrow regex matched nothing, and this path (the
        # "trusted re-check" ~20 audit scripts call) has no axiom-footprint backstop.
        return mentions_sorry(self.output)

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
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # --- LeanBackend Protocol -------------------------------------------------
    def compile_statement(self, expr: Expressio) -> bool:
        res = self._run_lean(_with_imports(expr.imports, _join_proof(expr.theorem_src, "by sorry", expr.preamble)))
        return res is not None and not res.has_errors

    def compile_with_error(self, expr: Expressio) -> tuple[bool, str]:
        """Compile the statement and return (ok, diagnostics). Powers the R4.2
        import-repair loop: a failed compile hands its Lean error back to the
        autoformalizer to fix the imports/statement."""
        res = self._run_lean(_with_imports(expr.imports, _join_proof(expr.theorem_src, "by sorry", expr.preamble)))
        if res is None:
            return (False, "lean backend unavailable")
        return (not res.has_errors, res.output)

    #: ADR 0097 — see LeanReplBackend.enforces_axiom_closure.
    enforces_axiom_closure = True

    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        """True iff the kernel accepted the proof AND its axiom footprint is clean (ADR 0097).

        `#print axioms` is appended to the SAME file the kernel checks, so the footprint cannot
        be skipped by a caller. `axiom_closure` cannot drive this backend at all (it needs the
        REPL's `_run`), which is exactly why the check has to live here rather than in a
        convention every call site repeats. Fails CLOSED on an unnamed declaration.
        """
        name = declaration_name(expr.theorem_src)
        if (not name or smuggles_top_level(proof_src)
                or closes_more_than_it_opens(proof_src)
                or not statement_is_single_declaration(expr.theorem_src)
                or not all(import_is_safe(m) for m in expr.imports)
                or defeats_the_kernel(expr.theorem_src)
                or defeats_the_kernel(proof_src)
                or defeats_the_kernel(expr.preamble)):
            return False
        # ADR 0097 round 3 -- see LeanReplBackend.check_proof.
        probe = fresh_probe_name()
        decl = probe_source(expr.theorem_src, proof_src, name, probe)
        src = f"{expr.preamble.rstrip()}\n{decl}" if expr.preamble.strip() else decl
        res = self._run_lean(_with_imports(expr.imports, src))
        if res is None or res.has_errors:
            return False
        # `res.kernel_ok` cannot be used here: its `uses_sorry` is a BROAD scan (deliberately —
        # see LeanResult.uses_sorry) and the `#print axioms <name>` this method appends echoes the
        # declaration NAME back, so a theorem called `sorry_free_addition` would DEFER silently.
        # Exclude exactly that echo, nothing else; `sorryAx` is still caught inside `mentions_sorry`.
        if mentions_sorry(res.output, ignore=_report_re(probe)):
            return False
        return bool(axiom_report_text(res.output, probe).get("ok"))

    #: ADR 0097 — this backend can answer the footprint question WITHOUT elaborating proposer
    #: syntax, so `LeanVerifier.discharge` must consult it before stamping. See
    #: `independent_axiom_footprint`.
    mint_requires_independent_check = True

    def independent_axiom_footprint(self, expr: Expressio, proof_src: str) -> Optional[dict]:
        """Read the axiom closure with the COMPILED reporter, outside the proposer's reach.

        `#print axioms` is a command, and a proof sharing its file can redefine that command's
        elaborator (`elab_rules : command | `(#print axioms $i:ident) => ...`) or simply print a
        report-shaped line. Both were demonstrated end-to-end against the pinned kernel, and both
        returned `kernel_verified=True` for a compiler-trusted proof — the second of them defeating
        a 128-bit unpredictable probe, because the hijack matches `$i:ident` and never needs to know
        the name. No amount of lexing the proof fixes that: five rounds of adversarial review each
        broke a syntactic guard.

        So this asks a different way. `lean-axcheck` is built into the image BEFORE any proposer
        text exists; it imports the compiled module and reads `Lean.collectAxioms` out of
        `ConstantInfo` data. It elaborates none of the proof's syntax, so `elab_rules` has nothing
        to hook, and it prints on a channel tagged with a nonce chosen per call.

        ADR 0098 adds a second, independent question in the same round-trip. The reporter reads
        what the environment SAYS; `lean4checker` replays that environment through a bare kernel
        and answers whether the kernel would accept it at all. Round 8 measured why both are
        needed: a `run_cmd` assembling `debug.skipKernelTC` from string fragments and `addDecl`-ing
        a self-referential `unsafe` constant of type `False` produces a genuinely EMPTY footprint,
        so the reporter passes it honestly — and no text scan can see it, because there is no
        string to match. The replay rejects it (`unknown constant 'evilConst'`, exit 1). It runs
        FIRST and short-circuits, so a footprint is never read from an environment the kernel
        would refuse.

        Returns the footprint dict, or None when either tool is unavailable — the caller treats
        None as FAIL, never as a pass. Costs ~5 s (compile + replay + query), which is why it
        gates the MINT and not every `check_proof`.
        """
        name = declaration_name(expr.theorem_src)
        if (not name or smuggles_top_level(proof_src)
                or closes_more_than_it_opens(proof_src)
                or not statement_is_single_declaration(expr.theorem_src)):
            return {"ok": False, "reason": "guard refused the source", "axioms": []}
        if not all(import_is_safe(m) for m in expr.imports):
            return {"ok": False, "reason": "import is not a bare module name", "axioms": []}
        # ADR 0097 round 6: NO probe alias. `def <probe> := @<name>` was surface syntax a smuggled
        # `macro_rules | `(@$_:ident) => ...` could rewrite, so the reporter was asked -- honestly
        # -- about the wrong constant. The declaration name now travels as ARGV instead, where no
        # macro can reach it, and the module carries the declaration and nothing else.
        decl = declaration_source(expr.theorem_src, proof_src)
        body = f"{expr.preamble.rstrip()}\n{decl}" if expr.preamble.strip() else decl
        source = _with_imports(expr.imports, body)
        nonce = fresh_probe_name()
        try:
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "Mint.lean").write_text(source)
                proc = subprocess.run(
                    ["docker", "run", "--rm", "-v", f"{td}:/scratch:ro",
                     "-w", "/work/lean-project", VERIFY_IMAGE, "bash", "-lc",
                     # Nothing proposer-derived is interpolated into this shell string any more.
                     # `Mint` is fixed and `nonce` is ours -- round 7 showed the theorem name was
                     # both a shell-injection vector and a way to mis-aim the question.
                     "cp /scratch/Mint.lean ./Mint.lean && "
                     "lake env lean -o Mint.olean Mint.lean >/dev/null 2>&1 && "
                     'export LEAN_PATH="$(lake env printenv LEAN_PATH):/work/lean-project" && '
                     # ADR 0098: the KERNEL REPLAY runs first and its failure short-circuits, so
                     # a footprint is never even read from an environment the kernel would reject.
                     "/work/lean4checker/.lake/build/bin/lean4checker Mint && "
                     f"/work/axcheck/.lake/build/bin/axcheck Mint {nonce}"],
                    capture_output=True, text=True, timeout=self.timeout_s,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None
        return _parse_axcheck(proc.stdout, nonce)

    def check_source(self, source: str) -> Optional[bool]:
        """Report the kernel verdict on a COMPLETE Lean source (helpers + theorem + proof already
        assembled). True iff it elaborates cleanly with no sorry; False if the kernel rejects it;
        None if the backend is unavailable (no docker/image). Like check_proof, this only REPORTS
        what the kernel said — it never touches Demonstratio.kernel_verified (LeanVerifier.discharge
        remains the sole writer). Used by the standalone CWC audit CLI (scripts/cwc_check.py), which
        renders a self-contained `validCWC ... = true := by decide` file; that file carries its own
        `def`s, so it must NOT go through _join_proof (which splits on the first `:=`)."""
        res = self._run_lean(source)
        return None if res is None else res.kernel_ok

    def check_proof_with_error(self, expr: Expressio, proof_src: str) -> tuple[bool, str]:
        """Like check_proof, but also return the kernel diagnostics (ADR 0029).

        Powers the agentic repair loop, mirroring compile_with_error: a failed check
        hands the kernel's complaint back to the reasoner to repair. It only REPORTS;
        kernel_verified is still written solely by LeanVerifier.discharge, which
        re-checks any ok candidate before stamping it.

        ADR 0096 build obligation 2. This predicate must MATCH `check_proof`, not be weaker than
        it. The panel gates on this and then discharges what it accepts; `proof_repair.py`'s
        `"kernel rejected a proof the pre-check accepted"` branch is dead only while the two agree.
        Tightening the mint alone would make it live, and the panel would burn rounds proposing
        `native_decide` proofs it then discards -- with no diagnostic the reasoner can act on. So
        the footprint is checked HERE too, and a dirty one is reported as an error the model can
        actually repair.
        """
        name = declaration_name(expr.theorem_src)
        if (not name or smuggles_top_level(proof_src)
                or closes_more_than_it_opens(proof_src)
                or not statement_is_single_declaration(expr.theorem_src)):
            return (False, "proof or statement opens a top-level declaration; write a term or tactic proof only")
        probe = fresh_probe_name()
        decl = probe_source(expr.theorem_src, proof_src, name, probe)
        src = f"{expr.preamble.rstrip()}\n{decl}" if expr.preamble.strip() else decl
        res = self._run_lean(_with_imports(expr.imports, src))
        if res is None:
            return (False, "lean backend unavailable")
        if res.has_errors:
            return (False, res.output)
        if mentions_sorry(res.output, ignore=_report_re(probe)):
            return (False, "proof still contains `sorry`")
        report = axiom_report_text(res.output, probe)
        if not report.get("ok"):
            return (False, _axiom_complaint(report))
        return (True, "")

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        for tac in self.trivial_tactics:
            res = self._run_lean(_with_imports(expr.imports, _join_proof(expr.theorem_src, f"by {tac}", expr.preamble)))
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
        # Thread-safe (ADR 0011): the lock guards container creation + the unique
        # filename counter + the scratch write, so persistent mode composes with the
        # concurrent prover ensemble. The long `docker exec` runs OUTSIDE the lock,
        # so checks still execute concurrently.
        with self._lock:
            self._ensure_container()
            if not self._cid or not self._workdir:
                cid = None
            else:
                self._counter += 1
                name = f"Thm{self._counter}.lean"
                (Path(self._workdir) / name).write_text(source)
                cid = self._cid
        if cid is None:
            return self._run_oneshot(source)  # container unavailable -> degrade
        try:
            proc = subprocess.run(
                ["docker", "exec", cid, "lake", "env", "lean", f"/scratch/{name}"],
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
