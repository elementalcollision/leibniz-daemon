"""The discovery frontier (ADR 0018) — steering conjecture toward the band of the
*novel-yet-tractable*.

The daemon runs end-to-end but rarely promulgates: conjectures land trivial (killed
by the novelty / decision-procedure gates) or too hard (the prover exhausts its
budget, UNPROVEN). ADR 0009 closed the learning loop on the *selection* side (KFM
recombines survivors); this closes it on the *proposal* side, where the text is
actually generated.

Everything here is **proposal-side** and writes no trust edge: it shapes what the
conjecturer is asked, scores stepping stones, and proposes weaker reformulations —
but every candidate it influences still runs the full cheap gates and the kernel's
N+1 consensus. The kernel and Z3 still decide; the trust boundary is untouched.

Pieces:
- ``difficulty`` — a mechanical structural proxy in [0,1] (quantifiers, implication
  depth, operators, length). No LLM.
- ``DiscoveryNotebook`` — a bounded, rolling memory of recent *outcomes* distilled
  into a steering block: proven shapes to emulate, trivial/known shapes to avoid,
  too-hard shapes to weaken.
- ``FrontierController`` — a thermostat: it nudges a target difficulty band from the
  recent proof-success rate (a curriculum — ease off when nothing proves, push when
  everything is trivial).
- ``weakening_seeds`` — turn UNPROVEN near-misses into strictly-weaker re-conjecture
  seeds (lemma mining), fed back through the same gated pipeline.
- ``quality`` — a graded stepping-stone score so a near-tractable miss outranks a
  wild one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from leibniz.propositio import Propositio
from leibniz.structural import congruence_signature
from leibniz.types import FinishReason

# Where the learned difficulty band + outcome notebook persist across runs (gitignored,
# per-machine). Persisting the notebook (ADR 0023) means near-misses accumulate across
# runs, so weaken-and-retry keeps grinding the same UNPROVEN frontier toward a proof.
_DEFAULT_FRONTIER = Path(__file__).resolve().parent.parent / ".leibniz" / "frontier.json"
_DEFAULT_NOTEBOOK = Path(__file__).resolve().parent.parent / ".leibniz" / "notebook.json"
# ADR 0034 Stage 1: curated novel-yet-elementary FLAVOUR anchors (checked in, operator-editable).
_DEFAULT_EXEMPLARS = Path(__file__).resolve().parent.parent / "corpus" / "novelty_exemplars.json"
_FAMILY_CAP = 64  # bound the persisted family histogram so it can't grow without limit


def _family(claim_property: str | None) -> tuple[str, str] | None:
    """A COARSE family key + human descriptor for a claim, from its congruence signature: the
    relop KIND and the modulus, with the polynomial DROPPED. This is the genre-hop unit — e.g.
    "== modular claims modulo 2" groups every divisibility-by-2 fact regardless of which
    polynomial, which is exactly the clustering measured in organic5 (10 promulgations spread
    across shapes but concentrated on `== mod 2`). A genuinely different KIND of mod-2 claim — a
    residue-SET characterization `n^2 % 2 in {…}` — has relop `in`, so it is a DISTINCT family and
    survives the nudge. None when the property is absent or outside the recognized DSL shapes (no
    family -> no kill). Proposal-side steering only; gates nothing (ADR 0034 §6).

    Deliberately coarse: the ADR records that a family-level kill only lengthens the genre-hop (it
    is the delivery vehicle for Stage 2, not a cure). A too-fine key would never fire across
    shapes; this one fires on the real cluster. It only ever STEERS — the conjecturer may still
    propose a killed family, and the gates + kernel still decide."""
    sig = congruence_signature(claim_property) if claim_property else None
    if sig is None:
        return None
    relop, m = sig[0], sig[1]
    return f"{relop}|{m}", f"{relop} modular claims modulo {m}"


def load_novelty_exemplars(path: Union[str, Path, None] = None) -> list[str]:
    """Load curated novel-yet-elementary FLAVOUR anchors (ADR 0034 Stage 1) as short steering
    lines. These are operator-curated reference points modelling a DIFFERENT structure from the
    textbook divisibility genre (e.g. characterizing a residue SET) — shown to the conjecturer
    as context, never proposed verbatim, never a gate. A missing/corrupt file yields an empty
    list (steering unchanged), so a fresh checkout / CI behaves exactly as before."""
    try:
        data = json.loads(Path(path or _DEFAULT_EXEMPLARS).read_text())
    except (OSError, ValueError, TypeError):
        return []
    out: list[str] = []
    # Defensive (matches from_dict): a missing key, explicit null, or a non-list payload (a
    # forged/truncated file) all yield [] — never a crash, never iterating a string's chars.
    raw = data.get("exemplars") if isinstance(data, dict) else None
    for e in (raw if isinstance(raw, list) else []):
        if isinstance(e, dict) and e.get("statement"):
            cp = e.get("claim_property")
            out.append(str(e["statement"]) + (f" [{cp}]" if cp else ""))
        elif isinstance(e, str) and e.strip():
            out.append(e.strip())
    return out


def novelty_exemplar_properties(path: Union[str, Path, None] = None) -> list[str]:
    """The curated exemplars' canonical `claim_property` predicates (ADR 0034 Stage 2). Used to
    EXCLUDE exemplars from the pattern-miner's pool so a fact already injected as steering context
    is not also mined (double-injection inflates apparent diversity). Missing/corrupt -> []."""
    try:
        data = json.loads(Path(path or _DEFAULT_EXEMPLARS).read_text())
    except (OSError, ValueError, TypeError):
        return []
    raw = data.get("exemplars") if isinstance(data, dict) else None
    return [str(e["claim_property"]) for e in (raw if isinstance(raw, list) else [])
            if isinstance(e, dict) and e.get("claim_property")]


# Outcomes that mean "do not propose shapes like this again" (dead ends).
_AVOID = frozenset({
    FinishReason.KNOWN, FinishReason.TRIVIAL, FinishReason.REFUTED,
    FinishReason.GAMED, FinishReason.UNFAITHFUL, FinishReason.MALFORMED,
})

_QUANTIFIERS = ("forall", "∀", "exists", "∃")
_IMPLIES = ("->", "→", "↔", "<->")
_OPERATORS = ("+", "*", "^", "<=", "≤", ">=", "≥", "<", ">", "%", "/", "∑", "∏", "∫")


def _statement_src(prop: Propositio) -> str:
    """The most formal text available — the Lean statement if formalized, else the
    human claim (difficulty is well-defined even for early-quarantined candidates)."""
    if prop.expressio and prop.expressio.theorem_src:
        return prop.expressio.theorem_src
    return prop.enuntiatio.statement if prop.enuntiatio else ""


def difficulty(prop: Propositio) -> float:
    """A mechanical, pre-proof structural difficulty proxy in [0, 1].

    Not a truth — a cheap proxy good enough to *target a band* and to *grade*
    stepping stones. Combines quantifier count, implication depth, operator
    density, and length. Deterministic; no LLM."""
    src = _statement_src(prop)
    if not src:
        return 0.0
    quant = sum(src.count(q) for q in _QUANTIFIERS)
    impl = sum(src.count(i) for i in _IMPLIES)
    ops = sum(src.count(o) for o in _OPERATORS)
    length = min(1.0, len(src) / 200.0)
    raw = (
        0.30 * min(1.0, quant / 3.0)
        + 0.25 * min(1.0, impl / 3.0)
        + 0.20 * min(1.0, ops / 8.0)
        + 0.25 * length
    )
    return round(min(0.999, raw), 3)


def quality(prop: Propositio) -> float:
    """Graded archive quality (replaces the coarse {1.0, 0.5, 0.0}).

    A promulgated law is 1.0. A faithful-but-unproven stepping stone is graded by
    how *close to tractable* it looks — a near-miss (low difficulty, yet the prover
    failed) is a more promising parent than a wild open-problem shape, so it scores
    higher. Dead ends are 0.0."""
    if prop.promulgated or prop.finish_reason is FinishReason.PROMULGATED:
        return 1.0
    if prop.finish_reason is FinishReason.UNPROVEN:
        # Peak at a MODERATE (frontier) difficulty, falling off toward both extremes:
        # a genuine near-miss outranks BOTH a vacuous trivially-shaped statement and a
        # wild open-problem shape. (Plain `1 - difficulty` rewarded simpler text, so a
        # near-vacuous statement could outrank a real near-miss — ADR 0018 review.)
        # Always in 0.40–0.60, strictly below a real proof's 1.0.
        peak = 0.45
        closeness = 1.0 - abs(difficulty(prop) - peak) / max(peak, 1.0 - peak)
        return round(0.40 + 0.20 * max(0.0, closeness), 3)
    return 0.0


@dataclass
class DiscoveryNotebook:
    """A bounded, rolling memory of recent outcomes, distilled into a steering block
    the conjecturer is given as context. Proposal-side only."""

    capacity: int = 6
    proven: list[str] = field(default_factory=list)    # emulate these shapes
    too_hard: list[str] = field(default_factory=list)  # weaken these
    avoid: list[str] = field(default_factory=list)     # don't re-propose these
    # ADR 0034 Stage 1: family-level genre steering (proposal-side context; gates nothing).
    # `genre_kill` names whole FAMILIES the daemon has repeatedly PROVED (the genre-hop
    # signature) so the conjecturer is nudged to a structurally different shape; `exemplars`
    # are curated novel-yet-elementary FLAVOUR anchors (loaded from corpus/novelty_exemplars.json,
    # NOT the ledger). `_family_counts` is the per-family proof histogram behind genre_kill.
    genre_kill: list[str] = field(default_factory=list)
    exemplars: list[str] = field(default_factory=list)
    genre_capacity: int = 6      # bound the kill list (ADR 0034 §9: <=6)
    genre_threshold: int = 3     # proven instances of a family before it is declared exhausted
    _family_counts: dict = field(default_factory=dict)

    @staticmethod
    def _push(bucket: list[str], item: str, cap: int) -> None:
        item = (item or "").strip()
        if not item or item in bucket:
            return
        bucket.append(item)
        if cap >= 1:
            del bucket[:-cap]  # keep only the most recent `cap`
        else:
            bucket.clear()  # cap<=0 disables the notebook (del bucket[:-0] would be a no-op)

    def record(self, prop: Propositio, reason: FinishReason | None = None) -> None:
        stmt = prop.enuntiatio.statement if prop.enuntiatio else ""
        if not stmt:
            return
        # The daemon resolves an absent finish_reason to UNPROVEN for the cycle; honour
        # that resolution here so a reached-but-unproven candidate is mined, not lost.
        r = reason if reason is not None else prop.finish_reason
        de = prop.demonstratio
        kernel_proved = bool(de and de.kernel_verified)
        # A kernel-proved shape is a *tractable* shape to emulate — even if it was held
        # back at promotion (OVER_BUDGET): the proof was real, only the judged-
        # faithfulness budget refused it (ADR 0018 review).
        if kernel_proved or prop.promulgated or r is FinishReason.PROMULGATED:
            self._push(self.proven, stmt, self.capacity)
            self._note_family(prop)  # ADR 0034 Stage 1: track proven FAMILIES for genre-kill
        elif r is FinishReason.UNPROVEN:
            self._push(self.too_hard, stmt, self.capacity)
        elif r in _AVOID:
            self._push(self.avoid, stmt, self.capacity)

    def _note_family(self, prop: Propositio) -> None:
        """Count this PROVEN claim's coarse family; once a family is clearly exhausted
        (>= genre_threshold proofs) promote it to the bounded genre_kill list. Proposal-side
        steering only — it changes the prompt, never a verdict."""
        cp = prop.enuntiatio.claim_property if prop.enuntiatio else None
        fam = _family(cp)
        if fam is None:
            return
        key, descriptor = fam
        self._family_counts[key] = self._family_counts.get(key, 0) + 1
        if len(self._family_counts) > _FAMILY_CAP:  # evict the lowest-count family
            self._family_counts.pop(min(self._family_counts, key=self._family_counts.get), None)
        if (self._family_counts[key] >= self.genre_threshold
                and descriptor not in self.genre_kill
                and len(self.genre_kill) < self.genre_capacity):
            self.genre_kill.append(descriptor)

    def steering(self) -> str:
        """A compact instruction block for the CONJECTURE prompt. Empty until there
        is something to learn from (so a cold start is unchanged)."""
        lines: list[str] = []
        if self.proven:
            lines.append("Recently PROVEN here (emulate this shape/difficulty): "
                         + "; ".join(self.proven[-3:]))
        if self.exemplars:  # ADR 0034 Stage 1: positive flavour anchors (a DIFFERENT structure)
            lines.append("For a sense of NOVEL-yet-elementary FLAVOUR — reach for this KIND of "
                         "claim (a different STRUCTURE), do NOT submit these verbatim: "
                         + "; ".join(self.exemplars))
        if self.avoid:
            lines.append("Recently TRIVIAL or already KNOWN (do NOT re-propose these "
                         "or close variants): " + "; ".join(self.avoid[-3:]))
        if self.genre_kill:  # ADR 0034 Stage 1: family-level exhaustion (coarser than `avoid`)
            lines.append("EXHAUSTED FAMILIES — you have already proved many of these; STOP "
                         "proposing this KIND and switch to a structurally different claim: "
                         + "; ".join(self.genre_kill))
        if self.too_hard:
            lines.append("Recently TOO HARD to prove (propose something in reach, or a "
                         "weaker cousin): " + "; ".join(self.too_hard[-3:]))
        return ("Lessons from the ledger so far:\n- " + "\n- ".join(lines)) if lines else ""

    # --- persistence (ADR 0023): carry accumulated near-misses across runs so the
    # weaken-and-retry loop keeps working the same frontier instead of forgetting it.
    def to_dict(self) -> dict:
        # exemplars are NOT persisted — they are reloaded from the curated corpus file each run.
        return {"proven": list(self.proven), "too_hard": list(self.too_hard),
                "avoid": list(self.avoid), "genre_kill": list(self.genre_kill),
                "family_counts": dict(self._family_counts)}

    @classmethod
    def from_dict(cls, d: dict, capacity: int = 6) -> "DiscoveryNotebook":
        nb = cls(capacity=capacity)
        if not isinstance(d, dict):
            return nb  # a non-dict payload (forged/truncated) -> fresh, never a crash
        for bucket, key in ((nb.proven, "proven"), (nb.too_hard, "too_hard"), (nb.avoid, "avoid")):
            vals = d.get(key)
            for stmt in (vals if isinstance(vals, list) else []):  # a str bucket would iterate chars
                cls._push(bucket, str(stmt), capacity)
        # ADR 0034 Stage 1: restore genre steering (defensive against a forged/truncated payload).
        gk = d.get("genre_kill")
        for desc in (gk if isinstance(gk, list) else [])[:nb.genre_capacity]:
            if str(desc) not in nb.genre_kill:
                nb.genre_kill.append(str(desc))
        fc = d.get("family_counts")
        if isinstance(fc, dict):
            for k, v in list(fc.items())[:_FAMILY_CAP]:
                try:
                    nb._family_counts[str(k)] = int(v)
                except (TypeError, ValueError):
                    continue
        return nb

    def save(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict()))

    @classmethod
    def load(cls, path: Union[str, Path, None] = None, capacity: int = 6) -> "DiscoveryNotebook":
        """Resume the notebook from disk; a missing/corrupt file yields a fresh one —
        so a cold start (or CI) behaves exactly as before."""
        try:
            return cls.from_dict(json.loads(Path(path or _DEFAULT_NOTEBOOK).read_text()), capacity)
        except (OSError, ValueError, TypeError):
            return cls(capacity=capacity)


@dataclass
class FrontierController:
    """A thermostat on conjecture difficulty: a curriculum holding a target proof-
    SUCCESS RATE. It steers the proposal band so the tractable tail of the cloud
    overlaps the prover's (unknown) reach — it does not claim to centre on it.

    Two robustness properties beyond a plain deadband (ADR 0018 review):
    - PROPORTIONAL homing: the step shrinks as the success rate nears the aim, so it
      settles smoothly instead of freezing at the first in-band rate or oscillating.
    - RE-EXPLORATION: if it pins a bound with zero success (a narrow window was
      overshot), it jumps to the opposite half and searches again — it never stays
      stuck at the floor forever.
    Proposal-side only; the band is just context for the conjecturer."""

    target: float = 0.45          # band centre in [0,1]
    window: int = 8               # outcomes considered
    aim: float = 0.35             # desired proof-success rate (exploration setpoint)
    gain: float = 0.30            # proportional gain on the rate error
    floor: float = 0.15
    ceil: float = 0.85
    _recent: list[bool] = field(default_factory=list)
    _jumps: int = 0

    def record(self, proved: bool) -> None:
        self._recent.append(bool(proved))
        del self._recent[:-self.window]

    def success_rate(self) -> float:
        return (sum(self._recent) / len(self._recent)) if self._recent else 0.0

    def update(self) -> None:
        """Retune the target from the recent success rate. Acts only on a full enough
        window so it doesn't lurch on one outcome."""
        if len(self._recent) < max(3, self.window // 2):
            return
        rate = self.success_rate()
        at_floor = self.target <= self.floor + 1e-9
        at_ceil = self.target >= self.ceil - 1e-9
        # Re-exploration: pinned at a bound with nothing proving -> the tractable band
        # was overshot. Jump to the opposite half, nudged by a deterministic offset that
        # varies per jump so successive sweeps probe different alignments and a narrow
        # window is eventually straddled (no permanent pin, no limit cycle).
        if rate == 0.0 and (at_floor or at_ceil):
            self._jumps += 1
            base = 0.65 if at_floor else 0.35
            jitter = (0.0, 0.08, -0.08, 0.04, -0.04)[self._jumps % 5]
            self.target = round(min(self.ceil, max(self.floor, base + jitter)), 3)
            self._recent.clear()
            return
        # Proportional homing: rate below aim (too hard) -> easier; above -> harder.
        err = self.aim - rate
        if abs(err) > 0.05:
            self.target = round(min(self.ceil, max(self.floor, self.target - self.gain * err)), 3)

    def band(self) -> str:
        lo, hi = max(0.0, self.target - 0.12), min(1.0, self.target + 0.12)
        return (f"Aim for difficulty ~{self.target:.2f} (band {lo:.2f}–{hi:.2f}; "
                "0 = decidable triviality, 1 = open problem). Prefer claims provable "
                "by standard Mathlib tactics.")

    # --- persistence (ADR 0019 follow-up): carry the learned band across runs -----
    def to_dict(self) -> dict:
        """The learned STATE only (not the tunable aim/gain/bounds)."""
        return {"target": self.target, "recent": list(self._recent), "jumps": self._jumps}

    @classmethod
    def from_dict(cls, d: dict) -> "FrontierController":
        if not isinstance(d, dict):
            return cls()  # a non-dict payload (forged/truncated) -> fresh, never a crash
        fc = cls(target=float(d.get("target", 0.45)))
        rec = d.get("recent")
        fc._recent = [bool(x) for x in (rec if isinstance(rec, list) else [])][-fc.window:]
        fc._jumps = int(d.get("jumps", 0))
        return fc

    def save(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict()))

    @classmethod
    def load(cls, path: Union[str, Path, None] = None) -> "FrontierController":
        """Resume the band from disk; a missing/corrupt file yields a fresh default —
        so a cold start (or CI) behaves exactly as before."""
        try:
            return cls.from_dict(json.loads(Path(path or _DEFAULT_FRONTIER).read_text()))
        except (OSError, ValueError, TypeError):
            return cls()


_WEAKEN_MARK = "STRICTLY WEAKER"


def weakening_seeds(statements: list[str], k: int = 2) -> list[str]:
    """Turn UNPROVEN near-misses into strictly-weaker re-conjecture seeds (lemma
    mining). Each weakened variant still runs the full novelty/faithfulness gates and
    the kernel — a trivial weakening is caught, a provable non-trivial one is a real
    (if modest) discovery and a stepping stone.

    Echo guard (ADR 0018 review): never weaken a statement that already carries the
    weakening instruction. This kills the compounding loop a verbatim-echoing provider
    could otherwise drive. (For an honest provider a weakened *claim* carries no marker,
    so legitimate progressive weakening across cycles is unaffected.)

    Targets the MOST RECENT k near-misses (ADR 0023): the freshest UNPROVEN candidates
    — the ones just seen to reach proof yet not close — are the best retry candidates,
    and with the notebook now persisted they accumulate across runs."""
    if k <= 0:
        return []  # NB: fresh[-0:] is the WHOLE list, not none — guard k explicitly
    fresh = [s for s in statements if _WEAKEN_MARK not in s]
    return [
        f"Propose a {_WEAKEN_MARK} but still non-trivial and novel variant of this "
        "claim that is more likely provable — add a hypothesis, specialize a "
        f"variable, or bound a quantifier: {s}"
        for s in fresh[-k:]
    ]


def steer(seed: str, notebook: DiscoveryNotebook | None, frontier: FrontierController | None) -> str:
    """Compose the conjecture context: the raw seed plus any ledger lessons and the
    target difficulty band. Returns the seed unchanged when there is nothing to add
    (cold start), so behaviour is identical until the daemon has learned something."""
    parts = [p for p in (
        notebook.steering() if notebook else "",
        frontier.band() if frontier else "",
    ) if p]
    if not parts:
        return seed
    return "\n\n".join(parts) + f"\n\nSeed: {seed}"
