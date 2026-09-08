# CLAUDE.md — Leibniz · *Calculemus*

Agentic theorem daemon. LLMs **propose**; only mechanical checkers — the Lean 4.31
kernel, Z3, and exact rational / finite-field / exact-enumeration decision
procedures — **decide**. Full context in `README.md`, `docs/architecture.md`, and the
ADRs under `docs/adr/`. **Start a fresh session from `HANDOFF-NEXT.md`** (self-contained
launchpad + playbook); `HANDOFF.md` is the porting history and rung tickets.

## Trust invariants — the reason this project exists

These are non-negotiable. They are enforced in code by `leibniz/trust.py` and by
`tests/test_invariants.py`; this file restates them so they stay in context.

1. **YOU MUST NOT** let an LLM decide a proof. `Demonstratio.kernel_verified` is
   set only inside `leibniz/verifiers.py::LeanVerifier.discharge`, and the proof
   edge is always `TrustTier.MECHANICAL`. No "the proof looks right" shortcut.
2. **YOU MUST NOT** promulgate unless `TrustPolicy.validate_path` passes. It is
   called from `VerificationGate.is_promotable`. Do not bypass it.
3. LLMs occupy only the proposal roles in `leibniz/types.py::Role`. The *only*
   place LLM judgment may reach a promulgated law is the OPEN_FORM faithfulness
   fallback, and it is budget-bounded.
4. Novelty is settled by retrieval + a decision procedure, never by a judge.
5. Run the cheap gates before the expensive one: cheap-refutation → novelty →
   faithfulness all happen in `FORMALIZE`, before any proof compute in `DERIVE`.
6. Candidates are quarantined with a `FinishReason`, never deleted.
7. `Q.E.D.` is stamped iff `kernel_verified`. Never hand-set it.

If a change you are about to make would require editing `tests/test_invariants.py`
to pass, STOP — you are weakening the trust boundary. Surface it to the operator.
A memory file is context, not enforcement; the tests and `TrustPolicy` are the
enforcement. For a hard block, add a PreToolUse hook.

Two more rules bind just as hard, enforced *elsewhere* than `test_invariants.py`:

8. **Kernel hygiene.** `native_decide` is forbidden; `sorry`, admitted lemmas and
   unaudited axioms are never a kernel decision. `#print axioms` must show only
   Lean's canonical trusted axioms (`propext`, at most `Classical.choice` /
   `Quot.sound`) — **never `sorryAx`**. → `leibniz/backends/lean_axioms.py`
9. **New kernels are report-only** (ADR 0048). Coq/Rocq and Isabelle may *observe*
   a kernel; they must never set `kernel_verified`, mint a proof edge, or import
   `leibniz/trust.py`. Promotion is deferred and operator-gated. →
   `tests/test_boundary_guards.py`, `tests/test_kernel_verified_writers.py`

## Before you touch a trust edge

Read `docs/adr/0001-charter-and-trust-hierarchy.md` and
`docs/adr/0002-faithfulness-gate.md` first. They record decisions already made;
do not relitigate them in code.

## Commands

```bash
pip install -e ".[verify,propose,dev]"   # core is stdlib-only; extras add Z3/Lean/LLM
python demo.py                            # turn one circadian cycle (deterministic fakes)
pytest -q                                 # 1,885 tests; the 11 invariants must stay green
ruff check .                              # lint (rule set pinned in pyproject; CI blocks on it)
scripts/run_kernel_tests.sh               # Docker-gated kernel lane; a silent skip is a FAILURE
PYTHONPATH=. python scripts/heartbeat.py  # one autonomous beat, by hand (ADR 0068)
```

Kernel images: `leibniz-lean:v4.31.0` + `leibniz-lean-repl:v4.31.0`
(`docker/{lean,lean-repl}.Dockerfile`). Lean-marked tests skip cleanly where absent.

## Layout

```
leibniz/
  types.py · trust.py · propositio.py · pipeline.py · daemon.py    # guarded core + six stages
  gates/{faithfulness,novelty,verification}.py                     # the three gates (guarded)
  gates/{lean,boolean,minmax,mixed_modulus,power_mod,factgcd}_decided.py  # 6 kernel-decided fragments
  verifiers.py · backends/                  # LeanVerifier (sole kernel writer) · Lean/Z3/cvc5/Walnut/Coq/Isabelle
  probes.py · dsl_to_lean.py · corpus.py · structural.py           # claim probes · renderer · novelty
  selection.py · discovery.py · consensus.py · proof_repair.py     # KFM · frontier band · N+1 · repair panel
  providers/ · arxiv_feed.py · seeds.py · seed_intake.py           # proposal models · the moving frontier
  calculemus{,_site}.py · origination.py · newton_exchange.py      # ledger · provenance · Newton folios
  observatory.py · runtime.py · instance_config.py · budget.py     # non-Q.E.D. tier · state · pins · caps
scripts/       # heartbeat · run_live · amplify · verify_* · export_*   (see HANDOFF-NEXT §4)
deploy/{heartbeat,profiles}/ · docker/ · lean-project/ · site/
docs/adr/0001..0092 · docs/{architecture,capability-ladder,optimization-roadmap}.md
docs/{results,crt,audits,runbooks}/ · tests/   # 11 byte-frozen invariants + ~1,870 more
```

## Conventions

- Ledger vocabulary is Latin: Enuntiatio (claim) / Expressio (formal statement) /
  Demonstratio (proof). Mirrors the sibling repo `newton-daemon`.
- Every decision attaches an `EdgeEvidence` with an explicit `TrustTier`. Tag the
  tier honestly; the policy and tests read it.
- New design decisions get an ADR (next number after **0092**). Don't bake a
  reversible architectural choice into code without one.
- The rung climb **R1 → R6 is complete** (real Lean 4.31 kernel via Docker; faithfulness via
  Z3 *and* six kernel-decided fragments; novelty retrieval; proposal models + the ADR 0029 repair
  panel; KFM / MAP-Elites archive; the *Calculemus* reading-room + operator publish gate), all
  behind the unchanged trust boundary. The project is in the **post-R6 optimization phase**
  (discovery yield), where the binding constraint is **novelty**, not prover reach or the trust
  boundary. The live work plan is **`docs/optimization-roadmap.md`**; `HANDOFF-NEXT.md` §3 holds
  current state. Do not trust this bullet for fine status — read those.
- **What the daemon is actually good at is verification-amplification:** re-deciding a recently
  published result's finite core with an exact decider (kernel-decided / exact-procedure /
  cross-kernel tiers). The second path is **origination** — its own conjecture, which must PASS
  the full mechanical novelty gate to carry that provenance (ADR 0050/0063).
- **Autonomous novelty is a measured, closed question.** Four converging probes plus a
  producer-method sweep found that the soundly-checkable *and* finitely-encodable region is the
  textbook region; the constraint is the **producer**, not the checker. Read
  `docs/autonomous-discovery-arc-capstone.md` before proposing another backend — that lever is
  spent, and the re-open gate is written down.
- The daemon **runs itself**: a nightly launchd beat (ADR 0068) turns capped, journaled cycles
  against `origin/main` (never a working tree) and files promulgations into
  `.leibniz/review_queue.md`. Publication is still the operator's ADR 0033 act — nothing
  publishes itself. The four-phase autonomy plan (heartbeat / moving frontier / reach / Newton
  exchange) is complete: ADRs 0068-0081, plus drift detection (0082) and the beat watchdog +
  stale-journal alarm (0092). Beat state lives in `.leibniz/`.
- **The repo is public and hardened** (ADR 0049), and **the operator merges.** Branch each unit of
  work off `origin/main`; never push to `main`, never force-push, never merge your own PR. CI's
  `invariants` job is a hard gate and must not pass vacuously.
- **Adversarial review is a standing gate on the trust surface, not a judgment call.** Every
  trust-edge defect found in the 2026-07-24→28 sweep came from a skeptic agent with a kernel, never
  from re-reading; one surfaced *after* the change was declared safe, and one hid inside a
  fail-open `except` whose failure mode was indistinguishable from success. It keeps paying:
  ADR 0089 (two more fail-open guards), ADR 0090 (bound what the predicate guard *admits*, not
  just its size), ADR 0087 (a queue feature that blanked the operator's primary artifact on a
  pre-migration DB). Before claiming a change to the gates, the probe, the promotion path or the
  hash/identity keys is sound, have it attacked.
