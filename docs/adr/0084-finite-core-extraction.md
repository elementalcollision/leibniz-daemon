# ADR 0084 — Extract the stated finite-core parameters of a queued paper

- Status: accepted
- Date: 2026-07-28
- Depends on: ADR 0069 (the feed), ADR 0083 (targets steer), ADR 0041 Phase 4 (proposer seams)

## Context

ADR 0083 put queued papers into the conjecture prompt as titles. A title is a weak hint: a
proposer aims far better at *"srg(1666, 105, 0, 21)"* than at *"On the non-existence of a strongly
regular graph"*. Every one of the daemon's eleven amplifications turned on a small tuple of stated
parameters — an srg quadruple, an explicit order (complex Hadamard 94), a basis count (Cabello's
14), a projective-plane parameter (double blocking 3q−1).

## Decision

`extract_core_parameters(title, summary)` — deterministic regex over the paper's own words for
exactly those shapes, LLM-free like `finite_core_score`. The feed now also retains a bounded slice
of the abstract (`_SUMMARY_CAP = 1500`), because extraction cannot read what the queue discards.
Results ride on the TARGET seed's payload and appear in the steering block as
`[stated: srg_parameters=(1666, 105, 0, 21)]`.

### Anti-fabrication is the load-bearing property

Every extraction carries the **verbatim span** it was read from, and a span that is not literally
present in the source is dropped. This is the discipline `seeds.py` already applies to FLOOR
values — `proof_of_use`, *"a reference tying the value to the source span"* — applied to
parameters. Pinned by test: every value and every span must appear literally in the source; a
number not present is never invented; `3 x 4` never yields `12`, because nothing infers or
computes.

### What this is not

It reports what a paper **says**. It verifies nothing, decides nothing, and is not evidence. The
parameters are an untrusted hint about *where a finite core might be*; the block still declares
itself untrusted, the seed is still a TARGET that can never become a `SandboxTask`, and every
resulting conjecture runs the full cheap-refute → novelty → faithfulness → kernel chain.

## Consequences

The conjecturer now sees the actual numbers, which is the difference between "try something about
strongly regular graphs" and "try srg(1666, 105, 0, 21)".

**This is one step of core extraction, not the whole of it.** The daemon still cannot fetch a PDF,
read a proof, or build the finite certificate — the step that turned each of those eleven papers
into a kernel-checked law was a human (or an agent) constructing the artifact. What is automated
here is the first and most mechanical part: knowing *which* finite object the paper is about.

The honest next question is measurable rather than architectural: do parameter-bearing hints
produce amplification-shaped conjectures? If they do, the increment after this is certificate
scaffolding for the commonest shape (srg non-existence has the clearest recipe). If they do not,
more extraction will not help, and the gap is in the conjecturer's reach rather than its
information.
