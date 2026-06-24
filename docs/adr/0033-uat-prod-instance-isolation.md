# ADR 0033 — UAT / Production instance isolation (the trust-safe fork)

- Status: **Accepted** (2026-06-24) — design decided; implementation **staged** (Slice 1,
  instance-tag + write-barrier, in progress). The broader fork (separate checkout + deploy
  profiles) follows the slices below.
- Date: 2026-06-24
- Related: ADR 0001 (charter & trust hierarchy), ADR 0008 (promotion ≠ publication), ADR 0013
  (edge provenance), ADR 0016 (persistent runtime), ADR 0025 (proof persistence / DB
  migration). Sibling precedent: Leonardo `UAT_PLAN.md` + `deploy-uat.sh`; Newton ADR 0014
  (config table) / 0035 (topology). Targets: `runtime.py`, `calculemus.py`, `assembly.py`,
  `corpus.py`, deploy config. Roadmap: ops/soak.

## Context

Leibniz has reached the trigger for a UAT/Prod split: a **valuable accumulating ledger** (the
Calculemus Codex the operator publishes) **+** **fast, trust-relevant iteration**. The evidence
is recent — a faithfulness-gate change (ADR 0031 L2) was shipped and reverted on `main` the same
day; on a single codeline that is a production scare. The house pattern already exists: Leonardo
is fully forked (`leonardo/` prod, `leonardo-uat/`), Newton is mid-adoption (ADR 0014/0035). Both
converge on one model: **the daemon code never branches; only the deploy configuration diverges.**
UAT soaks new `main`, then PROD adopts the soak-validated tag. Separation is enforced at every
load-bearing layer (distinct state/ledger/credentials/ports/cadence/cost-cap), with a scoped
credential as the blast-radius boundary.

**Leibniz adds a constraint the siblings do not have: the trust boundary.** A study of the
current code found Leibniz has **no instance isolation today** — the runtime DB carries no
instance tag, and `Calculemus.promulgate`/`publish` read no instance context. So a
**UAT-promulgated "law" could be published as a PROD law.** That single failure mode is what this
ADR exists to make impossible.

## Decision

### 1. The fork model — same code, divergent deploy config

UAT and PROD run the **identical `leibniz` codebase**. They differ only in a deploy profile
selected by `LEIBNIZ_INSTANCE` (`prod` | `uat` | `dev`, default `dev`) plus the existing path/knob
env vars. UAT is a separate working tree (`leibniz-uat/`) that fast-forwards `main`/experimental
branches and **soaks**; PROD tracks a soak-validated tag. Promotion is a deliberate gated
hand-off (pytest-green → UAT soak → validation report → PROD deploy), never automatic.

Per-instance divergence (mirrors Leonardo/Newton):

| Layer | PROD | UAT |
|---|---|---|
| runtime ledger | `LEIBNIZ_RUNTIME_DB=.leibniz/memory.db` | a separate path |
| frontier / notebook | `.leibniz/{frontier,notebook}.json` | separate paths |
| corpus / Lean image | pinned, audited | may pin experimental |
| cost cap / cadence | conservative | higher cap, faster cycles |
| credentials | prod keys | **separately-scoped** keys (blast radius) |

### 2. The trust-safe isolation invariants (the load-bearing part)

1. **Per-instance ledger + write-barrier.** Each instance writes its own DB. A
   `PersistentRuntime` refuses to open a DB that already holds candidates from a *different*
   tagged instance (the write-barrier) — so a misconfigured UAT pointed at the PROD ledger
   **fails closed** instead of interleaving.
2. **Indelible provenance.** Every candidate row is stamped with its `instance`. A UAT
   promulgation is permanently marked UAT and can never be mistaken for PROD.
3. **Publish guard.** `Calculemus.publish` reads the **PROD ledger only**, requires explicit
   instance confirmation, and the rendered colophon shows the instance — so the operator cannot
   accidentally publish a UAT law.
4. **Pinned kernel + corpus per instance.** UAT may run an experimental Lean image / corpus;
   PROD pins the audited ones. The image tag and corpus version are recorded per instance.
5. **The trust floor is frozen in BOTH.** `tests/test_invariants.py` stays byte-identical;
   `LeanVerifier.discharge` is the sole `kernel_verified` writer; N+1 and promotion≠publication
   hold identically. **UAT may relax ONLY the novelty and faithfulness gates** (e.g. DEFER for
   speed) — it may **never** touch the kernel floor. A UAT law is still kernel-true; it is simply
   not PROD-grade-audited, and the provenance + publish guard keep it out of the public Codex.

### Why a UAT law can never become a published PROD law (layered)

separate ledgers (1) → if mispointed, the write-barrier refuses (1) → if it still ran, the row is
stamped UAT (2) → publish reads PROD-only and shows the instance (3) → and the operator must
confirm (ADR 0008). Five independent layers; any one suffices. None depends on the kernel floor,
which is frozen anyway (5).

## Implementation plan (staged)

- **Slice 1 (now): instance-tag + write-barrier** — `LEIBNIZ_INSTANCE`; idempotent
  `ADD COLUMN instance` migration (ADR 0025 pattern); stamp on `remember()`; barrier on init.
  Pure SQLite/Python; `test_invariants.py` untouched.
- **Slice 2: publish guard** — `Calculemus.publish` PROD-only + instance confirmation + colophon
  instance line.
- **Slice 3: per-instance kernel + corpus pinning** — `build_daemon(instance=…)` selects image
  tag / corpus; record versions.
- **Slice 4: the fork itself** — `leibniz-uat/` checkout, deploy profiles, a `UAT_PLAN.md`-style
  runbook, scoped credentials.

## Validation

- **Unit (CI-safe, no Lean):** two instances → separate DBs, no cross-talk; the write-barrier
  refuses a cross-instance DB (fail-closed) while a fresh or same-instance or legacy-untagged DB
  is accepted; every row carries its `instance`; the publish guard refuses a UAT-tagged law.
  These live in `tests/test_uat_prod_isolation_r0033.py` — NOT in `test_invariants.py`, which
  stays frozen.
- **Trust floor unchanged:** `test_invariants.py` byte-identical; the boundary guards still pass.

## Consequences

- A clean, auditable separation: UAT breaks fast on the discovery machinery; the trust floor and
  the published ledger are unbreachable from UAT by construction.
- Small additive surface (one column, one barrier, one publish check, one config flag); fully
  back-compatible (legacy untagged rows are accepted; default instance `dev`).

## Open questions

- Whether to back-fill the existing `.leibniz/memory.db` rows to `instance='prod'` (protects the
  real ledger immediately) or leave them legacy-untagged (no mutation of the real ledger). Slice 1
  is lenient on legacy rows; back-fill can be a separate, explicit operator step.
- Cryptographic promulgation seal (HMAC over `kernel_verified`+proof) vs the plain `instance` tag
  — the tag + write-barrier + publish guard suffice for accidental contamination; a seal would
  additionally defend a *tampered* DB. Deferred unless a threat model requires it.
