<!--
External research brief (operator request 2026-07-05): a new kernel-certification approach for the large-block
PSD wall. For the external witness panel (the F2b-style multi-model round). Read ADR 0047 first; this brief
does NOT relitigate the HOLD decision — it scopes the Option-3 research the ADR pre-registered.
-->

# External research brief — breaking (or bounding) the large-block PSD kernel-certification wall

**Audience:** external reviewers (multi-model witness panel) + expert formalizers.
**Ask:** feedback, opinions, ranking, and novel approaches on how Leibniz could kernel-certify **PSD-ness of
order-130–414 exact-rational matrices** while staying inside its trust model — or a reasoned verdict that it
should not try. **This is a research-scoping brief, not an authorization.** Any mechanism that lands is a new
trust tier gated behind its own ADR + operator sign-off + a witness round (ADR 0044/0045/0047 precedent).

## 1. What Leibniz is and the exact rule that binds

Leibniz is an agentic theorem daemon: **LLMs only propose; only mechanical checkers decide** — the **Lean
4.31 kernel**, Z3, and exact-rational procedures. The charter (ADR 0001) is absolute: *the Lean kernel is the
sole arbiter of a MECHANICAL proof edge; there is zero non-kernel trust*. Concretely, **`native_decide` is
forbidden** — it evaluates via the compiled Lean runtime (trusting the compiler + `Array`/`Nat` runtime), not
the kernel's own reduction. Everything the kernel attests, it must **reduce** itself.

## 2. The problem, precisely

Leibniz kernel-attests upper bounds `A(n,d) ≤ β` for binary codes via **Terwilliger three-point SDP**
certificates. The certificate is an **exact-rational dual** whose validity reduces to: *this symmetric
integer/rational matrix `M` (order `N`) is positive semidefinite.* The kernel must certify `M ⪰ 0` by
reduction.

**Current sound primitive** (`scripts/terwilliger_psd_lowrank.py`, ADR 0047): `lowRankOK` / `ldltOK` — a
`decide`-checked exact identity where the kernel **recomputes** an integer Gram / LDLᵀ factorization and
verifies `M = Lᵀ D L` (or a low-rank `M = FᵀF`), **never trusting the factor or the rank** (fail-closed;
`r=N` recovers full LDLᵀ). Column-scale fusion avoids materializing `diag(d)`.

**The wall (measured, `docs/results/terwilliger-proofterm-probe-2026-07-02.md`):**

- The ceiling is **~N ≈ 60** for a low-rank certificate; a *full* LDLᵀ is lower.
- `decide` cost is **~O(term²) in the number of arithmetic terms**, and **term count is the killer**, not
  per-operation cost: one flat sum of K products costs K=200 → 1.4 s, K=1000 → 30 s, **K=4000 → timeout**;
  1600 trivial conjuncts alone time out. **`Nat` (GMP-accelerated) vs `Int` reduction is only marginal.**
- A "proof-term" (fully unrolled flat arithmetic) is **worse**, not better — it times out at N=40 where the
  compact `List`-`def` form reaches N=60, because it spells out all N²·r scalar ops as source terms.
- Verifying an `N`-order matrix at all touches ≥ `O(N²)` entries; for `N = 200` that is ≥ 40,000 kernel
  operations — **far past the ~1000–4000-term practical `decide` limit.** So *no certificate-reduction scheme
  in the current `decide` model can reach large blocks* — this is why ADR 0047 calls the wall a **trust-model
  property, not an engineering gap.**

**The target that would need it:** the Grassl–Márquez-Corbella–Suárez (GMS 2012) *quadruple-distance* SDP —
the modern frontier where records come from — has **Hamming reduced blocks of order O(n²) = 130–414** for
`n = 19..28` (indexed by pairs `(i,i')`, `i+i' ∈ [d,n]`, after `S_n` symmetry reduction; corroborated by
GMS's own 13-CPU-day, high-precision solve for `A(23,6)`). Block-diagonalization is *already applied* and the
blocks are *still* an order of magnitude past the ceiling.

## 3. What is NOT being asked

- **Do not** relitigate the charter or the ADR 0047 HOLD. `native_decide` as-is is off the table; it may only
  appear as an explicit new *tier* with mitigations, and is **dispreferred** vs a proved artifact.
- **Do not** assume this is authorized. We want the *best design + honest cost + go/no-go*, not a build.

## 4. Candidate approaches (framing — react to these AND propose your own)

**A. Big-`Nat` arithmetization (exploit the kernel's GMP path, few huge ops instead of many small terms).**
The probe closed "many small terms" but did **not** test packing the whole `O(N²/N³)` computation into `O(N)`
or `O(1)` **big-`Nat` operations** that the kernel's GMP-accelerated `Nat.mul`/`Nat.add`/`Nat.decEq` evaluate
in a few reduction steps (one multiply of two 10¹⁰⁰⁰⁰-scale packed integers is *one* fast kernel step).
Matmul-as-integer-multiplication via positional/Kronecker packing (à la Schönhage), or a CRT/modular identity
`M = LᵀDL (mod p₁…pₖ)` with a proved lift, could in principle put the heavy arithmetic on the GMP path with
small *term count*. **Open questions:** does a sound packing exist that keeps the *term count* (not the bit
size) `O(N)`? Does the kernel actually reduce packed `Nat` literal ops in `O(1)` terms, or does the encoding
re-expand? Soundness of the packing/CRT lift?

**B. DD / SDD cone certificates (DSOS / SDSOS — Ahmadi–Majumdar).** Replace the PSD cone with the
**diagonally-dominant (DD)** or **scaled-diagonally-dominant (SDD)** cone: `O(N²)` *row-sum inequalities*
(no matmul), LP/SOCP-solvable, and a strict *subset* of PSD (so the SDP bound is **looser**). If the SDSOS
relaxation still meets the target integer floor `⌊β⌋`, it is a valid, far cheaper-to-verify certificate.
**Open questions:** is SDSOS tight enough for Delsarte/Terwilliger-type LP/SDP bounds to match known integer
targets (any literature)? Even `O(N²)` row-sums may exceed the term ceiling — does the row-sum structure
arithmetize under (A) where dense matmul does not?

**C. External verified PSD checker, proved once in Lean (ADR 0047 Option 3, pre-registered as preferred).**
A checker function whose **soundness is proved once** (`checker M = true → M ⪰ 0`); per-certificate trust then
rests on that one proof + the kernel **evaluating** the checker on `M`. Keeps trust mechanical (a proved
artifact, not a trusted binary). **The sub-problem is efficient in-kernel evaluation** — which loops back to
(A), because Lean's kernel has **no `vm_compute`/`native_compute`** (unlike Coq/ValidSDP/CoqInterval).
**Open questions:** best Lean-4-native design given no fast kernel compute; realistic formalization cost
(person-months of expert Lean); existing Mathlib PSD/Cholesky infrastructure to build on.

**D. Deeper symmetry / block-diagonalization to shrink blocks below ~60.** LPS-2017 split-Terwilliger or a
finer irrep decomposition to get a proven 2–7× block-size reduction, putting `N` under the *existing* ceiling
with no new primitive. **Open questions:** is a proven shrink to `N ≤ 60` achievable for the GMS blocks?

**E. `native_decide` as an explicit new tier with mitigations.** Differential re-check vs the kernel on
sub-blocks it *can* reduce, pinned toolchain hash, scoped to PSD-block `Bool`s, quarantine tier. Dispreferred
(imports the compiler into the TCB) but a real fallback.

**F. Certifying / reflective tactic producing a compact `O(N²)` proof term.** A Schur-complement /
incremental-Cholesky recurrence, or a `norm_num`-style extension, whose emitted proof term is `O(N²)` rather
than `O(N³)` and stays under the reduction ceiling. **Open questions:** can any exact PSD witness be verified
in a proof term whose *term count* is sub-threshold for N≈200?

## 5. Specific questions for the panel

1. **Rank** A–F (and anything you add) by likelihood of reaching `N = 130–414` **while staying MECHANICAL**
   (kernel reduction or a once-proved artifact; no compiler/runtime trust). Justify the top choice.
2. **Big-`Nat` arithmetization (A):** viable or a dead end? Is there a *sound* packing (positional, Kronecker,
   CRT-with-proved-lift) that makes PSD/LDLᵀ verification `O(N)`-or-fewer big-`Nat` kernel ops? Does Lean's
   kernel reduce packed literal arithmetic in `O(1)` terms, or re-expand it?
3. **DD/SDD (B):** any evidence the SDSOS relaxation is tight enough for coding-theory (Delsarte/Terwilliger)
   bounds to hit integer targets? Point to literature or give a reason it will/won't.
4. **Verified checker (C):** best Lean-native design absent `vm_compute`, and an honest formalization-cost
   estimate. Is the ValidSDP/CoqInterval approach portable to Lean, or does the lack of kernel `vm_compute`
   make it categorically harder?
5. **Missed approaches?** Interval arithmetic; LLL / lattice certificate compression; sparse
   Positivstellensatz; homomorphic/modular checking with a soundness proof; "certificate of a certificate";
   randomized-made-deterministic (derandomized Freivalds) verification — anything.
6. **Charter audit:** which candidates keep *per-certificate* trust mechanical, and which secretly import
   non-kernel trust? Flag any that only *look* like they stay in the model.
7. **Is it worth it?** ADR 0047's trigger to revisit is a large-block cell that is (a) **not** already in the
   published tables **and** (b) **reachable by our float solve leg**. GMS records are published; the reachable
   cells are mined out (D1/D3 DRY). Is there any target that justifies the spend, or is **HOLD** correct on
   the merits — with this research banked for if/when such a target appears?

## 6. What a good answer looks like

A ranked recommendation with reasoning; a viability verdict on (A) and (C) specifically (the two that could
stay mechanical *and* scale); an honest formalization-cost band for the recommended path; at least one
approach we did not list; and an explicit position on question 7 (worth it now, or bank-and-hold). Concision
over exhaustiveness; cite where you can.
