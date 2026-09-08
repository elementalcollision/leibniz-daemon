---
type: Component
title: Sound Backends and the Observatory Tier
description: The SoundFaithfulnessBackend protocol (ADR 0037) generalizes the checker seam — Walnut (FO over k-automatic sequences, sound over unbounded n), SOS/Positivstellensatz, and a kernel bridge — each exact-or-DEFER with a re-checked certificate; the Walnut-decided Observatory tier (ADR 0038) is a separate, non-Q.E.D. ledger of mechanically decided theorems.
tags: [sound-backends, walnut, observatory, sos, positivstellensatz, certificate, recheck, non-qed, decidability]
---

# Sound Backends and the Observatory Tier

The faithfulness gate's bounded-Z3 gaming spine is a **pointwise, bounded-box** `[0,64]` linter over a tiny arithmetic DSL. ADR 0036/0037 generalized the checker seam so additional **sound** engines can decide unbounded/exact classes the box cannot — each behind the unchanged trust boundary, crawl-walk-run.

## The SoundFaithfulnessBackend protocol (ADR 0037)

`leibniz/gates/sound_backends.py` defines the protocol a sound backend satisfies:

- **PASS requires a re-checked certificate.** `is_pass_with_certificate()` is the gate: a PASS whose `Certificate` is missing or not `rechecked` is downgraded to DEFER. A backend cannot launder a pass it did not independently verify.
- **MECHANICAL, never JUDGED.** The LLM judge stays exactly where it is in `FaithfulnessGate` — reached only when every sound backend DEFERs.
- **exact-or-DEFER.** The backend returns DEFER, never a guess, when it cannot soundly decide; a FAIL is a sound *refutation* (statement diverges from claim).

The gate owns the `CertificateRechecker` for each certificate **kind** (automaton-universality for `walnut-automaton`, `ring` for `sos`, the Lean kernel for `kernel-bridge`). The backend's self-reported `rechecked` flag is **advisory**; the gate's own re-check is authoritative. This pins soundness structurally rather than trusting an honest tag.

The registered backends (run cheapest-first, after the gaming spine, before the probe):

| Backend | Class | Reach |
|---|---|---|
| Walnut | `leibniz/backends/walnut.py` | FO over k-automatic sequences — sound over **unbounded** n (Büchi–Bruyère) |
| SOS / Positivstellensatz | (probed, build deferred) | exact rational re-check stdlib-only; reaches `∀x∈ℝⁿ` |
| Kernel bridge | (deferred) | a full kernel re-check of a proof term |

## The Walnut-decided Observatory tier (ADR 0038)

`leibniz/observatory.py::WalnutObservatory` is a **separate, non-Q.E.D. ledger** of theorems mechanically **decided** by Walnut over unbounded n. Here the claim's `walnut_predicate` **is** the theorem (e.g. Thue–Morse overlap-freeness), and Walnut decides it as a sound decision procedure. A DECIDED result is MECHANICAL and re-checked (the automaton-universality certificate), but it is **not** `Q.E.D.`:

- It **never** sets `promulgated`, never produces a `Demonstratio`/`kernel_verified`/`Q.E.D.` (invariants 1 & 7 keep those kernel-only).
- It does **not** pass through `Promulgate`/`TrustPolicy.validate_path` — it is a parallel output identified solely by `FinishReason.WALNUT_DECIDED`.
- Faithfulness (predicate ↔ human claim) is handled by **formal-first** publication: the Walnut predicate + numeration is the statement of record, prose is commentary. No renderer is promoted into any TCB.
- The provenance edge is `WALNUT_DECISION_EDGE` ("walnut_decision"), deliberately **not** one of the promotion edges, so a Walnut-decided record can never satisfy `validate_path` even if mistakenly run through it.

**OFF BY DEFAULT**: nothing wires this into the assembled pipeline; the operator opts in, and the runner DEFERs (→ UNPROVEN) whenever Walnut is absent/errors.

## The Observatory faithfulness lint (ADR 0039)

`leibniz/observatory_lint.py` is a machine-checkable spec of the property the predicate is **meant** to encode, from a closed whitelist of families (`power_free`, `avoids_factor`, `avoids_pattern`). High-level parameters only (e.g. `exponent=4`) — the error-prone bound arithmetic lives solely in `walnut_predicate`, so this independently pins the predicate's **intent**. Brute-forced over a finite prefix before a DECIDED-true is filed; a prefix counterexample ⇒ the predicate is unfaithful ⇒ quarantine. When `require_descriptor=True`, a DECIDED-true with no usable `property_descriptor` is refused (the formal-first record then has no machine-checkable anchor).

## The measured conclusion

Across two independent sound backends (Walnut + SOS), the soundly-checkable **and** finitely-encodable region is the textbook region — a perfect anti-correlation held (everything in-reach was textbook; everything plausibly-novel left the backend's encodable class). The binding constraint moved one level deeper: **novelty at the producer — a structural encoding gap — not soundness, reach, or prover power** (`docs/discovery-ceiling-cross-backend-finding.md`). See [Optimization Roadmap](../roadmap.md) for the disposition.
