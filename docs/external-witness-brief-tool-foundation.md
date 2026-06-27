<!--
External-witness brief (round 3): the tool-using -> tool-building Leibniz foundation. Composed
2026-06-27 to stress-test the ADR 0041 direction BEFORE it hardens. Advisory only (invariant 4: no LLM
decides). Responses get adversarially synthesized and folded into docs/adr/0041-*.md before operator
sign-off. Prior rounds: external-witness-round-synthesis-2026-06-26.md (direction),
external-witness-brief-acceleration.md (GPU/Python ops).
-->

# External-witness brief — Tool-using → tool-building Leibniz under a hard soundness boundary

**Status:** composed 2026-06-27 for the 7-model witness round. **Advisory only** — input informs ADR
0041; a human approves; no model's verdict is binding (invariant 4). **Disposition:** the 7 responses
are collected by the operator, run through an adversarial synthesis (surviving guidance only), and
folded into ADR 0041 before sign-off.

**Why now:** we just closed the autonomous record-beating arc (RED across every lever; see
`docs/funsearch-pilot-result-finding.md` and `docs/autonomous-discovery-arc-capstone.md`). The operator
chose to generalize the FunSearch pattern (*untrusted tool proposes → sandbox executes → mechanical
checker decides*) into a foundation for **tool use**, with a path to **tool building**, seeded by
research ingestion (arXiv) and by Leibniz extending its own capabilities. This brief stress-tests that
direction and its trust model with external perspective before the architecture hardens.

---

## The prompt (given verbatim to each of the 7 witnesses)

> You are advising on a foundational architecture decision for **Leibniz**, an agentic theorem/discovery
> daemon. Your input is **advisory** — it will inform an architecture decision record (ADR) that a human
> approves; no model's verdict is binding. Please be rigorous and adversarial; we value dissent over
> validation.
>
> **What Leibniz is — and its one non-negotiable.** LLMs **propose**; only **mechanical checkers** (the
> Lean 4 kernel, Z3, automated table-of-record oracles) **decide**. The invariant is *"nothing false is
> ever stamped Q.E.D."* It is enforced in code: `kernel_verified` is set in exactly one function;
> promotion passes a trust policy; novelty is settled by retrieval + a decision procedure, never by an
> LLM judge; candidates are quarantined, never deleted. The trusted computing base (TCB) is small and
> explicit (the kernel, a few checkers). This boundary is the product; we will not weaken it for
> capability.
>
> **What we just measured (so you know where we are, honestly).** We ran a full autonomous
> mathematical-discovery arc — trying to beat published records for binary constant-weight codes —
> across every lever: exact solvers, heuristic search, structural (group-theoretic) construction, and
> finally a **FunSearch-style loop** (an LLM proposes *construction programs* → they run in a
> locked-down untrusted-code sandbox → an untrusted fitness check scores them → an automated oracle
> judges novelty → any candidate "beat" is re-checked by the Lean kernel). Across 100+ problem cells:
> **it matched many records, beat none.** The binding constraint is the *producer* (what it can
> encode/construct), not soundness, prover power, or compute. The daemon's honest, demonstrated identity
> today is a **sound verification instrument**, not yet an autonomous discoverer. Crucially: the
> FunSearch pipeline is *one instance* of a general pattern — **untrusted tool proposes → sandbox
> executes → mechanical checker decides** — and the trust boundary held throughout.
>
> **The proposed direction (what we want your impact on).** Generalize that pattern into a **foundation
> for tool use**, with a deliberate path toward **tool building**. Concretely, Leibniz should
> autonomously **discover, conjecture, and write**, seeded by two sources:
> 1. **Research it ingests** — e.g. an arXiv crawl that surfaces conjectures, targets, constructions,
>    and tool ideas. (We already ingested one paper soundly: rather than trust its claimed results, we
>    cross-checked them and used them only as a *conservative* bound — claims were treated as untrusted
>    hints, never decisions.)
> 2. **Extending its own core fundamentals** — Leibniz building new *capabilities/tools* for itself.
>    Near-term goal: lay the foundation for how Leibniz **utilizes** a registry of tools. Not-so-distant
>    future: Leibniz also **builds, assembles, tests, and proves** those tools.
>
> **The crux.** Autonomous tool-building is precisely how a system's TCB can silently explode and how
> "nothing false is stamped" can quietly fail (a self-built, unverified tool sneaks into a deciding
> role; a research claim is trusted; a self-improvement loop launders untrusted capability into trust).
> We want the foundation to make that *structurally impossible*, while still enabling genuine autonomy.
>
> **Please answer, structured:**
> 1. **Impact / is this the right bet?** Given the measured result (autonomous *discovery* is RED;
>    sound *verification* is GREEN), is "extend the daemon's own capabilities via tool-building" the
>    highest-value next direction — or a more capable way to keep hitting the same producer wall? What
>    would change your answer? Steelman the *strongest case against* this direction.
> 2. **The trust model you would mandate.** State the bright-line rules for: (a) a tool Leibniz *uses*,
>    (b) a tool Leibniz *builds*, (c) *research input*. Under what **exact** conditions — if any — may a
>    *built* tool ever enter a *deciding* role rather than remaining a forever-re-checked proposer? How
>    do you prevent TCB-growth-by-fiat? What belongs in code/tests/hooks vs. policy?
> 3. **Architecture.** How would you structure (a) the tool/capability protocol + registry, (b) the
>    research-seeding pipeline, (c) the build → assemble → test → prove → register lifecycle and its
>    trust gate? Reuse vs. rebuild relative to a sandboxed propose→check loop that already exists.
> 4. **Anti-patterns & failure modes.** The top specific soundness pitfalls of self-improving /
>    self-tool-building agents we must design against (reward/spec hacking, eval-on-self, capability
>    feedback loops, trusting one's own tools), each with the concrete guard you'd require.
> 5. **Sequencing.** A phased plan, each phase behind a measure-before-build gate. What is the smallest,
>    highest-value **first slice**? What should be explicitly *deferred* (and what would gate
>    un-deferring it)?
> 6. **One thing we're likely getting wrong.** Your single most important warning or contrarian point.
>
> Be concrete and cite mechanisms, not platitudes. Assume we will hold the soundness line absolutely;
> design within that, not around it.
