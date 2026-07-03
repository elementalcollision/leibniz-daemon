# Full in-Lean INFINITE-ORDER identification — GREEN, kernel-verified (2026-07-03)

**Result: GREEN, kernel sound.** The flashiest F2b-scale lift: the even process's **infinite Markov order** is
now proven **end-to-end in the kernel from its OOM operator definition** — no audit. This closes T8-b's
audit link (T8-b proved the *abstract* recurrence sequence nonzero, with "evenGap = the process's gap" as a
Python audit; now the gap *is* derived from the operators). Verified through the ADR-0011 Mathlib REPL.
`scripts/beyond_markov_infinite_order_lean.py`, `docs/results/beyond_markov_infinite_order_lean.json`,
`tests/test_beyond_markov_infinite_order_lean.py`. No trust surface touched.

## Kernel-Q.E.D. (0 errors, 0 sorries; both controls fail)

The even process defined in Lean (`eInit=![2/3,1/3]`, `eOp=![!![1/2,0;0,0], !![0,1/2;1,0]]`, `eFin=![1,1]`,
`eP w = Pval …`):

- **`eOp1_sq`** — the parity engine: `eOp 1 · eOp 1 = ½ · I` (a 2×2 computation).
- **`eP_append_11`** — appending "11" halves the word probability: `eP (w ++ [1,1]) = ½ · eP w`
  (from `eOp1_sq` + operator-product / scalar-multiplication associativity through `mulVec`/`dotProduct`).
- **`Dgap_rec`** — the cross-multiplied order-k conditional gap
  `D_k = P(0·1^k·1)·P(1·1^k) − P(1·1^k·1)·P(0·1^k)` satisfies **`D_{k+2} = ¼ D_k`**: both pasts `0·1^k`, `1·1^k`
  gain "11" (via `List.replicate_add`), each `P` halves, so `D` scales by `¼`.
- **`Dgap0` / `Dgap1`** — base cases evaluated *in-kernel*: `D_0 = −1/18`, `D_1 = 1/36` (both ≠ 0).
- **`even_infinite_order`** — `∀ k, D_k ≠ 0`, via `two_step_recurrence_nonzero` (the T8-b bridge, `q=¼`). The
  even process is **not order-k Markov for any k**: infinite Markov order, from the operators.

Controls (fail): a **wrong base case** (`D_0 = −1/17`) and a **wrong recurrence ratio** (`q = 1/4 → 1/3`, so
`Dgap_rec` no longer typechecks against the bridge). Python cross-check confirms `D_0=−1/18`, `D_1=1/36`,
`D_{k+2}=¼D_k`, all nonzero on `k=0..19`.

## What this closes

With the rank identification (`beyond-markov-process-lean-2026-07-03.md`), **both** of the even process's
core beyond-Markov properties are now kernel-derived from its 2-dim OOM, no audit:
- **Hankel rank = 2** — `hankel_block_rank_le` + a concrete in-kernel determinant.
- **infinite Markov order** — `even_infinite_order` (this doc).

So the canonical infinite-order-but-finite-dimension process is fully machine-certified from its operators —
the exact separation the whole beyond-Markov reframe is about, end-to-end. The **T8-c positive-realization**
identification (the necklace chain's fooling-set embedding in Lean) is the last remaining audit-linked
follow-on. The reusable `two_step_recurrence_nonzero` + `Tprod`/`Pval` + `eP_append_11` scaffold is what it
would build on. Amplification, not discovery; behind the unbroken trust boundary.
