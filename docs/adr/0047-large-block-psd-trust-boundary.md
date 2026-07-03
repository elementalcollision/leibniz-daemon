# ADR 0047 — Large-block PSD certification: hold the kernel-reducing boundary; defer any trust-tier expansion

- **Status:** ACCEPTED (2026-07-02) — the decision is to **HOLD the current trust model**: the
  kernel-reducing `decide`-based PSD primitive is the sole in-kernel PSD certification path, and its measured
  ~N≈60 ceiling is an **accepted, deliberate trust boundary**, not a defect to engineer around. Any expansion
  of that boundary (to attest large-block PSD, N ≫ 60) is a **new trust tier**, DEFERRED and gated behind its
  own ADR + operator sign-off + witness round (the ADR 0044/0045 precedent). This ADR adopts the hold and
  pre-registers the conditions for revisiting; it does **not** adopt any expansion.
- **Date:** 2026-07-02
- **Deciders:** Operator (any future tier expansion requires per-mechanism sign-off; the *hold* is the
  charter-safe default and needs none).
- **Touches the proof/trust edge:** NO. No code, no `leibniz/trust.py`/`verifiers.py` change,
  `tests/test_invariants.py` byte-identical. `native_decide` remains forbidden.
- **Siblings:** ADR 0001 (charter — MECHANICAL = kernel or decision procedure, zero LLM trust; "the Lean
  kernel is the sole arbiter"), ADR 0046 (Observatory tier for results not kernel-attested), ADR 0044/0045
  (trust-tier admissions — operator-gated, witness-round precedent).

---

## 1. Context — the frontier is mapped; the wall is a trust-model property

The Terwilliger program reached its kernel tier: three-point bounds are kernel-attested; the base family is
mined out; and the natural stronger formulation (GMS 2012 quadruple) was **blocked by GATE 0**
(`docs/results/terwilliger-gms-gate0-2026-07-02.md`): its reduced PSD blocks are O(n²), order 130–414, past
the kernel's PSD-certification ceiling. Two measurement rounds then characterized that ceiling exactly:

- **The best sound primitive** (`docs/results/terwilliger-psd-primitive-2026-07-02.md`, PR #247): the low-rank
  Gram form `lowRankOK` — a strict, sound generalization of `ldltOK` (kernel recomputes the integer identity,
  never trusts the rank; `r=N` recovers `ldltOK`) — plus column-scale fusion. Pushes the ceiling ~40 → ~60+
  and cuts certificate bit-length. This is the frontier of *kernel-reducing, no-new-trust* PSD certification.
- **The wall is fundamental** (`docs/results/terwilliger-proofterm-probe-2026-07-02.md`, PR #248): `decide`
  cost is ~O(term²) (a flat sum of K products: K=200→1.4 s, K=1000→30 s, K=4000→timeout); a "proof-term"
  (flat-arithmetic) encoding is *worse*, not better; Nat vs Int is marginal. Exact in-kernel recomputation of
  an N-scale matmul has irreducible term size, and `decide` on it is superlinear. **~N≈60 is a property of the
  trust model** (the kernel must reduce the certificate, and `native_decide` is forbidden), not an engineering
  gap. The research survey (verified Cholesky/LDLᵀ, Gershgorin/congruence, Schur recursion, SOS/Positiv-
  stellensatz, ValidSDP/CoqInterval) found no cheaper certificate that stays inside the model.

So raising the ceiling is not a solver problem; it is a **trust-boundary decision** with exactly three options.

## 2. The three options

1. **HOLD (status quo).** Keep the kernel-reducing `decide`-based primitive as the sole in-kernel PSD path.
   Large-block SDP results (GMS quadruple, any N ≫ 60 block) are **not kernel-attested** — they stay at
   Observatory/audit tier (ADR 0046) or are not produced. TCB unchanged. Cost: the daemon cannot kernel-attest
   large-block SDP bounds; the discovery frontier there (already near-zero per D3) stays closed at MECHANICAL
   tier.
2. **`native_decide` for PSD blocks (a new trust tier).** Compiler-*evaluated* rather than kernel-*reduced* —
   orders of magnitude faster, would clear N ≫ 60. But it trusts the **Lean compiler + the `Nat`/`Array`
   runtime**, a large TCB increase, and directly contradicts ADR 0001's "the Lean kernel is the sole arbiter"
   / MECHANICAL-with-zero-non-kernel-trust. Admissible only as an explicit new tier with mitigations
   (e.g. differential re-check, pinned toolchain hash, scoped to PSD-block `Bool`s).
3. **An external verified PSD checker (a new trust tier).** A checker (verified Cholesky / a reflection-based
   or ValidSDP-style routine) whose **own soundness is proved once** in Lean; per-certificate trust then rests
   on that one proof, not on re-reducing each cert. Keeps trust *mechanical* (a proved artifact, not a trusted
   binary), unlike `native_decide`. Cost: a substantial one-time formalization (weeks–months of expert Lean).

## 3. Decision

- **Adopt Option 1 (HOLD) now.** `ldltOK`/`lowRankOK` via `decide` remain the sole in-kernel PSD certification
  path; ~N≈60 is an accepted, documented trust boundary. `native_decide` stays forbidden. Large-block PSD
  results are Observatory/audit tier (ADR 0046) or not produced — never silently kernel-attested.
- **Defer Options 2 and 3.** Neither is adopted. If the boundary is ever revisited, the **recommended**
  mechanism is **Option 3 (external verified checker) over Option 2 (`native_decide`)**, because it keeps
  per-certificate trust mechanical (a once-proved artifact) rather than importing the compiler/runtime into
  the TCB — consistent with the charter. Either expansion is **gated**: its own ADR (next number), a
  PreToolUse-guarded change if it touches `verifiers.py`/tiers, operator sign-off, and a witness round
  (ADR 0044/0045 protocol). No such work is authorized by this ADR.
- **Trigger to revisit.** Only when a *live, non-dormant* need appears — a specific large-block SDP whose bound
  is (a) not already in the tables and (b) reachable by our solve leg — does the tier question become worth the
  spend. GATE 0 + D3 show no such need exists today (GMS records are published; the reachable cells are
  mined out). Absent that trigger, HOLD is not just safe but correct on the merits.

## 4. Consequences

- **Trust boundary intact.** No `trust.py`/`verifiers.py` edit; `tests/test_invariants.py` byte-identical.
  The daemon's kernel-PSD ceiling (~N≈60, low-rank) is now a documented, tested property
  (`scripts/terwilliger_{psd_lowrank,decide_probe}.py`).
- **GMS quadruple remains not-kernel-attestable**; the Terwilliger program rests at its kernel tier, complete.
- **Future large-block SDP work must first bring a tier ADR** — it cannot proceed as "just a solver
  improvement," because the measurements prove the ceiling is a trust property, not an engineering one.
- **No dormant trust surface added** (contrast ADR 0044): this ADR *declines* to add a tier, so there is
  nothing to leave dormant.

## 5. Non-goals

Not adopting `native_decide`; not building an external verified checker; not producing large-block
(GMS-quadruple) certificates at kernel tier. This ADR records the boundary and the gated path to revisit it —
nothing more.
