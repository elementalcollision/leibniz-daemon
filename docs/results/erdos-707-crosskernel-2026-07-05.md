# Cross-kernel amplification — Erdős 707 finite core in a second kernel (Lean ↔ Coq)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (12/12 Coq Examples; Rocq-sound, rocqchk axioms `<none>`)

## What this is

The **cross-kernel attestation sweep** applied to a marquee result: the finite core of **Erdős Problem 707**
(the Sidon-Extension Conjecture, a $1000 problem posed from 1976 and freshly resolved) that Leibniz's
**Lean 4.31** kernel decided in [#295](https://github.com/elementalcollision/leibniz-daemon/pull/295) is here
**independently re-decided by the Rocq 9.0 (Coq) kernel** — a second, independent trusted core.

## Target

Erdős 707 asks whether every finite **Sidon set** extends to a finite **perfect difference set (PDS)**.
Disproved by **Alexeev & Mixon** ([arXiv:2510.19804](https://arxiv.org/abs/2510.19804)) via `{1,2,4,8,13}`
(and Hall's `{1,3,9,10,13}`); **Niu** ([arXiv:2604.25214](https://arxiv.org/abs/2604.25214)) gave the size-4
candidates `{0,1,3,11}`, `{0,1,4,11}`. A PDS of order `n` has `n(n−1)=v−1`, so `B ⊂ ℤ_v` is a PDS iff its
pairwise diffs mod `v` are distinct; non-extension at order `n` ⟺ no size-`n` superset is Sidon mod `v` — a
bounded decidable fact.

## What Leibniz re-verified — in a second kernel

For each of the four counterexample sets, the Rocq 9.0 kernel re-decides (by `vm_compute`) the SAME facts the
Lean kernel decided: (i) the set is **Sidon** (`nodupZ (diffsZ S) = true`), and it is **non-extending** at
order `|S|` (`isPDS S v = false`) and at order `|S|+1` (`extends1 S v = false`, i.e. no single adjoined residue
yields a PDS). 12 `Example`s total, confirmed **axiom-free** by Rocq's own library checker `rocqchk` (`*
Axioms: <none>`, no unsafe constructs). Python `set`-arithmetic is a third, independent cross-check. Two
independent kernels agreeing on the finite exhaustion of a freshly-resolved $1000 problem is strictly stronger
evidence than either alone.

## Honest scope

Same **finite core** (Sidon + non-extension at small orders) as the Lean census, now in a second kernel — an
independent cross-check, not a re-proof of the infinite "no PDS at all" claim (proven non-finitely by
Alexeev–Mixon's polarity argument; the size-4 case is still conjectural). The Coq backend is **report-only**
and **dormant for promulgation** (ADR 0048): it never writes `kernel_verified` and its producer is unadmitted,
so no trust surface is touched; `tests/test_invariants.py` byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/erdos_707_crosscheck.v` — 12 Coq `Example`s (`nodupZ`/`isPDS`/`extends1`)
- Producer / verifier: `scripts/verify_erdos_707_crosskernel.py` · Tests: `tests/test_erdos_707_crosskernel.py`
- Result record: `docs/results/erdos_707_crosskernel_verification.json`
