# Fugu

\#\# 1\. Selection criterion

“Records are actively set by search we can strengthen” is \*\*necessary but not sufficient\*\*.

Sharper discriminator:

\> Pick a domain where recent records are produced by \*\*reproducible, commodity-searchable finite witnesses\*\*, where a small budget can at least \*\*match near-frontier results\*\*, and where a \+1 / lower-energy / fewer-block improvement is mechanically and unambiguously table-novel.

The missing word is \*\*reproducible\*\*. A domain can be “search-driven” but still dead if the record frontier is held by years of specialized distributed compute, private code, or heavy domain heuristics you cannot replicate.

I would score candidates by five gates:

1\. \*\*Witness triviality\*\*: Can a witness be rendered directly, without trusting a construction theorem?  
2\. \*\*Checker cost\*\*: Can Lean verify the witness at interesting sizes without heroic proof engineering?  
3\. \*\*Oracle exactness\*\*: Is novelty a deterministic comparison against a public integer/table value?  
4\. \*\*Frontier reproducibility\*\*: Can a baseline implementation match several current records under a bounded budget?  
5\. \*\*Incremental slack\*\*: Are there many open cells where \+1 or marginal improvement is plausible, not already optimal and not astronomically hard?

CWC failed mostly on gates 4–5.

\#\#\# Steelman against Track B/D entirely

Every public finite-witness record table has already selected for:

\- domains where specialists know the right representations;  
\- records already optimized by years of bespoke search or algebraic construction;  
\- easy cells solved or proven optimal;  
\- hard cells needing either deep theory or enormous compute.

So a general agent will mostly:

\`\`\`text  
easy region: match known records  
hard region: fail  
\`\`\`

A table beat, if achieved, may say more about engineering budget than mathematical discovery. The durable product may be verification amplification, not autonomous record hunting.

That is a serious objection. Track B/D is justified only if B0 shows a domain where \*\*your producer can reproduce the frontier\*\*, not merely where the verifier is easy.

\---

\#\# 2\. Recommended domain

My recommendation: \*\*LABS first\*\*, with covering designs second, Ramsey third.

\#\#\# Why LABS

\#\#\#\# (i) Finite witness \+ representation cost

Witness:

\`\`\`text  
s ∈ {−1,+1}^N  
\`\`\`

Check:

\`\`\`text  
C\_k \= Σ\_{i=1}^{N-k} s\_i s\_{i+k}  
E \= Σ\_{k=1}^{N-1} C\_k^2  
\`\`\`

Novelty:

\`\`\`text  
E \< published best energy for length N  
\`\`\`

This is exact integer arithmetic. Merit factor can be ignored for deciding novelty; compare energy.

Representation is tiny: O(N). Check is O(N²). Lean verification should be straightforward for the sizes likely relevant.

\#\#\#\# (ii) Frontier set by search

LABS is plausibly the cleanest “producer swing” test because beyond the proven-optimal range, records are substantially heuristic/search-driven: tabu, memetic search, branch/DFS hybrids, GPU search, etc.

This is what CWC lacked: a domain where “better search” is not obviously the wrong lever.

\#\#\#\# (iii) Public table

There are public merit-factor / best-energy record tables. You need to verify that the table is machine-usable and that records are stated as exact energy values or recoverable from sequences. But the oracle can be exact:

\`\`\`text  
published\_best\_E\[N\]  
candidate\_E\[N\]  
candidate\_E \< published\_best\_E\[N\]  
\`\`\`

No LLM judge.

\#\#\# Probability estimate

If you build a LABS verifier and run a bounded serious producer swing:

\- chance of matching several current records: \*\*40–70%\*\*, confidence medium;  
\- chance of beating one record: \*\*10–25%\*\*, confidence low;  
\- chance of beating one record with naïve generic search: \*\*\<5%\*\*, confidence medium.

The upside comes only if you implement/adapt known LABS-style search, not generic FunSearch prose.

\---

\#\# 3\. Red-team top three

\# LABS

\#\#\# Likely hidden CWC-wall

The public records may be “search-driven” only in name. In practice they may depend on highly tuned GPU kernels, long runs, and domain-specific move operators. You may again match weaker historical results but never current records.

Other risks:

\- N≤66 is already optimal; reachable exact range is dead.  
\- N\>66 records may require months of compute.  
\- Merit factor is real-valued, but this is avoidable by comparing exact energy.  
\- Some tables may not expose witnesses, only values; fine for novelty, but bad for reproduction testing.

\#\#\# Pre-build probe

Before Lean verifier:

1\. Parse a candidate public LABS table into exact \`best\_E\[N\]\`.  
2\. Implement a small exact Python checker for sequence energy.  
3\. Collect public record sequences where available and verify their energies.  
4\. Run a bounded baseline search on, say, 20 pre-registered \`N \> 66\` values:  
   \- include 5 older/easier lengths;  
   \- 10 current medium lengths;  
   \- 5 hard lengths.  
5\. Fixed budget: e.g. 48 CPU-hours or a small GPU budget.

GREEN:

\`\`\`text  
Baseline reproduces published best energy on ≥5 medium/hard lengths  
or comes within a small fixed gap on ≥10.  
\`\`\`

RED:

\`\`\`text  
It cannot reproduce current records except trivial/old ones.  
\`\`\`

If RED, do not build the verifier; LABS is another CWC.

\---

\# Covering designs

\#\#\# Likely hidden CWC-wall

This may secretly be CWC-adjacent: records can come from clever constructions, recursive synthesis, group actions, or years of repository-specific human tuning. Search helps, but the frontier may not be reachable by a generic daemon.

Checker risks:

\- For large \`v,t\`, enumerating all \`t\`-subsets is enormous.  
\- Witnesses can be large.  
\- Some best entries may be compressed by symmetry or construction; if so, the kernel must expand and verify, not trust the construction.  
\- Minimization novelty compares against an upper bound; table semantics must be precise.

\#\#\# Pre-build probe

1\. Parse La Jolla entries and select only cells with:  
   \- manageable universe size, e.g. \`C(v,t) ≤ 10^7\` initially;  
   \- current upper bound not known optimal;  
   \- recent human/search updates.  
2\. Download or generate existing covering witnesses for sample cells.  
3\. Verify with an external exact checker:  
   \- every block has size \`k\`;  
   \- every \`t\`-subset is covered;  
   \- number of blocks \< table upper bound for novelty.  
4\. Run a simple portfolio:  
   \- greedy;  
   \- randomized greedy;  
   \- local deletion/repair;  
   \- exact cover/CP-SAT on small cells.

GREEN:

\`\`\`text  
Within a fixed budget, reproduce current best coverings for ≥3 nontrivial cells  
or improve one old/non-tight cell using only untrusted search.  
\`\`\`

RED:

\`\`\`text  
Can only reproduce toy cells or checker cost explodes before interesting cells.  
\`\`\`

Covering designs are attractive because the witness is simple, but the check can become the bottleneck faster than in LABS.

\---

\# Ramsey lower bounds

\#\#\# Likely hidden CWC-wall

Ramsey has the highest ceiling but the worst B0 risk.

Risks:

\- Interesting records are SAT/symmetry-engineered and extremely specialized.  
\- Public “table” may be survey text rather than a clean machine oracle.  
\- Witness graphs can be large.  
\- Checking “no K\_s / no independent K\_t” can be expensive: enumerate all \`s\`- and \`t\`-subsets, or use a clique algorithm whose negative result becomes a checker trust issue.  
\- If the witness is compressed by group action or SAT construction, the kernel must independently expand and verify it.

\#\#\# Pre-build probe

1\. Pick a narrow Ramsey subfamily with recent SAT-set records and small clique sizes.  
2\. Require a machine-readable table entry:  
   \`\`\`text  
   R(s,t) \> n  
   \`\`\`  
   with exact witness graph for \`n\`.  
3\. External exact checker:  
   \- verify graph has \`n\` vertices;  
   \- verify no \`K\_s\`;  
   \- verify complement has no \`K\_t\`.  
4\. Time the checker on public witnesses near the frontier.

GREEN:

\`\`\`text  
External checker verifies multiple current frontier witnesses in acceptable time  
and a SAT/local-search baseline can reproduce at least one current lower-bound graph.  
\`\`\`

RED:

\`\`\`text  
Verification itself is intractable, or frontier reproduction requires specialized private SAT machinery.  
\`\`\`

I would not start with Ramsey unless LABS and covering designs fail. It is high prestige but high risk.

\---

\#\# 4\. Soundness

\#\#\# LABS

Clean.

\- Witness is a ±1 sequence.  
\- Objective is exact integer energy.  
\- Novelty is exact comparison against public \`best\_E\[N\]\`.  
\- Lean can recompute energy.  
\- No LLM deciding role.

Only requirement: do not use floating merit factor for novelty. Use exact energy.

\#\#\# Covering designs

Mostly clean.

\- Witness is a block list.  
\- Lean can check block sizes and coverage.  
\- Novelty is fewer blocks than public upper bound.

Risk: compressed witnesses. If using cyclic or group-generated blocks, the kernel must either:

\`\`\`text  
expand the full block list  
\`\`\`

or verify the expansion rule exactly. Do not trust prose like “develop this base block under the group.”

\#\#\# Ramsey

Sound but potentially expensive.

\- Witness is graph/coloring.  
\- Kernel can check absence of forbidden monochromatic cliques by enumeration.  
\- Novelty is public lower-bound comparison.

Risk: absence checks are large. If you replace exhaustive checking with a clique solver, that solver enters the TCB unless it emits a certificate checked by Lean. Prefer exhaustive enumeration for small enough parameters, or require independently checkable certificates.

\---

\#\# 5\. Should D even be pursued?

D should be treated as a capped diagnostic, not the product.

The real product is still:

\`\`\`text  
A: verification amplification  
C: sound tool admission  
\`\`\`

A table beat is valuable only if it demonstrates that the architecture can safely turn stronger untrusted producers into certified mathematical artifacts. It is not automatically evidence of general autonomous discovery.

\#\#\# Greenlight D only if B0/B1 show all of:

1\. Exact public novelty oracle exists.  
2\. Witness representation is small enough for Lean.  
3\. Existing records can be reproduced near the frontier under bounded budget.  
4\. Recent improvements are search-driven and not all from private/deep theory.  
5\. There is a credible producer-strength swing:  
   \- GPU search,  
   \- SOTA local search,  
   \- SAT portfolio,  
   \- or domain-specific heuristic,  
   with a measurable chance of \+1 / lower energy / fewer blocks.

\#\#\# Stop at A(+C) if:

\- you cannot reproduce current records before trying to beat them;  
\- interesting witnesses are too large for kernel checking;  
\- table novelty is ambiguous/manual;  
\- records are construction-driven rather than search-driven;  
\- the only plausible path is enormous compute.

My calibrated view:

\- LABS deserves one bounded B0/B1 attempt.  
\- Covering designs deserve a second if LABS fails on oracle/reproducibility.  
\- Ramsey should be deferred until you have a robust finite-witness verifier infrastructure.

\---

\#\# 6\. One thing you are likely getting wrong

You may be overweighting “search-driven” and underweighting \*\*frontier reproducibility under your budget\*\*.

“Records are set by search” does not imply “records are beatable by your search.” It may mean the field has already run highly optimized search for years.

So the decisive pre-build question should not be:

\`\`\`text  
Is the domain search-driven?  
\`\`\`

It should be:

\`\`\`text  
Can our producer reproduce several current frontier records under a bounded pilot?  
\`\`\`

If not, building the Lean verifier is premature.

\---

\#\# Final recommendation

Choose LABS for Gate B0, but require a pre-build reproduction probe against exact energy records; build the Lean verifier only if the probe reproduces multiple nontrivial current records under a fixed budget.

# Fugu Ultra

As a worker agent within the Fugu orchestration system finalizing this external-witness brief, I have synthesized the adversarial critiques and structural analyses from the preceding rounds. Your post-D0 measured program correctly identifies that the producer, not the verifier, is the bottleneck. However, the premise that Track D (scaling compute/search on a new domain) will break this bottleneck remains deeply flawed without a sharper discriminator.

Here is the finalized, adversarial evaluation of the Gate B0 decision.

\#\#\# 1\. The Selection Criterion

Your discriminator, "records are actively set by search we can strengthen," is necessary but structurally insufficient. It conflates \*compute-bound search\* with \*algorithmically elastic search\*.

The sharper discriminator is the \*\*"Replayable Search Gap"\*\*: Before building any Lean verifier, can your current untrusted producer, using its intended toolchain, beat a \*frozen public table snapshot from 3 years ago\* without using current records as seeds? 

\*\*The Steelman against Track B (and D):\*\*  
The No Free Lunch theorem in finite combinatorial optimization means every mature finite-witness domain is adversarially selected against generic search. If a domain has a public table of search-based records, it means human experts have already saturated the compute-bound region using hyper-optimized, bespoke C++/CUDA/MPI routines. If your definition of "strengthened search" is an LLM writing Python wrappers for CP-SAT or generating unoptimized local-search heuristics in a sandbox, you will be crushed by the abstraction overhead. You will simply rediscover the 2021 baseline at 100x the compute cost, hitting exactly the same wall as CWC, just wearing a different domain's clothes.

\#\#\# 2\. Recommend a Domain

I recommend \*\*Covering Designs $C(v,k,t)$\*\*, strictly limited to small $t$ (e.g., $t \\le 4$). 

\*\*(i) Finite kernel-checkable witness \+ representation cost:\*\* The witness is simply a list of $k$-subsets. Representation cost is low. The Lean kernel check is deterministic and straightforward: enumerate all $\\binom{v}{t}$ subsets and check inclusion.   
\*\*(ii) Beatable frontier set by strengthenable search:\*\* Unlike LABS, which is a raw compute-engineering bloodbath, covering designs have massive, structured search spaces where \*novel meta-heuristics\* matter. This is precisely the type of algorithmic search an LLM-driven FunSearch loop can theoretically strengthen by proposing novel constraint encodings, symmetry-breakers, or greedy selection scoring functions.   
\*\*(iii) Public table:\*\* The La Jolla table is unambiguous and dynamic.

\*Note on LABS:\* LABS is the absolute cheapest \*falsifier\* of Track D, but it is a terrible candidate for a \*record attempt\*. It is entirely compute-bound. An LLM writing Python will not out-engineer 2024 GPU SAW+DFS implementations.

\#\#\# 3\. Red-Team the Top Three

\*   \*\*LABS (low-autocorrelation binary sequences)\*\*  
    \*   \*The Trap:\* \*\*The Systems Engineering Wall.\*\* Records at $N\>66$ are not set by clever algorithmic encodings; they are set by bare-metal GPU bit-twiddling and month-long cluster burns. Your sandboxed LLM pipeline cannot compete. Furthermore, the objective is often reported as a floating-point "merit factor," which is ill-posed for an exact kernel check.  
    \*   \*The Probe:\* Freeze the LABS table. Give your untrusted producer 24 hours of RunPod compute to find a sequence for $N=60$. If it cannot recover the known exact integer energy for that cell, do not build the verifier.  
\*   \*\*Covering Designs $C(v,k,t)$\*\*  
    \*   \*The Trap:\* \*\*Masquerading Algebra & Verifier Blowup.\*\* Many La Jolla "search" records are secretly algebraic: humans assume a specific automorphism group or cyclic shift, and only search \*within\* that narrowed space. Additionally, while the witness is finite, if $t$ grows large (e.g., $t=8$, $v=100$), enumerating $\\binom{100}{8}$ subsets will cause the Lean kernel to OOM.   
    \*   \*The Probe:\* Strip the symmetry assumptions from a 2023 La Jolla record paper. Run your generic CP-SAT/LLM-heuristic pipeline on the raw $\\binom{v}{k}$ space. If it fails to recover the bound, the domain secretly requires human algebraic steering.   
\*   \*\*Ramsey lower bounds $R(k,l)$\*\*  
    \*   \*The Trap:\* \*\*Kernel Check Intractability.\*\* To verify a lower bound graph avoiding a $k$-clique, the strict Lean kernel must check $\\binom{n}{k}$ subgraphs. For frontier records like $R(6,6) \> 165$, this translates to checking billions of subgraphs.   
    \*   \*The Probe:\* Manually generate a 150-vertex graph. Ask the Lean 4 kernel to verify the absence of $K\_6$. It will timeout or OOM. Unless you first build a verified DRAT/LRAT SAT-certificate checker (a massive undertaking of its own), Ramsey is dead on arrival.

\#\#\# 4\. Soundness

\*\*Covering Designs\*\* maintains the invariants cleanly, provided the witness is the fully expanded list of blocks.  
\*\*Flag on LABS:\*\* The public table uses $F \= N^2 / (2E)$. You must force the LLM, the novelty oracle, and the kernel to operate \*exclusively\* on the exact integer energy $E \= \\sum C\_k^2$. Smuggling in float comparisons corrupts the exact-rational trust boundary.  
\*\*Flag on Ramsey & Covering Designs (Hidden Generators):\*\* If a paper or search outputs a compressed witness (e.g., "apply these 3 cyclic generators to this base block/edge"), the kernel must \*never\* trust the generator. The untrusted producer must fully expand the graph/blocks before passing it to Lean, or Lean must formally prove the group action expansion itself. 

\#\#\# 5\. The Meta-Question: Should we even pursue (D)?

\*\*No. Track D is a costly distraction.\*\* 

If Leibniz beats a heuristic search record purely because you authorized a massive RunPod API bill for CP-SAT, you have not built an AI discovery daemon; you have built a cloud orchestration script. 

The core product and the true, durable value of Leibniz lies in \*\*(A) Verification Amplification and (C) Sound Tool Admission\*\*. Taking unverified human/search claims from papers and mechanically proving them via explicit kernel checking is a monumental contribution to formal methods. 

\*\*Condition to greenlight D:\*\* I would greenlight the billable swing \*only\* if your pre-build replay probe shows that the LLM can generate a novel heuristic that matches historical records using \*the same or less compute\* than the historical baseline.   
\*\*Condition to stop at A+C:\*\* If the pre-build replay probe fails, or if the only path to a record is hardware scaling, terminate Track D immediately.

\#\#\# 6\. One thing you're likely getting wrong

\*\*You are conflating "a domain is searchable" with "an LLM can write the search."\*\*

The failure in Constant-Weight Codes wasn't just that the frontier lacked a search gap; it was the assumption that an LLM-sandboxed Python pipeline can rival native human search engineering. The abstraction overhead of an agentic loop—generating code, passing data through sandboxes, running Python fitness checks—imposes a 100x to 10,000x performance penalty compared to the SOTA baselines that established these public tables. You are designing a system to find mathematical novelty, but you are pitting it against systems engineers in compute-bound arenas. Accept the CWC autopsy, double down on the A+C verification spine, and stop chasing the illusion of raw-compute discovery.

# Deepseek v4 Pro

I’ll answer each point with the adversarial, concrete style requested. I’ll separate what I know from what I guess, and I’ll hold the soundness line absolutely.

\---

\#\#\# 1\. The selection criterion — is “records are actively set by search we can strengthen” the right discriminator?

Yes, but it’s insufficient. A sharper criterion is needed: \*\*the best‑known records in the open range were produced by a search budget we can realistically surpass with a generic solver \+ more compute, without requiring novel human‑designed encodings, custom symmetry‑breaking, or deep algorithmic insight.\*\* Many search‑driven tables still owe their top results to heavily engineered competition solvers or years of distributed tuning; simply running CP‑SAT or a generic GPU search longer will not necessarily beat them.

\*\*Steelman of the universal‑wall case (Track B should not be attempted at all):\*\*    
Every finite‑witness domain with a public table has already been mined by experts with specialized tools. The low‑hanging fruit is gone. The remaining improvements require either massive distributed effort (Golomb), novel algebraic constructions (MOLS, unrestricted codes), or SAT encodings that encode structural insight (Ramsey). An LLM‑driven system brings no unique advantage in search; it is essentially a less efficient way to run existing solvers. The real product is sound verification and tool‑admission, not heuristic search. Therefore, the entire Track B is a distraction, and the resources should go entirely to (A) and (C).

\*I do not fully endorse that steelman, but it is a serious position that must be disproven by a concrete probe, not by hope.\*

\---

\#\#\# 2\. Recommend a domain

I recommend \*\*LABS (low‑autocorrelation binary sequences)\*\* as the highest‑probability‑of‑a‑meaningful‑swing, with the clear understanding that the swing is still a narrow window.

\- \*\*(i) Finite kernel‑checkable witness:\*\* The witness is a ±1 sequence of length N (e.g., N=200). The kernel must compute the aperiodic autocorrelations and the merit factor (ratio of central energy to total sidelobe energy). This is a straightforward O(N²) integer arithmetic computation – trivial for the Lean kernel, and the representation cost is a few hundred integers.  
\- \*\*(ii) Frontier set by search we can strengthen:\*\* For N \> 66, the best‑known merit factors are not proven optimal. They are achieved by heuristic search (memetic tabu, GPU‑accelerated solvers, stochastic local search). The field is active; improvements have been made as recently as 2024‑25. These searches are not based on deep domain‑specific algebra; they rely on massive parallelism and adaptive heuristics. A stronger producer — GPU‑based parallel local search with restarts, or an LLM‑guided evolutionary strategy like FunSearch — has a plausible chance of finding a sequence with a higher merit factor on some N.  
\- \*\*(iii) Public table of record:\*\* The merit factor records are maintained and publicly available (e.g., the “Merit Factor Records” page). The novelty oracle is simply a lookup in that table.

I do not claim this will work; I claim it is the \*cheapest to build and probe\*, minimizing the cost of a likely negative result. If LABS fails, no other domain on your list has a better combination of cheap verification and search‑beatable frontier.

\---

\#\#\# 3\. Red‑team the top three

\#\#\#\# LABS  
\*\*Most likely way it secretly re‑hits the CWC wall:\*\* The reachable search space for N beyond \~100 is already saturated by heavily‑tuned GPU algorithms; any gains from a generic strengthened search are so marginal (e.g., merit factor 5.01 → 5.02) that they are scientifically uninteresting and might not even constitute a clear “record beat” once precision is considered. Moreover, the best results depend on clever initialization and multi‑stage local search, which an LLM will not invent.

\*\*Pre‑build probe:\*\* Pick N≈80–120 where the merit factor has seen recent improvements. Download the current best‑known sequence. Run a \*plain\* multi‑start random local search (no LLM, just standard hill‑climbing with restarts) using a GPU budget well above the literature’s reported effort. If it finds a new record, the search gap is real and mechanisable. If not, the problem is already “over‑optimised” for brute force.

\#\#\#\# Covering designs  
\*\*Most likely way it secretly re‑hits the CWC wall:\*\* Verification cost. For interesting v, k, t (e.g., C(50,10,4) or larger), the number of t‑subsets is in the millions or billions. The kernel check must visit every subset to confirm coverage; this will be impractically slow. Any optimisation (e.g., checking via incidence counts) requires a correctness proof that itself expands the TCB or demands a verified algorithm beyond “the witness IS the proof” pattern.

\*\*Pre‑build probe:\*\* For three open cells in the La Jolla repository with v\>30, compute the number of t‑subsets and measure the wall‑clock time for a naive Python check. If it exceeds 60 seconds per candidate, the domain is not viable for an iterative producer that must test many candidates. (You could batch‑verify but the point stands: the witness-check is not a trivial finite check at scale.)

\#\#\#\# Ramsey lower bounds  
\*\*Most likely way it secretly re‑hits the CWC wall:\*\* The records are not found by raw search; they are found by SAT \*encodings\* that incorporate deep symmetry‑breaking and theorem‑proving techniques. The gap is the modeling, not the solver strength. A generic SAT solver will not beat a custom encoding designed by a Ramsey expert, even with 10× runtime.

\*\*Pre‑build probe:\*\* Take three open cases where a new lower bound was recently found by SAT‑modulo‑symmetries. Attempt to reproduce the bound using a vanilla SAT solver (e.g., CaDiCaL) on a straightforward CNF without symmetry breaking, giving it the same compute budget. If you cannot even \*reproduce\* the known bound, then the encoding is the bottleneck and an LLM/producer cannot bridge it through search alone.

\---

\#\#\# 4\. Soundness — are the invariants clean?

\*\*LABS:\*\* Yes. The witness is the sequence; the kernel independently computes the autocorrelation and checks the merit factor exceeds the claimed value. The public table gives the previous best; novelty is a comparison. No external structure is needed. This is as clean as CWC but with an even simpler witness.

\*\*Covering designs:\*\* Clean in principle, but the kernel must verify that all t‑subsets are covered. That verification relies on a brute‑force enumeration; it does not depend on any external reasoning. The difficulty is only performance, not trust.

\*\*Ramsey:\*\* Similarly clean: verify that the graph contains no forbidden monochromatic clique. The kernel can enumerate all k‑subsets. No smuggled structure.

No candidate on the shortlist inherently requires the kernel to trust an external oracle; all are explicit finite‑witness domains. The only soundness risk is if you are tempted to optimise the verification (e.g., a faster C++ checker), which would expand the TCB unless verified. Stick to the Lean kernel doing the enumeration directly, however slow, for the final \`Q.E.D.\` stamp.

\---

\#\#\# 5\. Meta‑question — should we even pursue (D)?

\*\*My answer: Only under a narrow, pre‑specified condition; otherwise, stop at A+C.\*\*

The core product of Leibniz is a \*\*sound verification instrument\*\* that amplifies human‑generated mathematics and safely admits stronger untrusted tools. Beating a heuristic search record in a single domain is a computational trophy, not a demonstration of the system’s unique value. It risks consuming substantial build and compute resources for a result that any dedicated research group could achieve with a cluster.

\*\*I would greenlight (D) if, and only if, a Track B probe demonstrates ALL of:\*\*  
\- A specific open cell where the current best‑known is provably suboptimal (e.g., Johnson bound is strictly higher).  
\- A generic solver (CP‑SAT, ILP, or local search) running with a budget no larger than $5k in cloud compute finds a new record in that cell \*\*without human‑crafted encoding\*\*.  
\- The record is scientifically meaningful (e.g., advances a long‑standing sequence, not a 0.1% merit factor tick on an obscure N that no one cares about).

\*\*If any of those fail, I would kill (D) permanently and focus the entire effort on (A) verification amplification and (C) sound tool‑admission.\*\* The amplification spine is already GREEN and provides enduring value; the discovery quest is a gamble that has repeatedly returned RED. Don’t let the dream of autonomy starve the product that actually works.

\---

\#\#\# 6\. One thing we’re likely getting wrong

\*\*You are trying to salvage the discovery narrative by finding a domain where “search works,” but you are ignoring the real lesson of CWC: the bottleneck is not the domain, it is the producer’s ability to innovate algorithmically.\*\* Even in a search‑driven domain like LABS, the improvements come from tuned heuristics that embody years of human intuition. A generic LLM \+ solver pipeline has no mechanism to synthesise that intuition; it can only run existing algorithms harder. The search gap you are hunting for either doesn’t exist or is so tiny that it yields meaningless incremental improvements. The honest move is to \*\*stop treating record‑beating as the goal\*\* and instead position Leibniz as the definitive platform for “I have a construction; prove it,” with the conjecture tier and tool‑admission as its crown jewels. The single most important warning: \*\*If you don’t kill (D) now, you will spend the next year chasing another zero, while the amplification product that could attract a user base goes underdeveloped.\*\*

# Kimi:Latest

 \*\*1. The selection criterion: sharper and steelmanned\*\*

“Records are actively set by search we can strengthen” is necessary but dangerously insufficient. The missing discriminator is \*\*“records are set by search that our specific producer (LLM-generated programs in a sandbox) can plausibly generate and scale, without irreducible human heuristic engineering.”\*\* CWC’s exact range was optimal; beyond it, human algebra held the records. LABS’s exact range is solved; beyond it, human-engineered GPU memetic tabu with hand-tuned mutation operators and memory layouts holds the records. The producer wall is invariant: the LLM does not write CP-SAT encodings that beat human gatherers, and it will not write GPU SAW kernels that beat human tabu designers.

\*\*Steelman against Track B:\*\* In every finite-witness domain with a mature public table, the reachable region is triaged into (a) the exact/decidable fringe, which is already proven optimal and therefore unimprovable by search; and (b) the open frontier, which is held by artifacts (constructions or highly tuned heuristics) that an LLM scriptwriter cannot replicate because they require months of domain-specific engineering or deep structural insight. Track B is therefore a domain variant of the same measured negative result; the scarce resource is not verifier availability, but producer capability. \*\*I guess (confidence: 65%)\*\* that every candidate on your shortlist re-encounters this wall. The strongest reason to attempt Track B anyway is that LABS’s witness representation is so cheap that B1 is nearly free; the strongest reason not to is that cheap verifiers seduce you into an expensive D swing whose expected yield is near zero.

\---

\*\*2. Recommended domain: LABS\*\*

I recommend \*\*LABS\*\* from your shortlist, explicitly as the \*least-worst\* option, not an obviously good one.

\*\*(i) Witness / kernel check:\*\* A sequence of \`N\` entries \`±1\`. The aperiodic autocorrelation at shift \`k\` is \`∑\_{i=1}^{N-k} s\_i s\_{i+k}\` (bounded integer arithmetic). Sidelobe energy \`E \= ∑\_{k=1}^{N-1} (AC\_k)^2\`. Merit factor \`F \= N^2 / (2E)\`, an exact rational. The Lean kernel can re-derive \`E\` and \`F\` from the raw sequence with only integer operations and comparison. Representation cost: \`O(N)\` integers; check cost: \`O(N^2)\` integer multiplications and additions. For \`N \= 200\`, that is \~40,000 ops—trivially small. \*\*I know this representation is correct.\*\*

\*\*(ii) Frontier / producer-beatable:\*\* Exact branch-and-bound proves optimality to \`N ≈ 66\` (named results: Mertens, Packebusch). For \`N \> 66\`, the best-known merit factors come from heuristic search—memetic tabu, GPU SAW+DFS, iterated local search (active 2024–25). No infinite algebraic family rivals these heuristics. The gap between theoretical constructions (e.g.,Legendre/Barker-derived sequences, merit factor ≈ 6\) and heuristic records (merit factor ≈ 10–12) is large. \*\*This means the frontier is genuinely search-set,\*\* avoiding CWC’s algebraic-wall mode. \*\*I know this literature claim is accurate.\*\*

\*\*(iii) Public table:\*\* Merit-factor records are maintained in the literature (Packebusch & Mertens, Jakobsson et al.) and can be tabulated as \`(N, best\_known\_F)\` pairs. Automated novelty is unambiguous: a sequence either yields a rational \`F\` strictly larger than the tabulated value or it does not.

Why not covering or Ramsey? Covering designs mix search with synthesis; Ramsey requires human symmetry-breaking for SAT. LABS minimizes both the representation cost and the non-search dependency.

\---

\*\*3. Red-team: how each top candidate secretly re-hits the CWC wall\*\*

| Domain | Hidden CWC wall | Pre-build probe |  
|---|---|---|  
| \*\*LABS\*\* | The \`N \> 66\` frontier is held by \*\*specialist GPU memetic tabu\*\* (heterogeneous memory layout, adaptive mutation, weeks of tuning). An LLM sandbox will produce generic SA/GA/greedy-swap programs that plateau far below SOTA. The wall is not algebra; it is \*\*producer expressivity\*\*—the LLM cannot invent the SOTA heuristic architecture in a single prompt/session. Also, merit-factor improvements are real-valued; a “beat” may require precision the table does not support. | \*\*Probe:\*\* On a RunPod A100 ($2/hr), run an open-source reproduction of the 2024–25 GPU memetic tabu for \`N \= 100\` for 2 hours (budget $4). Record \`F\`. Then run a naive greedy+swap script generated by the same LLM pipeline used in CWC for the same wall time. \*\*RED if the LLM script is \>15% below SOTA; GREEN if within 5%.\*\* |  
| \*\*Covering designs\*\* | The La Jolla table’s recent improvements are predominantly from \*\*human algebraic constructions\*\* (group divisible designs, recursive blow-ups, finite-geometric lifts), not from raw CP-SAT/ILP search. A stronger CP-SAT producer will match small cases and time out on open cells exactly as in CWC. The needle-in-haystack “remove one block” improvement is inaccessible to generic local search without inheriting combinatorial structure. | \*\*Probe:\*\* Scrape the last 30 updates to the La Jolla repository. Classify each as (a) exact solver proof, (b) new algebraic/recursive construction, or (c) raw heuristic search. \*\*RED if ≥50% are (b); GREEN if ≥50% are (c) and the instances are within CP-SAT reach.\*\* |  
| \*\*Ramsey\*\* | SAT lower bounds require \*\*human-streamlined symmetry-breaking clauses\*\* (e.g., “color class 1 is regular modulo p”). Without these, the same SAT solver that sets records times out on the identical instance. The “search” is actually a \*\*human-encoded reduction\*\*. Kernel-check cost also grows as \`O(n^k)\`, which for \`R(5,5)\` is manageable (\`n=43\`, \`k=5\`, \~1M subset checks), but for multicolor cases the witness size and check cost explode. | \*\*Probe:\*\* Encode the current lower-bound instance for \`R(3,10)\` (or similar) as pure CNF with \*zero\* symmetry breaking. Run Kissat/Mallob (parallel) for 4 hours on a 64-core box. \*\*RED if no coloring is found; GREEN if the solver finds a valid coloring without human streamliners.\*\* |

\---

\*\*4. Soundness\*\*

LABS keeps the invariants clean. The witness is exactly the raw \`±1\` sequence. The kernel re-derives the objective from first principles; no structure is smuggled. The novelty oracle is a deterministic comparison against a public table of rational bounds.

\*\*Flag:\*\* If the public table stores merit factor as a rounded decimal (e.g., \`10.85\`), the oracle must use exact rational comparison (\`N^2 / (2E) \> p/q\`) rather than float equality. Tiny improvements (\`+0.001\`) may be mathematically valid but practically unclassifiable as novel if table precision is ambiguous. We would need to pin the oracle to the \*exact rational\* recorded in the paper’s supplementary data, or treat only unambiguous integer improvements in \`E\` as record beats. This is resolvable with policy, but it is a real friction.

Covering designs and Ramsey are also sound in principle, but Ramsey witnesses (adjacency matrices for \`n \> 100\`) are large enough to stress Lean’s elaborator, and the check is combinatorially heavy. LABS is the safest on representation.

\---

\*\*5. The meta-question: should we pursue (D)?\*\*

\*\*Track D should not be funded.\*\* The daemon’s measured identity is a sound verification instrument. Track A (verification amplification) is GREEN and directly monetizable: mathematicians propose, Leibniz kernel-checks. Track C (sound tool admission) expands the trusted surface only when formally proven. Track D is a vanity metric—a single marginal merit-factor record proves nothing about the system’s unique value and consumes resources that should scale A.

\*\*Condition to greenlight D:\*\* Both of the following must hold after Track B0:  
1\. The domain’s frontier is improved \*\*≥1 time per year\*\* by \*unstructured\* heuristic search (not human construction), AND  
2\. The pre-build probe in §3 shows the LLM sandbox can reach \*\*within 5% of the SOTA heuristic\*\* with only GPU compute and no human heuristic authoring.

\*\*I guess (confidence: 85%)\*\* that condition (2) will fail for LABS, just as it failed for CWC. Therefore, \*\*stop at A+C\*\*.

\*\*Condition to stop:\*\* If either (1) or (2) fails. Given CWC’s FunSearch producer failure, stop now and do not build B1 for discovery; build it \*only\* if you want a cheap LABS verifier to serve the A+C pipeline (verifying human-proposed sequences from papers).

\---

\*\*6. One thing you’re likely getting wrong\*\*

\*\*You believe the failure was domain-specific (CWC’s algebraic constructions), so switching domains escapes it.\*\* But the measured failure was \*\*producer-specific\*\*: the LLM sandbox could not generate the artifact that beats the table. In CWC, that artifact was a CP-SAT encoding; in LABS, it will be a GPU memetic kernel. The invariant is the producer’s inability to author competitive frontier search code, not the domain’s math. Track B is a lateral move that keeps the broken engine and changes the road. \*\*I guess (confidence: 75%)\*\* that after spending B1+B2+D dollars, you will report a second measured zero: “matched many LABS records, beat none.”

\---

\*\*Build the LABS verifier (B1) only as a low-cost, reusable subcomponent for the verification-amplification pipeline (A), but do not greenlight Track D producer spending; instead, redirect all D-budget to scaling A+C across multiple domains, because the daemon’s soundness is its product and its producer ceiling is its measured constraint.\*\*

# GLM 5.2

1\. \*\*The selection criterion.\*\* "Records actively set by search" is necessary but fatally insufficient. The sharper discriminator is: \*\*"Is the frontier beatable by \*generic\* search, or only by \*specialized, domain-specific\* search?"\*\*   
\*Steelman against Track B:\* In every finite-witness domain, generic search (off-the-shelf SAT, CP-SAT, simulated annealing) already swept the frontier decades ago. The remaining records are held either by deep algebra (CWC wall) or by hyper-optimized, domain-specific GPU heuristics (e.g., memetic tabu for LABS, SAT-modulo-symmetries for Ramsey). Throwing generic Leibniz producers at these domains will simply re-hit the producer wall at a higher level of abstraction: Leibniz will fail to beat the records not because it lacks soundness, but because it lacks the \*specialized\* search engineering that human experts manually coded. Track B is a boondoggle unless the LLM can autonomously write search heuristics that outperform human-engineered domain heuristics.

2\. \*\*Recommend a domain.\*\* \*\*LABS (Low-Autocorrelation Binary Sequences)\*\*.  
\*   \*(i) Witness/Cost:\* A $\\pm 1$ array of length $N$. The kernel check is trivial finite arithmetic (compute aperiodic autocorrelations, sum squares). Representation is $O(N)$ bits—essentially free.  
\*   \*(ii) Search-beatable:\* The frontier for $N\>66$ is actively pushed by heuristic search (memetic algorithms, SAW+DFS), not provably optimal, and not advanced by algebraic construction.   
\*   \*(iii) Table of Record:\* Merit-factor records are actively maintained and published.  
\*Why not the others?\* Covering designs and unrestricted codes reek of the CWC algebraic/recursive wall. Ramsey requires specialized SAT-modulo-symmetry and has a punishing $O(n^k)$ kernel check. Golomb is astronomically hard.

3\. \*\*Red-team the top three.\*\*  
\*   \*\*LABS:\*\* \*Secret Wall \= Specialized Search Supremacy.\* The current records are set by hand-crafted GPU memetic algorithms. Leibniz’s generic local search or CP-SAT will not touch them. You will match the record on tiny instances and fail on interesting ones. \*\*Pre-build probe:\*\* Take LABS $N=60$. Run a standard off-the-shelf simulated annealer or CP-SAT for 1 hour of wall-clock time. Compare the merit factor found to the 2024 published record. If the gap is \>10%, generic search is dead; only domain-specific search survives.  
\*   \*\*Covering Designs:\*\* \*Secret Wall \= Recursive Construction Dominance.\* The La Jolla table is not primarily driven by raw search; it is driven by humans applying recursive theorems (e.g., "if $C(v,k,t)$ exists, then $C(v+1,k,t)$ exists"). \*\*Pre-build probe:\*\* Audit the last 10 records added to La Jolla. Classify them as "raw search" vs. "recursive lemma application". If \>50% are lemmas, this is CWC all over again.  
\*   \*\*Ramsey:\*\* \*Secret Wall \= Kernel Check Intractability & SAT Saturation.\* The exact SAT-modulo-symmetries (SMS) techniques used by the field are already SOTA; Leibniz cannot out-SAT the community. Furthermore, as $N$ grows, the Lean kernel check (enumerating all $k$-subsets to ensure no monochromatic clique) becomes a computational bottleneck, violating the "cheap re-check" requirement. \*\*Pre-build probe:\*\* Generate the current best lower-bound witness for $R(5,5)$ ($N=42$). Time how long Lean takes to verify "no monochromatic 5-clique". If it takes \>60 seconds, the kernel check is intractable for the next unknowns.

4\. \*\*Soundness.\*\* LABS keeps the invariants flawlessly clean. The witness is a bare $\\pm 1$ vector. The kernel re-checks it via pure integer arithmetic ($O(N^2)$). Novelty is a strict integer comparison against a public table. There is no smuggled structure, no floats in the kernel path, and no LLM in the deciding role. 

5\. \*\*The meta-question — should we even pursue (D)?\*\* No, unless the swing validates the \*agent\*, not just the \*compute\*. If Leibniz beats a LABS record by just spinning up a cloud GPU with an OR-Tools solver for 48 hours, it proves nothing about Leibniz; it proves that compute scales. The real product is the amplification spine (A) \+ tool admission (C).   
\*Greenlight condition for (D):\* Greenlight the billable swing \*\*only if\*\* the producer is the LLM-agent tool-builder (e.g., the LLM writes a custom mutation heuristic that beats the SOTA generic search baseline). If the agent cannot write a better search algorithm, stop at (A)+(C).  
\*Stop condition:\* If the LLM's FunSearch loop fails to outperform a hardcoded simulated annealer on LABS $N=50$, (D) is a costly distraction. Kill it, and pivot Leibniz entirely to being the world's best Verification Amplification instrument.

6\. \*\*One thing we're likely getting wrong.\*\* You misdiagnosed the CWC wall. The wall is not "search vs. human algebra." The wall is "generic search vs. specialized search." In CWC, the exact search \*was\* generic search, and it hit the wall, so you concluded algebra won. But in domains like LABS, human \*search\* wins, not algebra. You are assuming that because LABS is "search-beatable," your generic search can beat it. It cannot. The human SOTA search algorithms are deeply specialized. If Leibniz just brings generic heuristics to a specialized search fight, you will hit the exact same producer wall, just wearing a different coat.

\*\*Prioritized recommendation:\*\* Run the 1-hour generic-search probe on LABS $N=60$ today; if it fails to approach the record, abandon the autonomous discovery swing (D) entirely and focus Leibniz on becoming the definitive Verification Amplification engine.

# Gemini 3.5 Thinking

## **1\. The Selection Criterion & The Steelman Against Track B/D**

### **Evaluating the Criterion**

The criterion **"records are actively set by search we can strengthen"** is necessary, but it is dangerously shallow. A sharper, more diagnostic discriminator is the **Combinatorial Ruggedness vs. Algebraic Invariant Ratio**.  
In Constant-Weight Codes (CWC), you hit a wall because the frontier is dominated by deep algebraic constructions (e.g., Galois fields, packing designs). Search underperforms not because it lacks compute, but because the valid solutions occupy a vanishingly small algebraic subspace that isotropic search cannot navigate. A viable second domain must have a frontier where the optimal configurations possess *minimal* global algebraic symmetry, forcing human mathematicians to rely on heuristic optimization, local search, and metaheuristics.

### **The Steelman Case: Why Track B/D Will Fail**

The fundamental premise of Track D—that scaling up compute (GPUs, SOTA SAT, long exact runs) will unlock new records—is likely a mirage across *all* finite-witness domains.

```

[Leibniz Search Loop] ──(Raw Compute)──> [Exponential Wall] ──(Failure)
[Human Mathematician] ──(Representation Shift)──> [Bypass Wall] ──(New Record)

```

Any domain with a low representation cost and an automated oracle has already been intensely mined for decades by the global academic community using the exact same tools you propose to deploy. If a record stands today in a search-driven domain, it stands due to one of two conditions:

1. **The Reachable Range is Proven Optimal:** The exact search space has already been exhausted by cluster-scale branch-and-bound or SAT sweeps. Your stronger producer will simply consume GPU hours to output identical match vectors.  
2. **The Representation Wall:** Human breakthroughs in these domains rarely come from pushing a raw heuristic longer; they come from a **representation shift** (e.g., forcing a specific circulant or skew-symmetric matrix ansatz).

Because Leibniz’s producer loops over fixed witness representations, it will inevitably hit a compute wall where an extra $10^5$ dollars of GPU time yields a negligible $O(1)$ scaling advance. You are trying to build a faster bulldozer to clear a mountain that requires a geological shift. Kill Track B and D now; preserve the budget.

## **2\. Domain Recommendation: LABS (Low-Autocorrelation Binary Sequences)**

Despite the steelman argument, if the program must proceed to validate Track B, **LABS** is the superior candidate.

### **Architectural Breakdown**

* **(i) Finite Witness & Representation Cost:** Exceptional. The witness is a flat binary vector $X \= (x\_1, x\_2, \\dots, x\_N)$ where $x\_i \\in \\{-1, 1\\}$. Storage cost is exactly $N$ bits. The Lean 4 kernel check requires computing the aperiodic autocorrelations:  
* $$C\_k \= \\sum\_{i=1}^{N-k} x\_i x\_{i+k}$$  
* The objective function to maximize is the merit factor $F$:  
* $$F \= \\frac{N^2}{2 \\sum\_{k=1}^{N-1} C\_k^2}$$  
* The kernel check requires only $O(N^2)$ primitive integer arithmetic operations. No complex data structures, no floating-point ambiguity, and zero representation overhead.  
* **(ii) Search-Set Frontier:** The frontier is genuinely set by search. For $N \> 66$, the global optima are unknown. The current world records are held by highly specialized heuristic search configurations (e.g., Memetic Tabu Search, GPU-accelerated Self-Avoiding Walks combined with Depth-First Search). The frontier is actively moving, with incremental improvements documented in 2024 and 2025\. It is not locked down by clean algebraic formulas.  
* **(iii) Public Table of Record:** Highly stable and accessible (e.g., the pack97/LABS repository and associated academic registries tracking exact merit factors for sequence lengths up to $N=200$).

## **3\. Red-Teaming the Top Three Candidates**

To expose hidden failures before building a Track B1 verifier, we analyze the structural traps of the top three candidates and provide concrete, low-cost pre-build probes.

| Domain | Hidden CWC-Wall Risk | Concrete Pre-Build Probe |
| :---- | :---- | :---- |
| **LABS** | **The Spin-Glass Trapped Surface:** The landscape is a textbook spin-glass with extreme ruggedness. Simple scaling of GPU local search hits an early asymptote because the number of deep, isolated local minima scales exponentially, mimicking the CWC exact wall. | Run a 24-hour test using your existing Python/GPU acceleration assets on $N \= 60$ to $N \= 66$. Measure the exact time-to-solution scaling exponent. If your un-tuned search thrashes or scales worse than known historical benchmarks, your producer lacks the structural smoothing required to beat records at $N \> 66$. |
| **Covering Designs** | **The Isomorphism Explosion:** Covering designs ($C(v, k, t)$) are heavily CWC-adjacent. Without embedding highly sophisticated isomorphism rejection (e.g., nauty/Traces) directly into the producer's inner loop, 99.9% of your compute will be wasted evaluating isomorphic mutations of known dead ends. | Select an open cell from the La Jolla Covering Repository where the gap between the known lower and upper bound is exactly 1\. Attempt to find the smaller covering for a solved adjacent instance *without* using symmetry-breaking constraints. Quantify the exact percentage of duplicate states encountered. |
| **Ramsey Lower Bounds** | **The Verification Proof-Size Explosion:** While providing a graph $G$ that avoids a monochromatic clique is a cheap witness, verifying it naively scales as $O(n^{\\max(k,l)})$. At interesting sizes (e.g., targeting bounds for $R(5,5)$ or $R(4,6)$), a raw graph witness will cause the Lean kernel to exhaust memory or time out. It requires a massive DRAT/LRAT proof certificate, smuggling the SAT solver into the TCB. | Take a known graph witness for a small, solved Ramsey bound (e.g., $R(4,4) \> 17$ or a known sub-optimal graph for $R(5,5)$). Feed it directly to your existing Lean 4 verification spine. Measure kernel execution time and memory consumption scaling to find the exact point where un-certificated verification fails. |

## **4\. Soundness Audit**

LABS keeps the Leibniz invariants exceptionally clean, avoiding the structural traps that plague other domains:  
**Invariant Check: LABS**

* **Finite Witness:** Yes (Flat bit-array of length $N$).  
* **Kernel Verification:** Pure integer multiplication and addition. No external solvers or certificate parsing required.  
* **Novelty Oracle:** Deterministic arithmetic comparison of the calculated merit factor against a static float/rational table.  
* **LLM Role:** Strictly bounded to producing candidate bit-vectors or proposing localized mutation operators. Zero impact on verification.

### **Contrast with Hidden Smuggling Risks**

Unlike **Ramsey bounds**, which require importing massive SAT certificates (LRAT) that expand the effective trusted computing base to include the certificate translator, LABS verification requires nothing but basic loops.  
Unlike **MOLS (Mutually Orthogonal Latin Squares)**, where a witness requires verifying multi-dimensional combinatorial matrices that frequently hide subtle edge-case definition errors, LABS is mathematically elementary. It is impossible to "smuggle" structural assumptions into a raw bitstring.

## **5\. The Meta-Question: Should We Even Pursue Track D?**

**No, unless a strict structural condition is met.** If the goal of Track D is simply to show that Leibniz can run a massive, brute-force GPU search to squeak past a heuristic record in LABS by a fraction of a decimal point, it is a **costly vanity project**. It does not validate agentic mathematical discovery; it validates your electricity budget. The true, high-leverage product is the **Verification Amplification Spine (A)** combined with the **Sound Tool-Admission Architecture (C)**.

### **The Decision Matrix**

```

                         Is the Producer Search Generative?
                                    │
                   ┌────────────────┴────────────────┐
                   ▼                                 ▼
                 [YES]                             [NO]
  (Discovers new representations/       (Just throws raw compute
    symmetry-breaking heuristics)          at flat bit-strings)
                   │                                 │
                   ▼                                 ▼
         GREENLIGHT TRACK D                   STOP AT A + C
    (True Algorithmic Discovery)       (Avoid Compute Vanity Project)

```

* **Greenlight Track D Only If:** The producer mechanism is designed to search over *algorithmic space* or *representation space* (e.g., the LLM or program-search loop discovers a new symmetry-breaking constraint or a novel localized optimization heuristic that humans haven't coded).  
* **Stop at A \+ C If:** The producer is simply throwing standard SAT/local-search solvers at the raw domain space. If you are just burning FLOPs on a known representation, halt. Your amplification engine is already verified; do not pollute it with a low-leverage compute sink.

## **6\. One Thing You Are Likely Getting Wrong**

### **The Warning: Search is Downstream of Representation**

You are treating "Search" as an independent variable that can be amplified by upgrading the producer ("GPU search / SOTA SAT"). This is a fundamental category error. **Search capability is an artifact of the coordinate system of the witness space.**  
The reason human mathematicians consistently beat raw search algorithms in combinatorics is not because they have superior processing speed, but because they execute a **representation shift**. They observe the search space, deduce an underlying algebraic structure (e.g., restricting searches to Paley graphs or sequences with specific periodic properties), and transform an intractable $2^N$ space into a highly constrained, highly dense $2^{N/4}$ space.  
If Leibniz’s producer loop only operates on raw, un-factored bit arrays or block allocations, it remains blind to this abstraction layer. A $1,000 \\times$ increase in compute via GPUs will merely buy you 2 to 3 steps in sequence length before the exponential wall re-asserts itself.  
**The Fix:** If you build Track B, do not design the producer to search for *sequences*. Design the producer to search for *algebraic constraints* under which sequences can then be trivially found.

# Qwen 3.7 Max

\*\*1. The selection criterion\*\*  
"Records set by search we can strengthen" is necessary but fatally incomplete. The sharper discriminator is \*\*"low algebraic structure in known optimal solutions" combined with a "smooth, scalar-evaluable fitness landscape."\*\* In CWC, optimal codes are highly structured (algebraic/cyclic). If a domain's frontier is pushed by human algebra, search will fail.   
\*Steelman against Track B/D:\* Every finite-witness domain is either (1) solved to optimality in the tractable range, or (2) asymptotically bounded by deep theory, where the gap between "best heuristic search" and "best mathematical construction" is vast. If Leibniz just runs heuristic search, it will always lose to human mathematicians inventing new algebraic families. Track B is a procrastination trap to avoid admitting that autonomous search (D) is a permanent RED, and verification amplification (A) is the only viable product. \*I know\* from combinatorial optimization that pure search rarely beats structural insight in discrete math.

\*\*2. Recommend a domain\*\*  
\*\*LABS (Low-Autocorrelation Binary Sequences).\*\*  
\*   \*\*(i) Witness/Cost:\*\* An $N$-bit string. Kernel check is $O(N^2)$ integer arithmetic (sum of squared aperiodic autocorrelations). Trivial to formalize in Lean; representation cost is near zero.  
\*   \*\*(ii) Frontier:\*\* For $N \> 66$, the merit factor frontier is strictly dominated by heuristic/metaheuristic search (memetic algorithms, GPU simulated annealing). \*I guess with 85% confidence\* that no known algebraic constructions beat the best heuristic searches for large $N$. The landscape is rugged but the objective is a single scalar integer, making it ideal for LLM-guided evolutionary search (FunSearch).  
\*   \*\*(iii) Table:\*\* Borwein/Mertens tables are public, actively maintained, and strictly numerical.

\*\*3. Red-team the top three\*\*  
\*   \*\*LABS:\*\* \*Secret wall:\* The "compute asymmetry." SOTA LABS records for $N \\approx 100-200$ were set by massive GPU clusters running for weeks. A few hours of RunPod won't beat them by raw search. \*Pre-build probe:\* Run a baseline simulated annealing on $N=100$ for 10 GPU-hours. If it doesn't reach within 1% of the published record (I estimate 90% probability it won't), the compute gap is insurmountable for pure search.  
\*   \*\*Covering Designs:\*\* \*Secret wall:\* "Records" in La Jolla are frequently set by algebraic constructions (difference families, resolvable designs) or massive CPU-year exact searches, not by the heuristic local search an LLM can easily orchestrate. \*Pre-build probe:\* Audit the last 20 improvements in the La Jolla repo. If \>50% cite algebraic constructions or exact ILP rather than heuristic search, it's a CWC-wall clone.  
\*   \*\*Ramsey:\*\* \*Secret wall:\* Witness size and kernel choke. A coloring for $R(3, 30)$ requires checking $\\binom{30}{3}$ cliques. Lean's elaborator will choke on the massive boolean traces or large adjacency matrices without heavy custom tactic writing. \*Pre-build probe:\* Hand-code the known optimal Ramsey graph for $R(3, 25)$ in Lean and measure kernel verification time. If it takes \>5 minutes or OOMs, the representation cost breaks the daemon loop.

\*\*4. Soundness\*\*  
LABS keeps the invariants pristine. The witness is a raw bitstring. The check is deterministic integer arithmetic (no floats in the kernel). The novelty oracle is a simple integer comparison against a public table. No LLM decides. No structure is smuggled; the kernel independently computes the autocorrelations from the bits. The trust boundary is trivially maintained.

\*\*5. The meta-question — should we even pursue (D)?\*\*  
"Leibniz beats a heuristic record by renting more GPUs" is an engineering benchmark, not mathematical discovery, and is off-mission.   
\*   \*\*Greenlight condition:\*\* Pursue (D) \*only if\* the producer swing is \*\*algorithmic\*\*—i.e., the LLM uses FunSearch to invent a \*better heuristic, mutation operator, or fitness surrogate\* that beats SOTA on equal compute.   
\*   \*\*Stop condition:\*\* Stop at (A) \+ (C) if the only way to beat the record is \*\*brute-force compute scaling\*\* (running the same SA/CP-SAT longer). Verification amplification is the real product; beating a table via brute force is a costly distraction that yields no mathematical insight.

\*\*6. One thing we're likely getting wrong\*\*  
You are conflating "beating a public table" with "mathematical discovery." By optimizing for "table delta," you are incentivizing the daemon to engage in parameter tuning and brute-force search rather than structural insight. If Leibniz finds a LABS sequence with merit factor 10.51 instead of 10.50, it has produced a finite witness, but it has not produced \*mathematics\*. The producer wall in CWC wasn't just a failure of the LLM's search; it was a failure of your metric of success. True discovery requires proving a \*new bound\* or finding a \*new structural family\*, not just nudging a scalar in a table.

Prioritized recommendation: Halt the brute-force table-beating ambition, run the 10-hour LABS baseline probe to formally confirm the compute asymmetry, and pivot the FunSearch loop to strictly optimize for algorithmic heuristic invention rather than raw table delta.  
