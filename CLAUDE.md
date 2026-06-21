# CLAUDE.md — Leibniz · *Calculemus*

Agentic theorem daemon. LLMs **propose**; only mechanical checkers (the Lean
kernel, Z3) **decide**. Full context in `README.md`, `docs/architecture.md`, and
the ADRs under `docs/adr/`. Work plan and porting notes in `HANDOFF.md`.

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

## Before you touch a trust edge

Read `docs/adr/0001-charter-and-trust-hierarchy.md` and
`docs/adr/0002-faithfulness-gate.md` first. They record decisions already made;
do not relitigate them in code.

## Commands

```bash
pip install -e ".[verify,propose,dev]"   # core is stdlib-only; extras add Z3/Lean/LLM
python demo.py                            # turn one circadian cycle (deterministic fakes)
pytest -q                                 # trust invariants must stay green
ruff check .                              # lint
```

## Layout

```
leibniz/
  types.py · trust.py · propositio.py · pipeline.py · daemon.py
  gates/{faithfulness,novelty,verification}.py
  selection.py · verifiers.py · adapters.py
docs/adr/{0001,0002}.md · docs/{capability-ladder,architecture}.md
tests/test_invariants.py · demo.py · HANDOFF.md
```

## Conventions

- Ledger vocabulary is Latin: Enuntiatio (claim) / Expressio (formal statement) /
  Demonstratio (proof). Mirrors the sibling repo `newton-daemon`.
- Every decision attaches an `EdgeEvidence` with an explicit `TrustTier`. Tag the
  tier honestly; the policy and tests read it.
- New design decisions get an ADR (next number after 0002). Don't bake a
  reversible architectural choice into code without one.
- The current rung is **R0 (scaffold, green)**. Next is **R1 (real Lean kernel)**.
  See `HANDOFF.md` for the rung tickets and exit tests — not this file.
