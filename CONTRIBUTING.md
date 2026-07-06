# Contributing to Leibniz

Leibniz is an agentic theorem daemon and its *Codex Calculemus* reading‑room. Its reason to
exist is a single, non‑negotiable invariant:

> **LLMs propose; only mechanical checkers — the Lean 4.31 kernel, Z3, and exact
> rational / finite‑field decision procedures — decide.** No "the proof looks right"
> shortcut ever reaches a promulgated law.

Outside contributions are welcome, but this repository is **source‑available and hardened**:
every PR is reviewed, CI is a hard gate, and changes to the trust boundary are
operator‑only. Please read this before opening a PR.

## The trust boundary is off‑limits

These files encode the property above. A PR **must not weaken them**, and any change to them
requires review from the code owner (`@elementalcollision`) via `CODEOWNERS` — an ordinary
PR touching them will be blocked at the merge path:

- `leibniz/trust.py`, `leibniz/verifiers.py`, `leibniz/types.py`, `leibniz/propositio.py`,
  `leibniz/pipeline.py`, `leibniz/gates/`
- `tests/test_invariants.py`, `tests/test_boundary_guards.py`,
  `tests/test_kernel_verified_writers.py`
- `.claude/hooks/guard-trust-files.py`, `.claude/settings.json`, `.github/`

If your change *appears* to require editing one of these to pass, stop — that almost always
means it is weakening the boundary. See `CLAUDE.md` (trust invariants) and
`docs/adr/0001‑charter‑and‑trust‑hierarchy.md` / `0002‑faithfulness‑gate.md`, which record
decisions already made; do not relitigate them in code. Genuine strengthening of the
boundary is very welcome — open an issue first so we can discuss it.

## What good contributions look like

- **New verification‑amplification cycles**: independently re‑decide a recently published
  result with an exact mechanical decider (Lean `decide` / Z3 / exact‑rational /
  finite‑field / exact enumeration). Follow the existing pattern — a `scripts/verify_*.py`
  producer, a downloadable certificate under `docs/crt/`, tests, a results doc, and a
  Calculemus cycle exporter. The data a cycle rests on must be **exact** and either printed
  in the source or reconstructible from stated axioms — never a floating‑point or
  interval‑only witness.
- **New backends stay report‑only** unless promotion is separately, operator‑gated (ADR
  0048): a backend may *observe* a kernel, but must never set `kernel_verified`, mint a
  proof edge, or import `leibniz/trust.py`.
- Bug fixes, docs, and reading‑room (`site/`) improvements.
- New design decisions get an **ADR** (next number after the highest in `docs/adr/`).

## PR requirements

- **CI must be green.** The `invariants` job runs the trust‑invariant tests, guards against a
  vacuous "0 collected" pass (`pytest` must collect ≥ 11 nodes), turns one demo cycle, and
  runs `ruff check .`. Keep the tree ruff‑clean.
- Add tests for new behaviour; keep `pytest -q` green.
- Keep the core **stdlib‑only** (extras add Z3 / Lean / LLM / dev tooling).
- **Do not** commit `node_modules/`, build artifacts, large binaries, or any credential.
  `.env` is ignored; only `*.env.example` templates are tracked.
- Workflows must use the `pull_request` trigger (never `pull_request_target`) and must not
  require secrets — fork PRs run with a read‑only token and no secrets, by design.
- Sign your commits if you can (encouraged, not required), and keep the history linear‑ish
  with focused commits.

## Reporting security / trust issues

Do **not** open a public issue for a trust‑boundary breach or a vulnerability — see
[`SECURITY.md`](SECURITY.md).

## License

By contributing you agree that your contribution is licensed under the repository's
**PolyForm Noncommercial License 1.0.0** (see [`LICENSE.md`](LICENSE.md)).
