# Security Policy

Leibniz exists to hold one property invariant: **LLMs propose; only mechanical checkers
(the Lean kernel, Z3, exact‑rational / finite‑field decision procedures) decide.** A
"security issue" here is therefore broader than the usual sense — anything that could let
an *unverified proposal* pass as a *decided law* is a vulnerability, even if it never
touches a credential.

## Reporting a vulnerability

Please report privately, **not** in a public issue or PR:

- Use GitHub's **[Private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)**
  on this repository (Security → *Report a vulnerability*), or
- email the maintainer at the address on the GitHub profile of **@elementalcollision**.

Include a minimal reproduction and the commit/PR you observed it on. We aim to acknowledge
within a few days.

## In scope — the trust boundary

The highest‑severity class is any way to **breach the trust boundary**. Concretely, report
if you find a path that:

- lets `Demonstratio.kernel_verified` be set anywhere other than
  `leibniz/verifiers.py::LeanVerifier.discharge`, or mints a `TrustTier.MECHANICAL` proof
  edge without a real kernel decision;
- promulgates a law without `TrustPolicy.validate_path` passing (it is called from
  `VerificationGate.is_promotable`);
- lets an LLM/proposal role decide novelty or faithfulness outside the budget‑bounded
  OPEN_FORM fallback;
- causes `native_decide`, `sorry`, an admitted lemma, or an unaudited axiom to be accepted
  as a kernel decision by any backend;
- makes a *report‑only* backend (Coq/Isabelle, ADR 0048) write `kernel_verified`, mint a
  proof edge, or import `leibniz/trust.py`;
- would let a change to `leibniz/trust.py`, `leibniz/verifiers.py`, or
  `tests/test_invariants.py` / `tests/test_boundary_guards.py` /
  `tests/test_kernel_verified_writers.py` land **without** operator (CODEOWNERS) review, or
  makes the `invariants` CI check pass vacuously (e.g. "0 tests collected").

Also in scope: standard issues (dependency CVEs, CI/token privilege escalation, workflow
injection, self‑hosted‑runner abuse).

## Out of scope

- The **content** of a published law is decided by the kernel, not by us; a mathematically
  surprising but kernel‑verified result is not a vulnerability.
- The repository intentionally contains **no secrets**. `.env` is git‑ignored and only
  `*.env.example` placeholder templates are tracked. Do not submit real credentials in a PR;
  they will be treated as compromised.

## Enforcement layers

The boundary is defended in depth (HANDOFF §4): (1) the invariants encoded in
`leibniz/trust.py` and `tests/test_invariants.py`; (2) the `TrustPolicy` gate; (3) the
PreToolUse hook `.claude/hooks/guard-trust-files.py` (interactive‑session layer); (4)
`CODEOWNERS` + branch protection + the required `invariants` CI check (merge‑path layer). A
report that defeats *any* layer is valuable even if the others would have caught it.
