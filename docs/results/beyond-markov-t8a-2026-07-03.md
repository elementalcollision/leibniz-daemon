# T8-a — minimal rational-HMM beyond-Markov certificate suite: GREEN, kernel-attested (2026-07-03)

**Result: GREEN, sound end-to-end.** The first buildable artifact of the beyond-Markov domain (roadmap T8, the
panel's "recommended first move") is built and **kernel-attested**: for two rational-HMM witnesses, the real
Lean 4.31 kernel accepts a valid certificate that the process is beyond every finite-order Markov model and
**rejects the corrupted control**. `scripts/beyond_markov_cert.py`, `docs/results/beyond_markov_cert.json`,
`tests/test_beyond_markov_cert.py` (CI-safe legs green; kernel leg docker-gated, verified operator-local).

## What the certificate proves (every leg the external panel demanded)

For a witness given as a **rational HMM** `(π, {T_a})` with `P(w)=π·T_w·1`:

1. **Process validity (the panel's #1 mandate).** `hmmValid`: `π≥0, Σπ=1`; every `T_a≥0`; `Σ_a T_a`
   row-stochastic — so `P(w)` is a genuine stochastic process for *all* words, not a signed formal series. We
   stay in the positive-HMM subclass (general-OOM validity is the undecidable Negative Probability Problem).
2. **Hankel rank ≥ 2.** A nonsingular 2×2 rational Hankel minor, `det≠0` (kernel recomputes the determinant
   from the integer-cleared matrix — it does not trust the producer).
3. **Markov order > K.** For each `k≤K`, a conditional-separation certificate on two pasts sharing a length-`k`
   suffix: the cross-multiplied determinant `D_k = P(h1 a)P(h2) − P(h2 a)P(h1) ≠ 0` **with denominator
   positivity** `P(h1),P(h2)>0` ⟹ `P(a|h1)≠P(a|h2)` ⟹ not order-`k` Markov.

The kernel program is **core Lean only** (`decide`; no Mathlib): `hmmValid ∧ minorNZ(H) ∧ (∀k minorNZ(D_k) ∧
0<num_h1 ∧ 0<num_h2)`. No trust surface touched (`verifiers.py`/`trust.py`/`tests/test_invariants.py`
unchanged) — a standalone checker exactly like `bareiss_ldlt.py`'s `detSignOK`.

## Measured (K=8)

| Witness | valid HMM | rank(H)≥2 | order>8 | kernel valid | bogus rejected |
|---|---|---|---|---|---|
| **BM-1** symmetric 2-mode HMM (q=3/4, e=1/8) | ✓ | ✓ `det=−192` | ✓ 9/9 | **True** | **True** |
| **BM-4** even process ε-machine | ✓ | ✓ `det=−2` | ✓ 9/9 | **True** | **True** |

Nice structure surfaced: the even process's order-separation determinants alternate `−2, 1, −2, 1, …` — the
**parity of the 1-run**, exactly its ε-machine memory. BM-1's memory is the mode posterior (pasts `0·0^k` vs
`1·0^k`); the even process's is 1-run parity (pasts `0·1^k` vs `1·1^k`).

## Honest scope (per the panel)

- **"order > K", NOT "infinite order".** K finite separation certificates prove order > K only. Infinite order
  is **T8-b** — a recurrence + induction bridge lemma (`Δ_{k+2}=qΔ_k, Δ_0,Δ_1≠0, q≠0 ⇒ ∀k Δ_k≠0`), which is
  Q.E.D.-reachable (the F2b pattern; the kernel checks proof terms, so induction is as sound as `decide`), not
  Observatory. The even-process alternation `−2,1,−2,1` is exactly a two-step geometric recurrence — the
  cleanest first target for T8-b.
- **Rank ≥ 2 is a lower bound.** Global `rank ≤ r` (hence `rank = r`) needs the linear-representation bridge
  lemma (the HMM *is* the representation) — also a T8-b/F2b-style slice.
- **Amplification, not discovery.** Both processes are textbook. The novelty is the end-to-end Lean-kernel trust
  chain (process → HMM validity → determinant → inequality, one replayable proof object). The discovery-shaped
  bet remains **T8-c** (the Minimal Positive Realization Problem via `exact_simplex` infeasibility).
