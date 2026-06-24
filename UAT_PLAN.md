# Leibniz UAT — fork & runbook (ADR 0033 Slice 4)

**Status**: drafted 2026-06-24. Implements the operational fork on top of ADR 0033
Slices 1–3 (instance-tag + write-barrier; publish guard; per-instance kernel/corpus
pinning), all already on `main`.

**Purpose**: stand up a sub-production (UAT) environment so trust-relevant changes —
faithfulness/novelty gates, prover ladder, DSL — can soak on real cycles before PROD
adopts them, **without ever risking the production Codex ledger**.

**Audience**: a separate Claude Code session operating from
`/Users/dave/Claude_Primary/leibniz-uat/`. This document is the strategic anchor; the
in-code guards (below) are the enforcement.

> House pattern: same as Leonardo (`leonardo-uat/`) and Newton — **the daemon code never
> branches; only the deploy configuration diverges.** UAT soaks new `main`; PROD tracks a
> soak-validated tag.

---

## 1. Why UAT now

A faithfulness-gate change (ADR 0031 L2) was shipped and reverted on `main` the same day.
On a single codeline that is a production scare: the same process that discovers laws is the
process under active, trust-relevant edit. Meanwhile the published Calculemus Codex is a
**valuable accumulating ledger**. Valuable ledger + fast trust-relevant iteration is exactly
the UAT trigger the siblings hit.

What UAT adds that local `pytest` + a dry run cannot: a **runtime** stage where new gate
behaviour fires on real conjecture→proof cycles, on a faster cadence, against controlled
state, before it can touch the production ledger.

## 2. The trust crux (Leibniz-specific)

Leibniz carries a constraint the siblings do not: **the trust boundary**. The one failure
mode this fork exists to make impossible is **a UAT-promulgated "law" being published as a
PROD law**. Five independent layers prevent it; any one suffices:

1. **Separate ledgers** — UAT writes its own DB (`deploy/profiles/uat.env` →
   `.leibniz-uat/memory.db`), never the prod `.leibniz/memory.db`.
2. **Write-barrier** (Slice 1) — if a UAT run is *mispointed* at the prod DB, the runtime
   **fails closed** (refuses to open a ledger owned by another instance).
3. **Indelible provenance** (Slice 1) — every row is stamped with its `instance`; a UAT
   promulgation is permanently marked UAT.
4. **Publish guard** (Slice 2) — `Calculemus.publish` reads the PROD ledger only, requires
   explicit instance confirmation, and the colophon shows the instance.
5. **Operator confirmation** (ADR 0008) — publication is a deliberate, gated act.

None of these depends on the kernel floor, which is **frozen in both instances**:
`LeanVerifier.discharge` is the sole `kernel_verified` writer, N+1 consensus and
promotion≠publication hold identically, and `tests/test_invariants.py` is byte-identical.
**UAT may relax ONLY the novelty and faithfulness gates** (e.g. DEFER for speed); it may
never touch the kernel floor. A UAT law is still kernel-true — just not PROD-grade-audited,
and the provenance + publish guard keep it out of the public Codex.

## 3. Hard isolation rules

Non-negotiable; enforced in code where marked:

1. **Ledger isolation** — separate `LEIBNIZ_RUNTIME_DB` per instance. *(write-barrier, Slice 1)*
2. **Discovery-state isolation** — separate `LEIBNIZ_FRONTIER_PATH` + `LEIBNIZ_NOTEBOOK_PATH`
   so UAT's frontier/notebook never perturb PROD's adaptive band. *(launch guard, Slice 4)*
3. **Kernel/corpus pinning** — PROD runs the audited code-pinned Lean image + corpus and
   **refuses** experimental env overrides; UAT may pin experimental. *(Slice 3)*
4. **Credential isolation** — UAT uses **separately-scoped** API keys (independent budget =
   blast-radius boundary), kept in the UAT checkout's gitignored `.env`, never committed.
5. **Published-ledger isolation** — UAT must not export to the prod Codex (`LEIBNIZ_LEDGER`).
   *(launch guard refuses a non-UAT-scoped ledger; publish guard refuses a UAT row)*
6. **Naming** — UAT state lives under `.leibniz-uat/`; the launcher echoes
   `LEIBNIZ_INSTANCE` so it is visually obvious which environment is being touched.
7. **Blast radius** — a UAT failure can corrupt only UAT state; it can never corrupt PROD.

## 4. Folder topology

```
Claude_Primary/
├── leibniz/                 PRODUCTION checkout (tracks a soak-validated tag)
│   └── .leibniz/            prod ledger + frontier + notebook + provenance
└── leibniz-uat/             UAT checkout (soaks new main)         ← create this
    └── .leibniz-uat/        uat ledger + frontier + notebook + provenance
```

Create the UAT checkout as a git worktree (shares the object store, separate working tree):

```bash
cd /Users/dave/Claude_Primary/leibniz
git worktree add ../leibniz-uat main
cd ../leibniz-uat
pip install -e ".[verify,propose,dev]"
cp deploy/profiles/uat.env.example deploy/profiles/uat.env   # then fill if needed
# put SEPARATELY-SCOPED keys in ./.env (gitignored): ANTHROPIC_API_KEY, OPENROUTER_API_KEY, HF_API_KEY
```

## 5. Deploy profiles + the launcher

Profiles live in `deploy/profiles/`. Only the `*.env.example` templates are committed; the
filled `*.env` files are gitignored (operator-specific). Launch via:

```bash
scripts/run_instance.sh uat              # 8x3 calibrate run at the profile's USD cap
scripts/run_instance.sh prod -- python3 -u scripts/calibrate_discovery.py 8 3 20
```

`run_instance.sh` sources the profile, runs the **isolation guard** (`python3 -m
leibniz.deploy` — refuses a non-prod profile that points at prod state, or a prod profile
that points at UAT state), then execs the command. The runtime write-barrier remains the
backstop if the guard is ever bypassed.

For a long unattended soak (same pattern as the organic runs):

```bash
cd /Users/dave/Claude_Primary/leibniz-uat
nohup caffeinate -i scripts/run_instance.sh uat > /tmp/uat_soak.log 2>&1 &
```

## 6. The promotion gate (UAT → PROD)

Promotion is deliberate and gated — never automatic:

1. **`pytest -q` green** on the candidate `main` (invariants byte-identical).
2. **UAT soak** — run the candidate on real cycles in `leibniz-uat/`; inspect dispositions,
   cost, and any gate relaxations. Compare the UAT ledger against the prior baseline.
3. **Validation report** — record what changed, the soak's known/promulgated/cost mix, and
   any regressions. (The per-instance provenance JSONL ties results to the exact kernel image
   + corpus version that produced them.)
4. **PROD adopts the tag** — tag the soak-validated commit; the prod checkout fast-forwards to
   it. PROD pins the audited image/corpus in code; bumping a pin is its own reviewed change.

## 7. Operator runbook (quick reference)

```bash
# one-time: create the UAT worktree + profile (see §4)
git worktree add ../leibniz-uat main

# check a profile is isolated before launching
set -a; source deploy/profiles/uat.env; set +a; python3 -m leibniz.deploy

# run UAT / PROD
scripts/run_instance.sh uat
scripts/run_instance.sh prod

# audit provenance (which kernel image + corpus produced this instance's laws)
cat .leibniz-uat/provenance-uat.jsonl

# publish (PROD only; the guard enforces instance==prod + confirmation)
#   see scripts/export_calculemus.py + Calculemus.publish
```

## 8. What this slice does NOT do

- It does not create real `*.env` files or real scoped credentials (operator action).
- It does not stand up the `leibniz-uat/` worktree automatically (one `git worktree add`).
- It does not change cadence/scheduling; the daemon's circadian phase is unchanged. A
  scheduled soak is just `run_instance.sh uat` under `nohup caffeinate` (or cron).
