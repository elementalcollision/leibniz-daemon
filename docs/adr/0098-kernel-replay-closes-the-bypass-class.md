# ADR 0098 — Replay the kernel: closing the class ADR 0097 said could not be closed

- Status: **accepted — landed, mutation-checked with every syntactic guard disabled**
- Date: 2026-09-11
- Depends on: ADR 0097 (the axiom-footprint layer, and the measurement that motivated this),
  ADR 0095 (the 4.34 pin this is built against), ADR 0096 (the gap 0097 fulfils)
- Corrects: ADR 0097's assessment that the kernel-bypass class was not closable

## Context

ADR 0097 closed the **axiom-footprint** class — `native_decide`, admitted axioms, `sorry` — with a
compiled reporter that reads `Lean.collectAxioms` out of `ConstantInfo`, never elaborating
proposer syntax. It left the **kernel-bypass** class open, and argued the gap was open *in
principle*:

> a `run_cmd` can assemble `debug.skipKernelTC` from string fragments at elaboration time, so
> there is no string for any scan to match. Lean is a metaprogramming language, so a text scan
> over this class is defeatable in principle, not merely in this implementation.

**That reasoning was correct and the conclusion was wrong.** The premise rules out *scanning*; it
says nothing about *checking*. The reporter reads what the environment SAYS. Nobody was asking
whether the kernel would accept that environment at all — which is a different question, and the
one `lean4checker` exists to answer.

ADR 0097 also asserted lean4checker was unusable: *"stuck at v4.29.0-rc8 against the v4.34.0-rc2
pin, and olean formats are not forward-compatible."* That was inferred from the repository's
toolchain metadata rather than measured. **The actual API drift across five minor versions is one
added parameter**: v4.34 inserted `maxRecDepth : USize` into `Environment.addDeclCore`. The port
is two lines.

## Decision

**Vendor lean4checker and replay the kernel at the mint.**

`docker/lean4checker.Dockerfile` pins upstream to a SHA, applies
`docker/patches/lean4checker-v4.34.0-rc2.patch`, and **runs upstream's own test suite as a build
step** — `AddFalse`, `ReplaceAxiom` and the private-conflict cases exist for precisely this attack
class, so their passing is the evidence the port is sound rather than merely compiling. If they
fail, the image does not build.

It layers on the axcheck image, so **one compiled olean serves both checks**, and the replay runs
FIRST and short-circuits: a footprint is never read from an environment the kernel would reject.

The two questions are independent and neither subsumes the other:

| question | tool | what it catches |
|---|---|---|
| what does the environment SAY it depends on? | `lean-axcheck` | `native_decide`, admitted axioms, `sorry` |
| would the KERNEL accept this environment? | `lean4checker` | `skipKernelTC`, `unsafe` self-loops, ill-typed terms |

## Consequences — measured, with the guards switched off

With `check_proof` forced True **and** `smuggles_top_level`, `closes_more_than_it_opens`,
`statement_is_single_declaration` and `defeats_the_kernel` all forced open:

| input | before | after |
|---|---|---|
| honest `by decide` | passes | passes |
| `by native_decide` | refused | refused |
| literal `skipKernelTC` + `unsafe` | **stamped `Q.E.D.`** | **refused** |
| programmatic `skipKernelTC` | **stamped `Q.E.D.`** | **refused** |

`defeats_the_kernel` is therefore no longer load-bearing. ADR 0097 was careful to say it *was* —
"one of them is the guarantee, for one class" — and that is no longer true. It stays as defence in
depth, and it is now allowed to be wrong.

The 28 promulgated ledger laws re-discharge unchanged. Cost is unchanged in shape (~5 s per stamp,
now compile + replay + query), because the replay shares the compile.

## What is still open

**The statement-meaning class.** `notation "False" => True` in an ADR 0062 preamble stamps
`theorem oops : False`, and **no kernel check will ever catch it** — every layer is behaving
honestly. The kernel really did prove the statement as elaborated; the environment really is
sound; only what the statement MEANS has changed. `lean4checker` passes it, correctly.

This is a **preamble-trust decision, not a checker gap**, and it falsifies ADR 0062's standing
claim that a smuggled hole in the preamble is caught. The remedies are to confine the preamble, or
to restrict promotion to the DSL-rendered provider paths where the six `*_decided` gates already
re-render `theorem_src` and the proof from a checked contract. It remains pinned as a strict-xfail
regression so it cannot be quietly forgotten.

## The lesson worth keeping

ADR 0097 declared a limit on the basis of a sound argument about the wrong activity, and the
declaration went unchallenged for a round because it *felt* like the honest, humble call. The
check that dissolved it took two lines. **"This cannot be done" deserves the same adversarial
scrutiny as "this is secure"** — both are claims, and this repo's practice of attacking the second
should extend to the first.
