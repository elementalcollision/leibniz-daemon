# Independent confirmation of the first counterexample to EFX existence

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact exhaustive census; faithfulness cross-checked)

## What this is

An independent, exact-census confirmation of a landmark 2026 result in a domain new to the ledger (**fair
division / discrete allocation**). Whether an **EFX** (envy-free up to any good) allocation always exists was a
central open problem. **Akrami, Mayorov, Mehlhorn, Srinivas & Weidenbach**
([arXiv:2604.18216](https://arxiv.org/abs/2604.18216), 2026) resolve it **negatively** with an explicit
instance found by SAT-solving: **3 agents, 8 goods, monotone valuations, and no EFX allocation**.

## The instance

Each agent `i`'s valuation `vᵢ` is an **ordinal**: `vᵢ(A)` is the rank (`0..255`) of the subset `A` in agent
`i`'s linear order over the `2⁸ = 256` subsets of the 8 goods. The three rank tables are arbitrary (SAT-found,
"far from additive or cardinality-based"); Leibniz vendors them verbatim from the paper's companion artifact
into [`docs/crt/efx/`](../crt/efx/) (see [`SOURCE.md`](../crt/efx/SOURCE.md) for provenance).

## What Leibniz verified — exact exhaustive census

1. **Valid monotone valuations.** Each `vᵢ` is a **bijection** onto `{0,…,255}` (`∅→0`, full set `→255`) and is
   **monotone** (`A ⊂ B ⟹ vᵢ(A) < vᵢ(B)`) — a legitimate monotone valuation, exactly the class the EFX
   question is posed for.
2. **No EFX allocation exists.** For **every** one of the `3⁸ = 6561` allocations of the 8 goods to the 3
   agents, some agent EFX-envies another — `vᵢ(Xᵢ) < vᵢ(X_{owner(g)} ∖ g)` for some good `g` and non-owner `i`
   (removing any single good from the envied bundle does not remove the envy). **Zero** allocations are EFX.
3. **Faithfulness cross-check.** Of the `5796` allocations with all-nonempty bundles, **exactly 272** violate
   **exactly one** of the `2m = 16` EFX-conditions — reproducing the paper's own reported statistic
   bit-for-bit. This certifies the vendored valuation tables were ingested correctly (a single wrong rank would
   almost surely perturb this count).

Every check is exact-integer — no floating point.

## Honest scope

This is an **audit of a SAT-found instance**, not an independent re-derivation: the valuations are arbitrary
monotone rankings that cannot be reconstructed, so Leibniz verifies the *given* object (that it is a valid
monotone instance with no EFX allocation) rather than recomputing it — the same posture as verifying a given
code or design. The decider is an **exact-integer exhaustive census** (a mechanical decision procedure, like the
finite-field / exact-rational deciders in earlier cycles), cross-validated against the paper's own statistics.
The paper separately **formalized the correctness of its SAT-encoding in Lean**; this instance-level census is
complementary. A full in-kernel `decide` census (6561 allocations × 256-entry table lookups) exceeds the
kernel's reduction budget (ADR 0047), so the exact census — not the Lean kernel — is the decider here. The
verification is **report-only**: nothing sets `kernel_verified` or touches `trust.py`;
`tests/test_invariants.py` is byte-identical.

## Artifacts

- Counterexample data (downloadable): [`docs/crt/efx/Val{0,1,2}ByCard.txt`](../crt/efx/) — the three valuation
  rank tables (+ [`SOURCE.md`](../crt/efx/SOURCE.md)).
- Producer / verifier: [`scripts/verify_efx_counterexample.py`](../../scripts/verify_efx_counterexample.py) ·
  Tests: [`tests/test_efx_counterexample.py`](../../tests/test_efx_counterexample.py)
- Result record: `docs/results/efx_counterexample_verification.json`

## References

- Akrami, H., Mayorov, A., Mehlhorn, K., Srinivas, S., & Weidenbach, C. (2026). *A counterexample to EFX:
  n ≥ 3 agents, m ≥ n + 5 items, submodular valuations via SAT-solving* (arXiv:2604.18216). arXiv.
