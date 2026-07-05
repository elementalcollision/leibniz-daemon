"""Isabelle/HOL backend — the real Isabelle kernel, run in an OrbStack/Docker container (ADR 0048).

A third *proof-edge* decider alongside Lean and Coq, built to the ``leibniz.backends.lean_cli`` contract:
it shells out to a pinned Isabelle, **REPORTS** what ``isabelle build`` said, and never touches
``Demonstratio.kernel_verified`` — ``IsabelleVerifier.discharge`` is the sole writer. Until the operator
admits ``"IsabelleVerifier.discharge"`` to ``trust.KERNEL_PRODUCERS`` (the deferred, PreToolUse-guarded
edit; see ADR 0048 §4.2 / ADR 0045 precedent), an Isabelle proof edge is still rejected structurally at
promotion — live for verification-amplification (audit tier), dormant for promulgation.

Trust rule. Under the default ``quick_and_dirty=false`` an ``isabelle build`` **hard-errors** on ``sorry``
("Cheating requires quick_and_dirty mode!"), so that laundering route cannot build. But ``sorry`` desugars to
the ``Skip_Proof.cheat_tac`` oracle, which — invoked directly through the ``tactic`` proof method or any
``ML``/``oracle`` command — closes **any** goal (even ``2+2=5``), exits 0, and emits no error marker (found
by adversarial review, 2026-07-05). So a theory is kernel-verified iff:
  (1) ``isabelle build`` exits 0 (rejecting ``sorry`` and any unfinished proof); AND
  (2) the source carries no trust-defeating construct — ``sorry`` / ``oops`` / ``axiomatization`` /
      ``quick_and_dirty`` **and** the arbitrary-code escape hatches ``tactic`` / ``ML`` / ``ML_prf`` /
      ``ML_val`` / ``ML_command`` / ``ML_file`` / ``oracle`` / ``Skip_Proof`` / ``cheat_tac``. The scan runs
      on the source with ``(* … *)`` comments and DOC cartouches stripped but PROOF cartouches KEPT, so a
      cheat hidden inside ``by (tactic \<open>…\<close>)`` is still caught.

The theory is checked as a one-theory session ``S = HOL + theories S`` built on the image's prebuilt HOL
heap (so a check is ~seconds, not a full HOL rebuild). The default image is native **arm64**
(``makarius/isabelle:Isabelle2025_ARM``) so no Rosetta is needed on Apple Silicon; ``platform`` stays None
(override both for an amd64 host). Its ENTRYPOINT is ``isabelle`` itself, so the container is invoked as
``build -D <dir>``. The session dir is a host tempdir bind-mounted **read-only** (build writes heaps to the
container's own ``$ISABELLE_HEAPS``, never back to the mount); it is chmod 0755 so the container's non-root
``isabelle`` user can traverse it.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from leibniz.propositio import Expressio

# Native arm64 (pinned) — makarius publishes `<version>_ARM` variants; on Apple Silicon this avoids Rosetta.
# Override `image`/`platform` for an amd64 host (e.g. image="makarius/isabelle:Isabelle2025", platform="linux/amd64").
DEFAULT_IMAGE = "makarius/isabelle:Isabelle2025_ARM"

# Trust-defeating constructs. Beyond the obvious hole-leavers (sorry/oops) and axiom-introducers
# (axiomatization) and the cheat re-enabler (quick_and_dirty), we MUST forbid the arbitrary-code escape
# hatches: `sorry` desugars to `Skip_Proof.cheat_tac`, which — invoked directly via the `tactic` proof
# method or any `ML*`/`oracle` command — closes ANY goal (even `2+2=5`), exits 0, and emits no error. A
# keyword blocklist alone can't be exhaustive, but banning the ML/oracle surface removes the general escape.
_FORBIDDEN = ("sorry", "oops", "axiomatization", "quick_and_dirty",
              "tactic", "ML", "ML_prf", "ML_val", "ML_command", "ML_file",
              "oracle", "Skip_Proof", "SkipProof", "cheat_tac")
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN) + r")\b")
# The `theory NAME` DECLARATION begins a line (after optional whitespace) — anchor there so the word
# "theory" inside a comment (e.g. "one-theory session") can't be mistaken for the declaration.
_THEORY_NAME_RE = re.compile(r"(?m)^[ \t]*theory\s+([A-Za-z][A-Za-z0-9_']*)")
_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)
# DOC cartouches only (text/section/…/\<comment> \<open>…\<close>) are inert prose to strip. PROOF cartouches
# (e.g. `by (tactic \<open>…\<close>)`) are KEPT so an escape hatch hidden inside one is still scanned.
_DOC_CARTOUCHE_RE = re.compile(
    r"(?:\btext\b|\btxt\b|\bsection\b|\bsubsection\b|\bsubsubsection\b|\bchapter\b|\bparagraph\b|\\<comment>)"
    r"\s*\\<open>.*?\\<close>", re.DOTALL)


def _strip(src: str) -> str:
    """Drop inert PROSE — ``(* … *)`` comments and DOC cartouches — so a keyword named in documentation isn't
    mistaken for a proof step. PROOF cartouches are KEPT, so an ML/oracle/cheat escape hatch hidden in one is
    still caught by the forbidden scan; a real `sorry`/`oops`/`tactic` in code survives."""
    return _DOC_CARTOUCHE_RE.sub(" ", _COMMENT_RE.sub(" ", src))


@dataclass(frozen=True)
class IsabelleResult:
    returncode: int
    output: str
    source: str = ""

    @property
    def has_errors(self) -> bool:
        return self.returncode != 0 or "*** " in self.output

    @property
    def uses_forbidden(self) -> bool:
        # Scan CODE only (comments/cartouches stripped): a keyword named in documentation is inert. The
        # real anti-cheat guard is the build itself (quick_and_dirty=false hard-errors on `sorry`); this
        # lexical scan additionally blocks `oops` (which the build tolerates) and added axiomatizations.
        return bool(_FORBIDDEN_RE.search(_strip(self.source)))

    @property
    def kernel_ok(self) -> bool:
        return (not self.has_errors) and (not self.uses_forbidden)


def _assemble(expr: Expressio, proof_src: str) -> str:
    """Assemble a complete Isabelle theory from an Isabelle Expressio + a proof. `imports` are theory
    names (the Lean default "Mathlib" is skipped; Main is always included); `theorem_src` is an Isar
    statement header (`lemma foo: "..."`) and `proof_src` its proof (`by simp`, `proof ... qed`, ...)."""
    extra = [m for m in (expr.imports or ()) if m and m not in ("Mathlib", "Main")]
    imports = " ".join(["Main", *extra])
    body = f"{expr.theorem_src.strip()}\n{(proof_src or '').strip()}".strip()
    return f"theory Scratch imports {imports} begin\n{body}\nend\n"


@dataclass
class IsabelleDockerBackend:
    """Report-only Isabelle runner. Mirrors LeanCliBackend's surface so an IsabelleVerifier can discharge
    through it exactly as LeanVerifier discharges through LeanCliBackend."""

    image: str = DEFAULT_IMAGE
    platform: Optional[str] = None   # None = native (arm64 image on arm64 host); set "linux/amd64" to emulate
    timeout_s: int = 300
    _cache: dict[str, IsabelleResult] = field(default_factory=dict, repr=False)

    # --- proof-edge surface (mirrors LeanBackend) -----------------------------
    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        res = self._run(_assemble(expr, proof_src))
        return res is not None and res.kernel_ok

    def check_source(self, source: str) -> Optional[bool]:
        """Report the kernel verdict on a COMPLETE Isabelle theory (`theory NAME ... begin ... end`).
        True iff the session builds clean and carries no cheating construct; False if the build rejects
        it; None if the backend is unavailable. Never touches kernel_verified."""
        res = self._run(source)
        return None if res is None else res.kernel_ok

    def check_source_with_detail(self, source: str) -> Optional[dict]:
        res = self._run(source)
        if res is None:
            return None
        return {
            "verified": res.kernel_ok,
            "returncode": res.returncode,
            "has_errors": res.has_errors,
            "uses_forbidden": res.uses_forbidden,
            "output_tail": "\n".join(res.output.splitlines()[-8:]),
        }

    def compile_statement(self, expr: Expressio) -> bool:
        """Syntactic validity of the statement. We cannot use `sorry` (build rejects it), so probe with a
        trivial-but-real discharge and treat a genuine build error about the PROOF (not the statement) as
        'statement is well-formed'. Conservative: returns True unless the header itself fails to parse."""
        src = _assemble(expr, "by (rule refl)")
        res = self._run(src)
        if res is None:
            return False
        # A parse/type error in the header shows up before any proof step is attempted.
        return "Inner syntax error" not in res.output and "Undefined" not in res.output

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        for tac in ("by simp", "by auto", "by blast", "by arith"):
            res = self._run(_assemble(expr, tac))
            if res is not None and res.kernel_ok:
                return True
        return False

    # --- internals ------------------------------------------------------------
    def _run(self, source: str) -> Optional[IsabelleResult]:
        key = hashlib.sha256(source.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        m = _THEORY_NAME_RE.search(_strip(source))
        name = m.group(1) if m else "Scratch"
        try:
            with tempfile.TemporaryDirectory(prefix="leibniz-isabelle-") as td:
                os.chmod(td, 0o755)  # the container's non-root `isabelle` user must traverse the mount
                (Path(td) / "ROOT").write_text(f"session {name} = HOL +\n  theories {name}\n")
                (Path(td) / f"{name}.thy").write_text(source)
                for p in Path(td).iterdir():
                    os.chmod(p, 0o644)
                cmd = ["docker", "run", "--rm"]
                if self.platform:
                    cmd += ["--platform", self.platform]
                cmd += ["-v", f"{td}:/work/sess:ro", self.image, "build", "-D", "/work/sess"]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        res = IsabelleResult(proc.returncode, f"{proc.stdout}\n{proc.stderr}", source=source)
        self._cache[key] = res
        return res


def available(image: str = DEFAULT_IMAGE) -> bool:
    """True iff docker and the Isabelle image are usable (used to skip Isabelle tests when Docker is down)."""
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
