"""Construction-intake soundness primitives (ADR 0045 §2.1/§2.3 — the non-trust scaffolding).

These implement the corrected design's CRITICAL fixes (the adversarial review found the first draft
unsound). They are pure functions — no kernel, no Propositio, no trust edit — so they are safe to land
ahead of the operator-gated wiring (the `discharge` construction path + the `trust.py` producer).

- LOCKED_*_PRELUDE: the operator-owned helper definitions, taken byte-identically from the verifiers
  (single source of truth). In the integration these ride OUTSIDE the witness-influenced statement (a
  fixed prelude), so a witness can never hollow `validCovering`/`validCWC` to make `by decide` stamp a
  false bound (review CRITICAL #1).
- theorem_structural_guard: a construction's Expressio.theorem_src must be EXACTLY one
  `theorem … := by decide` over witness LITERALS — no `def`/`axiom`/`macro`/`native_decide`/…, one
  `theorem`, one `:=` (so `discharge`'s first-`:=` split is unambiguous — review CRITICAL/HIGH #2).
- canonical_claim: the SINGLE source of truth for the tri-edge binding (review CRITICAL #3) — the
  (domain, params, size, statement) derived FROM the witness via the operator template; proof,
  faithfulness, and novelty must all bind to THIS, so no edge can attest a different statement. `size`
  is always len(witness), never a tool-supplied number (E7).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import covering_verify  # noqa: E402
import probe_beta_cwc_pilot  # noqa: E402

# Operator-owned, byte-pinned to the verifiers (test_construction_intake asserts no drift).
LOCKED_COVERING_PRELUDE = covering_verify._LEAN_HELPERS
LOCKED_CWC_PRELUDE = probe_beta_cwc_pilot._LEAN_HELPERS

# Tokens that must NEVER appear in a construction theorem_src (defs live in the locked prelude; the
# proof is a plain kernel `decide`; nothing may route to host code or smuggle structure).
_FORBIDDEN = ("def ", "axiom ", "macro ", "notation ", "set_option", "instance ", "@[", "sorry",
              "native_decide", "unsafe", "import ", "#eval", "#check", "partial ", "opaque ")


def theorem_structural_guard(theorem_src: str) -> tuple[bool, str]:
    """True iff theorem_src is a single clean `theorem … := <proof>` over literals (no defs/axioms/etc.,
    one theorem, one ':='). The locked prelude is supplied separately, never here.

    WARNING — NOT TRUST-PATH READY (internal adversarial review, 2026-06-30). This is a DENYLIST and was
    shown BYPASSABLE: it admits run_cmd / elab / macro_rules / inductive / structure / class / abbrev /
    attribute / namespace / section / open and other declaration/metaprogram forms (which need neither a
    'theorem ' token nor a ':='), enabling axiom-injection that makes the kernel stamp a FALSE bound.
    Before this gates any PROOF edge it MUST be replaced by an ALLOWLIST parse (exactly one
    `theorem <id> : validCovering|validCWC <lits> = true := by decide`, verified by an Environment diff)
    PLUS an empty-axiom-closure check PLUS an import-free source. It is currently wired to NOTHING in a
    trust path (no discharge_construction exists). See docs/external-witness-brief-construction-proof-edge.md."""
    s = theorem_src
    for tok in _FORBIDDEN:
        if tok in s:
            return False, f"forbidden token {tok!r} in theorem_src (defs/structure must live in the locked prelude)"
    if s.count("theorem ") != 1:
        return False, f"expected exactly one theorem, found {s.count('theorem ')}"
    if s.count(":=") != 1:
        return False, f"expected exactly one ':=' (the proof assignment), found {s.count(':=')}"
    return True, "ok"


def canonical_claim(witness: dict) -> dict:
    """Derive the canonical (domain, cell, params, size, statement) from a witness via the operator
    template — the single source of truth for the tri-edge statement binding. `size` = len(witness),
    never tool-supplied (E7). Raises on an unknown domain."""
    domain = (witness.get("domain") or "").strip().lower()
    if domain == "covering":
        v, k, t = int(witness["v"]), int(witness["k"]), int(witness["t"])
        b = len(witness["blocks"])
        return {"domain": "covering", "cell": f"C({v},{k},{t})", "params": (v, k, t), "size": b,
                "statement": f"C({v},{k},{t}) <= {b}"}
    if domain == "cwc":
        n, d, w = int(witness["n"]), int(witness["d"]), int(witness["w"])
        m = len(witness["code"])
        return {"domain": "cwc", "cell": f"A({n},{d},{w})", "params": (n, d, w), "size": m,
                "statement": f"A({n},{d},{w}) >= {m}"}
    raise ValueError(f"unknown construction domain {domain!r}")
