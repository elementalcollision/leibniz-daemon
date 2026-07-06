# ADR 0049 — Public repository, hardened against outside incursion

**Status:** Accepted (2026-07-06). Supersedes nothing; complements ADR 0001 (charter & trust
hierarchy) and the HANDOFF §4 enforcement stack.

## Context

Leibniz has been a private repository. The operator has decided to make it **public** so the
*Codex Calculemus* ledger and the daemon that produces it can be read and independently
verified — while **preventing any outside voice from weakening the trust boundary** (LLMs
propose; only the kernel / Z3 / exact procedures decide).

Going public exposes the entire git history irreversibly, so a pre-flight audit was run
first. Findings:

- **No secrets in 450 commits.** Every credential pattern (`sk-ant`, `sk-or`, `ghp_`, AWS,
  Slack, HF tokens) returned zero. `.env` is git-ignored; only empty `*.env.example`
  placeholder templates are tracked. The two "secret-shaped" scan hits were both bytes
  inside `site/node_modules/` third-party packages (a compiled libvips `.dylib` containing a
  `BEGIN … PRIVATE KEY` fixture; an `hf_` substring in minified JS) — public npm content, not
  ours.
- **The anti-incursion architecture was already largely built**: `CODEOWNERS` requires
  operator review on the trust files, branch protection on `main` already requires the
  `invariants` CI check + a code-owner review and blocks force-push/deletion, CI uses the
  `pull_request` trigger (not `pull_request_target`) and touches no secrets.
- One real problem: **`site/node_modules/` was committed** — ~115 MB / 6,995 files, not
  ignored, pure bloat.

## Decision

1. **License: PolyForm Noncommercial 1.0.0** (source-available). Anyone may read, run, and
   verify the software and use it noncommercially; commercial use needs a separate license.
   (`LICENSE.md`; swap to PolyForm Strict / BUSL is a one-file change if stricter reuse terms
   are later wanted.)
2. **Purge `site/node_modules/` from history** with `git filter-repo` (rewrites all commit
   hashes; safe now — 0 forks, solo operator), and ignore it going forward (`node_modules/`,
   `**/node_modules/` in `.gitignore`; untracked via `git rm --cached`).
3. **CODEOWNERS** extended: a default `*` owner plus explicit rules on every trust-critical
   path, now including `tests/test_boundary_guards.py`,
   `tests/test_kernel_verified_writers.py`, `leibniz/pipeline.py`, `leibniz/gates/`, and the
   governance files (`.github/`, `CODEOWNERS`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE.md`,
   `docs/adr/`).
4. **Contributor governance**: `SECURITY.md` (private vulnerability reporting; the trust
   boundary is the top severity class) and `CONTRIBUTING.md` (the boundary is off-limits to
   outside PRs; report-only backends; CI is a hard gate; no secrets/node_modules).
5. **Least-privilege CI**: both workflows declare `permissions: contents: read`. Fork PRs
   already receive a read-only token and no secrets by virtue of the `pull_request` trigger.
6. **Self-hosted runner note**: `kernel-nightly.yml` runs on a self-hosted `lean` runner and
   therefore must never gain a `pull_request`/`pull_request_target` trigger — only `schedule`
   and operator `workflow_dispatch`. A self-hosted runner reachable from fork PRs is an RCE
   risk; this is documented in-file.

### Operator-applied settings (require admin; not expressible in-repo)

Applied at/around the visibility flip:

- flip visibility to **public** (the irreversible step — done last, after the audit is clean
  and this hardening has merged);
- **enable secret scanning + push protection** (GitHub Advanced Security, free on public);
- Actions → **"Require approval for all outside collaborators / first-time contributors"** so
  fork-PR workflow runs need operator approval;
- Actions → default workflow token permissions **read-only**;
- **disable the Wiki** (unused inbound surface); Issues stay enabled;
- verify branch protection survives the visibility change (required `invariants` check +
  code-owner review + no force-push/deletion).

Deliberately **not** adopted for now (operator's call, "current setup is correct"): required
signed commits, `enforce_admins`, disabling Issues. Each is a one-setting change if wanted.

## Consequences

- The trust boundary now has a **fifth** effective guard for the public world — the license
  and contributor policy — on top of the four in HANDOFF §4. An outside PR that weakens
  `trust.py` / `verifiers.py` / the invariant tests cannot merge without operator review and
  cannot pass CI if it breaks an invariant.
- The history rewrite changes every commit hash; anyone with an old clone must re-clone. This
  is acceptable given no forks exist.
- No secret was ever committed, so no credential rotation is required by the visibility flip.
