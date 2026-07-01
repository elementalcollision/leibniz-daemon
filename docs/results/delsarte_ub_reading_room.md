# Calculemus — Audit Annex: Delsarte upper-bound certificates

*Kernel-verified Delsarte LP **dual** certificates for binary codes A(n,d) — the UPPER-bound analog of the construction amplification annex. Each row: an untrusted LP solver proposed an exact integer dual certificate; the Lean 4.31 kernel independently re-checked it (recomputing Krawtchouk), proving A(n,d) <= bound. **Audit-tier — kernel-checked certificate validity, not promulgated laws**; the certOK => bound step is Delsarte's theorem (bridge lemma deferred). Novelty is record-relative vs an unvetted best-known snapshot.*

**18/18 kernel-verified.**

| cell | claim | kernel | novelty | method |
|---|---|---|---|---|
| A(5,3) | A(5,3) <= 4 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(6,3) | A(6,3) <= 8 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(7,3) | A(7,3) <= 16 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(6,4) | A(6,4) <= 4 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(8,4) | A(8,4) <= 16 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(8,5) | A(8,5) <= 4 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(9,5) | A(9,5) <= 6 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(10,5) | A(10,5) <= 12 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(11,5) | A(11,5) <= 24 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(13,3) | A(13,3) <= 512 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(13,5) | A(13,5) <= 64 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(13,7) | A(13,7) <= 8 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(14,3) | A(14,3) <= 1024 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(14,5) | A(14,5) <= 128 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(14,7) | A(14,7) <= 16 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(15,3) | A(15,3) <= 2048 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(15,5) | A(15,5) <= 256 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
| A(15,7) | A(15,7) <= 32 | KERNEL-VERIFIED | reproduces best-known | Delsarte LP dual certificate |
