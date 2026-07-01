<!--
CLI runbook for the Delsarte-LP + SDP-three-point (Terwilliger) validation arc. Every command is copy-paste
from the repo root. Audit-tier throughout: the Lean kernel (docker leg) is the ONLY soundness-relevant check;
free-CPU / solver legs validate mechanism. No command here touches the trust boundary.
-->

# Runbook — Terwilliger / SDP three-point, from the CLI

Run everything from the repo root:

```bash
cd /Users/dave/Claude_Primary/leibniz
```

Two things you already have on this machine (verified): cvxpy 1.9.2, numpy, ortools. The only extra a full run
needs is the **Lean docker image** (for the kernel legs) — §1.3.

---

## 0. TL;DR — the immediate "run this" (Phase 0, free-CPU, ~1 s)

```bash
python3 scripts/terwilliger_beta.py          # β generator + real-code PSD oracle → GREEN
python3 -m pytest tests/test_terwilliger_beta.py -q   # 6 tests, free-CPU
```

Expected tail:

```
terwilliger β generator: GREEN
  n=3: singleton=ok, repetition=ok, even-weight=ok, full-space=ok
  ...  n=6 ...
  control (corrupt β breaks PSD): True
  published oracle: 372 nonzero β entries -> docs/results/terwilliger_beta_oracle.tsv
```

Exit code 0 = GREEN. Writes `docs/results/terwilliger_beta.json` + `docs/results/terwilliger_beta_oracle.tsv`.

---

## 1. Prerequisites

### 1.1 Environment
```bash
python3 -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -e ".[verify,propose,dev]"                 # core is stdlib-only; extras add z3/lean-dojo/anthropic + pytest/ruff
```

### 1.2 Operator-local solver deps (already installed here)
```bash
pip install cvxpy numpy ortools     # cvxpy(+SCS/CLARABEL) & numpy for the SDP legs; ortools for the Delsarte LP
python3 -c "import cvxpy, numpy, ortools; print('solver deps OK')"
```
These are **not** in `pyproject` extras on purpose — they are operator-local so CI skips the solver legs cleanly.

### 1.3 Lean kernel image (needed only for the docker/kernel legs, §4)
```bash
docker image inspect leibniz-lean:v4.31.0 >/dev/null 2>&1 && echo "image present" || \
  docker build -f docker/lean.Dockerfile -t leibniz-lean:v4.31.0 .     # OrbStack/Docker; builds Lean 4.31 + Mathlib cache
python3 -c "from leibniz.backends.lean_cli import available; print('kernel available:', available())"
```
If `available()` is `False`, every script below still runs — it just **skips its kernel leg** and reports the
free-CPU/solver result. The kernel leg is the only soundness-relevant step, so run it before trusting a result.

---

## 2. Dependency legend (what each script needs)

| Script | free-CPU core | cvxpy+numpy | ortools | docker (Lean) leg |
|---|---|---|---|---|
| `terwilliger_beta.py` | ✅ all of it | — | — | — |
| `psd_certificate_microprobe.py` | ✅ mechanism | — | — | kernel verify/reject (auto-skips) |
| `psd_scaling_probe.py` | ✅ bit-length | — | — | kernel check (auto-skips) |
| `bareiss_ldlt.py` | ✅ factorization | — | — | kernel verify/reject (auto-skips) |
| `delsarte_lp_probe.py` | — | — | ✅ LP (GLOP) | cert → kernel (auto-skips) |
| `delsarte_reach_probe.py` | — | — | ✅ (via LP) | cert → kernel (auto-skips) |
| `delsarte_bank.py` | — | — | ✅ (via LP) | corpus kernel-verify (auto-skips) |
| `irrationality_margin_test.py` | — | ✅ ϑ SDP | — | rational cert → kernel (auto-skips) |
| `sdp_code_bound.py` | — | ✅ ϑ SDP | ✅ cross-check | cert verify + bogus-reject (auto-skips) |

"auto-skips" = if the Lean image is absent the script prints `kernel=unavailable`/skips that leg and still exits
on its free-CPU/solver verdict. None take CLI arguments — each is a bare `python3 scripts/<name>.py`.

---

## 3. Tier A — free-CPU (run anywhere, no solver/docker)

```bash
python3 scripts/terwilliger_beta.py               # Phase 0: β generator, GREEN, writes json+tsv
python3 scripts/psd_certificate_microprobe.py     # #212 exact-PSD (integer LDLᵀ) mechanism
python3 scripts/psd_scaling_probe.py              # #213 compute-trap: naive cert bit-length growth
python3 scripts/bareiss_ldlt.py                   # #215 fraction-free (Bareiss) determinant-bounded cert
```
Free-CPU pytest for this tier:
```bash
python3 -m pytest tests/test_terwilliger_beta.py tests/test_psd_certificate_microprobe.py \
                  tests/test_psd_scaling_probe.py tests/test_bareiss_ldlt.py -q
```

## 4. Tier B — solver-gated (cvxpy+numpy / ortools)

```bash
# Delsarte LP dual → exact integer certificate (ortools GLOP)
python3 scripts/delsarte_lp_probe.py              # reproduces known A(n,d); writes delsarte_lp_probe.json
python3 scripts/delsarte_reach_probe.py           # discovery test on open cells (result: NO-TIGHTENING)
python3 scripts/delsarte_bank.py                  # banks the kernel-verified LP-cert corpus + reading room

# SDP legs (cvxpy/SCS + numpy)
python3 scripts/irrationality_margin_test.py      # #214 revised gate: rational PSD cert floors ϑ→α, GREEN
python3 scripts/sdp_code_bound.py                 # #215 code-SDP → dual → rational cert → (kernel); GREEN
```
Solver-gated pytest:
```bash
python3 -m pytest tests/test_delsarte_lp_probe.py tests/test_delsarte_reach_probe.py \
                  tests/test_delsarte_bank.py tests/test_irrationality_margin.py \
                  tests/test_sdp_code_bound.py -q -rs      # -rs shows skip reasons if a dep is missing
```

## 5. Tier C — kernel-gated (docker + Lean image)

With the image present (§1.3), the same scripts above now **exercise their kernel legs** (valid cert accepted,
bogus cert rejected). To run the docker-gated tests as a dedicated lane that FAILS on a silent skip:

```bash
# the SDP-arc kernel tests (end-to-end: cert → real Lean 4.31 kernel, incl. bogus-cert rejection)
python3 -m pytest tests/test_sdp_code_bound.py tests/test_psd_certificate_microprobe.py \
                  tests/test_bareiss_ldlt.py -q -rs -k "kernel or docker or main_pipeline"

# the existing kernel-CI lane (GATE-4 false-theorem backstop etc.); errors if the image is absent
bash scripts/run_kernel_tests.sh
```

## 6. Full-suite one-shot

```bash
# whole SDP/Terwilliger arc, free-CPU + solver + (kernel if image present); -rs surfaces any skip
python3 -m pytest tests/test_terwilliger_beta.py tests/test_delsarte_lp_probe.py \
  tests/test_delsarte_reach_probe.py tests/test_delsarte_bank.py \
  tests/test_psd_certificate_microprobe.py tests/test_psd_scaling_probe.py \
  tests/test_bareiss_ldlt.py tests/test_irrationality_margin.py tests/test_sdp_code_bound.py -q -rs

# reproduce every result JSON in one go
for s in terwilliger_beta psd_certificate_microprobe psd_scaling_probe bareiss_ldlt \
         delsarte_lp_probe delsarte_reach_probe delsarte_bank irrationality_margin_test sdp_code_bound; do
  echo "== $s =="; python3 "scripts/$s.py" || echo "  (exit $?)"
done

ruff check scripts/ tests/          # lint
python3 -m pytest tests/test_invariants.py -q     # trust boundary (must stay green)
```

## 7. Expected outputs & GREEN criteria

| Script | Output JSON (under `docs/results/`) | GREEN means |
|---|---|---|
| `terwilliger_beta.py` | `terwilliger_beta.json`, `terwilliger_beta_oracle.tsv` | all real-code blocks PSD (16/16) + corrupt-β breaks PSD |
| `psd_certificate_microprobe.py` | `psd_certificate_microprobe.json` | integer LDLᵀ cert verifies; bogus rejected (kernel leg if docker) |
| `psd_scaling_probe.py` | `psd_scaling_probe.json` | measured naive bit-length growth (the compute trap) |
| `bareiss_ldlt.py` | (bareiss json) | Bareiss cert bit-length ≪ naive; kernel accepts valid / rejects bogus |
| `delsarte_lp_probe.py` | `delsarte_lp_probe.json` | reproduces the 9 known A(n,d) via integer certs |
| `delsarte_reach_probe.py` | `delsarte_reach_probe.json` | NO-TIGHTENING (LP reproduces best-known, never tightens) |
| `delsarte_bank.py` | corpus json + reading room | kernel-verified LP-cert corpus banked |
| `irrationality_margin_test.py` | `irrationality_margin_test.json` | ⌊t*⌋=α for all irrational-ϑ graphs, tax < 0.01 |
| `sdp_code_bound.py` | `sdp_code_bound.json` | reproduces A(4,2)/A(4,4)/A(5,2); kernel-verified; bogus rejected; sound |

---

## 8. Where this sits

- **Phase 0 (§0) is the current front line** — it validated eq. (7) and fixed the first cell to **A(19,6)
  1289→1280**. See `docs/results/terwilliger-phase0-2026-07-01.md`.
- Tiers A/B/C reproduce the already-GREEN gates behind Phase 0 (#212 mechanism, #213 compute-trap, #214
  irrationality margin, #215 foundation). See `docs/results/sdp-foundation-2026-07-01.md` and the synthesis
  `docs/results/terwilliger-review-synthesis-2026-07-01.md`.
- **Next build is Phase 1** (mechanical dual) — not yet a script; see the synthesis doc §4.
- Trust tier is **audit** (`DUAL_CERTIFICATE_CHECKED`): the kernel legs guarantee certificate arithmetic; a
  bridge theorem (later rung) is required before any output is Q.E.D.
