# Kernel-attested minimal double blocking sets of size 3q−1 in PG(2,q) (Csajbók–Héger 2019)

**Date:** 2026-07-06 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact GF(q) incidence arithmetic; Lean 4.31 `decide`)

## What this is

An independent, exact-arithmetic confirmation of a published result in a domain new to the ledger (**finite
geometry / blocking sets**). A **t-fold blocking set** of the projective plane `PG(2,q)` is a set of points
meeting *every* line in at least `t` points; the `t=2` case is a **double blocking set**, and it is **minimal**
if no proper subset is one. The trivial double blocking set is the union of the three sides of a triangle, of
size `3q`. **Ball–Blokhuis (1996)** proved that for `q ≤ 8` every double blocking set has at least `3q` points,
and R. Hill's 1984 problem paper expected, "cautiously," that no set of size `3q−1` with two `(q−1)`-secants
exists for any `q`.

**Csajbók & Héger** ([arXiv:1805.01267](https://arxiv.org/abs/1805.01267); *European J. Combin.* **78** (2019),
655–678) **refute that expectation**: by a MIP search they exhibit explicit **minimal double blocking sets of
size `3q−1`** admitting two `(q−1)`-secants for `q ∈ {13, 16, 19, 25, 27, 31, 37, 43}`. For prime `q > 13`
these are the **first** double blocking sets of size below `3q`. Together with their Section-3 non-existence
theorem (removing six points of a triangle and adding five cannot give one), the paper resolves **two 1984
conjectures of Raymond Hill**. This cycle amplifies the **constructive** half — the *existence* of the
size-`(3q−1)` sets — which is the part that reduces to an exact finite object.

## What Leibniz verified — two independent checks, over five prime cases

Each construction fixes the two `(q−1)`-secants as the coordinate axes `L_X` (`y=0`) and `L_Y` (`x=0`), with
four "holes" `(1:0:1),(1:0:0),(0:1:1),(0:1:0)`; `B` is both axes minus the holes, plus the `q+2` further points
printed in the paper. Working over the finite field `ℤ/qℤ` for the five **prime** cases `q ∈ {13,19,31,37,43}`,
Leibniz reconstructs `B` and checks, by exact incidence arithmetic (`a·x+b·y+c·z ≡ 0 mod q`):

1. **Double blocking.** Every one of the `q²+q+1` lines meets `B` in **≥ 2 points** — i.e. there is no 0- and
   no 1-secant. All five pass (`|B| = 3q−1`: 38, 56, 92, 110, 128).
2. **Minimality.** Every point of `B` lies on a **2-secant** (bisecant); deleting it would leave that line a
   1-secant, so no proper subset is double blocking. All five pass.

**Faithfulness anchor.** For every case Leibniz reproduces the paper's **published secant distribution** `nₜ`
(`t ≥ 3`) *exactly* — e.g. `q=13`: `n₁₂,n₈,n₇,n₆,n₅,n₄,n₃ = 2,1,1,4,10,19,51`; `q=43`:
`n₄₂,n₈,n₇,n₆,n₅,n₄,n₃ = 2,4,8,26,122,321,590`. A single mis-transcribed point shifts the distribution, so the
exact match certifies the reconstructed `B` (axes included) is the authors' set. The two `n_{q−1}=2` long
secants are precisely the two `(q−1)`-secants Hill's conjecture said could not coexist.

## The Lean kernel re-decides it

The **Lean 4.31 kernel** independently re-decides, by plain `decide` (report-only), the two flagships — `q = 13`
(the unique example admitting two `(q−1)`-secants up to projective equivalence) and `q = 19` (the first prime
`q > 13`, the headline novelty) — in [`docs/crt/double_blocking.lean`](../crt/double_blocking.lean):

- `db13_blocking`, `db19_blocking` — every line meets `B` in ≥ 2 points;
- `db13_minimal`, `db19_minimal` — every point of `B` lies on a 2-secant;
- `db13_control`, `db19_control` — the **negative control**: `B` with one point removed is **not** double
  blocking (`= false`), proving the check discriminates.

All six theorems are `#print axioms`-clean — each **depends on no axioms at all** (pure `Nat`/`Bool` `decide`; no
`native_decide`, no `sorry`).

## Honest scope

This confirms **existence and minimality** of the size-`(3q−1)` sets — the constructive refutation of Hill's
conjecture — by exact re-verification of explicitly transcribed point sets, cross-checked against the paper's
own secant distribution. What is **not** attempted here: the paper's Section-3 non-existence theorem (a proof,
not a finite object); projective-equivalence / uniqueness claims; and the non-prime cases `q ∈ {16,25,27}`
(which need `GF(q)` extension arithmetic rather than `ℤ/qℤ`) — these are verified in exact arithmetic only for
the five prime `q`, with the kernel leg on `q ∈ {13,19}`. The backend is **report-only**: nothing sets
`kernel_verified` or touches `trust.py`; `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/double_blocking.lean`](../crt/double_blocking.lean) — Lean 4.31, six
  `decide` theorems (two flagships × blocking + minimal + control).
- Producer / verifier: [`scripts/verify_double_blocking.py`](../../scripts/verify_double_blocking.py) ·
  Tests: [`tests/test_double_blocking.py`](../../tests/test_double_blocking.py)
- Result record: `docs/results/double_blocking_verification.json`

## References

- Csajbók, B., & Héger, T. (2019). *Double blocking sets of size 3q−1 in PG(2,q)*. European Journal of
  Combinatorics, 78, 655–678. [arXiv:1805.01267](https://arxiv.org/abs/1805.01267).
- Ball, S., & Blokhuis, A. (1996). *On the size of a double blocking set in PG(2,q)*. Finite Fields and Their
  Applications, 2(2), 125–137.
- Hill, R. (1984). *Some problems concerning (k,n)-arcs in finite projective planes*. Rendiconti del Seminario
  Matematico di Brescia, 7, 367–383.
