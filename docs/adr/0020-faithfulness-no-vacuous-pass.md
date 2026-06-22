# ADR 0020 — Faithfulness gate: refuse vacuous passes (encodability gate) (Accepted)

- Status: **Accepted** (implemented 2026-06-22)
- Date: 2026-06-22
- Related: ADR 0002 (faithfulness gate), ADR 0004 (structured claim contract),
  ADR 0010 (probe table), ADR 0019 (live calibration that surfaced this).
  `leibniz/probes.py`, `leibniz/backends/smt_z3.py`. Non-guarded (the guarded
  `gates/faithfulness.py` is untouched). Roadmap: Tier 1 (faithfulness).

## Context

The first live calibration (ADR 0019) showed **10/10 conjectures passing
faithfulness** and reaching proof. Investigation found the passes were **vacuous**.

The faithfulness DSL (`smt_z3.py`) is a single-variable arithmetic fragment: `n`,
integer literals, `+ − *`, comparisons, and/or/not. Anything richer — `^`, a second
variable, a function (`Nat.log`, `factorial`), division — raises `PredicateError`,
and `_search` deliberately degrades to `None` ("no witness") rather than crashing the
gate. The coverage probe (ADR 0010) reads `find_gaming_witness(...) is None` as "no
coverage gap → MECHANICAL PASS".

So for any conjecture whose structured contract is richer than single-`n` arithmetic
— i.e. essentially every real conjecture — the gaming-witness silently fails to
encode and the probe **passes vacuously**. The gate certified faithfulness it never
checked. This is precisely the residual ADR 0002 exists to guard: a kernel-valid
proof of a *mis-stated* theorem, most authoritative when most wrong.

## Decision

The probe must **DEFER (return None), never vacuously PASS, when it cannot actually
search the contract.** Implemented entirely in non-guarded code:

- `Z3Backend.encodable(pred)` — True iff `pred` compiles in the DSL.
- `coverage_probe` — before trusting a `None` search result, require that
  `claim_domain`, `claim_property`, and `established_domain` are all encodable. If any
  is not, return `None` (DEFER). Requiring `claim_property` too makes a PASS mean
  *both* the probe (domain coverage) and the gate's adversarial spine (property
  gaming, run earlier with the same encodable property) genuinely ran.

A measurable claim that DEFERs is refused, not laundered to a judge (existing gate
behaviour) — so it never reaches proof or promulgation.

## Consequences

- **The faithfulness gate is now honest.** It certifies faithfulness only for
  contracts it can mechanically search; everything else DEFERs. No more vacuous
  passes; no risk of promulgating a kernel-proven but unverified-faithful law.
- **It exposes the real frontier blocker.** With the DSL this small, almost all
  rich conjectures DEFER at faithfulness — so honest discovery is gated less by the
  prover's reach (ADR 0019) than by the **faithfulness DSL's reach**. The next deep
  faithfulness ADR is to widen what the gate can mechanically check (multi-variable,
  exponentiation, named functions) — or add a sound non-DSL faithfulness mechanism.
- Trust unaffected structurally: proposal-side gate-quality fix; `gates/` untouched;
  `tests/test_invariants.py` byte-identical. This *tightens* the trust posture (fewer
  unverified passes), it does not relax it.

## Open questions

- Widening the faithfulness DSL is the highest-leverage discovery unblock now —
  bigger than prover budget, since candidates DEFER before proof.
- A graded "partially encodable" signal (certify the encodable part, flag the rest)
  could recover some yield without vacuous certification.
