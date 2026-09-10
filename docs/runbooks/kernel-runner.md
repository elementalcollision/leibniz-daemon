# Runbook — the `lean` self-hosted runner for `kernel-nightly`

## Read this before registering anything

**This repository is PUBLIC.** Running a self-hosted runner on a public repository is the one
configuration GitHub explicitly warns against, because a fork's pull request can execute arbitrary
code on the machine hosting the runner. That is not a theoretical concern; it is the documented
failure mode.

Today the exposure is closed: `kernel-nightly.yml` is triggered only by `schedule` and
`workflow_dispatch`, so no fork can fire it (ADR 0049). As of ADR 0093 that is no longer just a
comment — `tests/test_selfhosted_exposure_r0093.py` fails the BLOCKING invariants job if any
workflow ever pairs a self-hosted job with a fork-reachable trigger.

Register a runner only if you accept that the machine runs code from this repository on a schedule.
If you would rather not, **the honest alternative is to delete the kernel lane** rather than leave
it queueing forever — see "If you decide not to" below.

## Why this runbook exists

Measured 2026-09-08: **60 scheduled runs since 2026-07-11, zero successes.** Fifty-nine were
cancelled (GitHub expires an unclaimed job after 24 h) and one had been queued 3 h. Zero
self-hosted runners are registered. A lane whose commit message calls it *"no-silent-skip"* had
been silently skipping every night for two months, because an expired queue and a night that has
not happened yet look identical in the Actions tab.

ADR 0093 adds a GitHub-hosted `runner-guard` job that fails loudly after 10 minutes when nothing
claims the kernel job. It never reports the kernel lane as passing — absence is reported as absence.

## Prerequisites on the host

The kernel lane needs Docker and the operator-local `leibniz-lean` image (there is no in-repo
Dockerfile). Verify before registering:

```bash
docker info >/dev/null && echo "docker: up"
docker image inspect leibniz-lean:v4.34.0-rc2      >/dev/null && echo "kernel image: present"
docker image inspect leibniz-lean-repl:v4.34.0-rc2 >/dev/null && echo "repl image:   present"
python3 --version                              # the lane installs 3.11 itself via setup-python
```

## Registering

The registration token is short-lived and account-scoped. **Generate it yourself** — do not paste
it into a chat, a script, or an issue:

Settings → Actions → Runners → **New self-hosted runner**, then follow GitHub's generated commands.
The only thing this repository requires of them is the label:

```bash
./config.sh --url https://github.com/elementalcollision/leibniz-daemon \
            --token <TOKEN-FROM-THE-SETTINGS-PAGE> \
            --labels lean \
            --ephemeral                 # STRONGLY recommended: one job per registration
```

`--ephemeral` matters. The runner deregisters after a single job, so a compromised job cannot
persist on the host or poison a later run. It costs a re-registration per night, which a
`launchd`/`systemd` unit can automate.

Then run it. Prefer a dedicated non-privileged user, and do not run it as root:

```bash
./run.sh                       # foreground, for a first check
# or install as a service once you have seen it claim a job
```

Confirm it is visible:

```bash
gh api repos/elementalcollision/leibniz-daemon/actions/runners \
  --jq '.runners[] | "\(.name) \(.status) \(.labels | map(.name) | join(","))"'
```

Then trigger the lane by hand rather than waiting for 07:00 UTC:

```bash
gh workflow run kernel-nightly.yml
gh run watch "$(gh run list --workflow kernel-nightly.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
```

A healthy run shows `runner-guard` passing within seconds and `kernel` executing
`scripts/run_kernel_tests.sh`.

## If you decide not to register one

Leaving the lane in place with no runner is the state ADR 0093 was written about: it accumulates
cancelled runs that read as "not run yet". Either

- delete `.github/workflows/kernel-nightly.yml`, and say in the commit that the kernel lane is
  operator-local and run by hand via `scripts/run_kernel_tests.sh`; or
- keep it, in which case `runner-guard` will fail every night — which is noisy, but it is *honest*
  noise, and preferable to sixty invisible expirations.

Do not simply disable the guard. That restores the silence this ADR exists to remove.

## Security posture, restated

| control | where |
|---|---|
| no fork-reachable trigger on a self-hosted job | `kernel-nightly.yml`, enforced by `tests/test_selfhosted_exposure_r0093.py` |
| least-privilege token | `permissions: contents: read` (the guard adds `actions: read`, no writes) |
| ephemeral runner | `--ephemeral` at registration (operator choice, recommended) |
| non-root user | operator choice, recommended |

The first two are enforced in the repository. The last two are yours, and nothing here can check
them for you.
