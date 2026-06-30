# Fugu

\#\# Executive feedback

The brief asks the right questions, but the proposed mechanism is still too source-text-centric for the most sensitive path in the system.

My main objection:

\> Do not let a construction candidate supply \`theorem\_src\` and then try to prove it safe by prefix checks and token guards. The construction branch should take typed witness data and canonical parameters, then the trusted code should generate the entire Lean source from a fixed template.

If “only literals are witness-controlled” is the intended invariant, enforce that at the API boundary. Do not accept arbitrary Lean source for construction proofs.

The proposed inlined prelude can be acceptable, but only if it is treated as a hash-pinned trusted artifact and the theorem is generated, not parsed from candidate source. Prefix-detection as routing is not acceptable.

Given there is no record beat in hand, I would \*\*defer editing \`LeanVerifier.discharge\`\*\* unless you implement the construction path behind a disabled/non-promoting dry-run gate first. Editing the sole \`kernel\_verified\` writer for dormant infrastructure has poor risk/reward.

\---

\# 1\. Is the trusted-surface expansion sound?

Lean can soundly check multiple declarations. The expansion from one declaration to:

\`\`\`lean  
locked prelude \+ theorem := by decide  
\`\`\`

is not inherently unsound.

But the concrete admission mechanism is fragile if it relies on source text supplied by the candidate.

The strongest attack is not “make Lean prove false” directly. The strongest attack is:

\> Prove a true but different theorem, then let the faithfulness/novelty edge treat it as a record for a different canonical cell.

Examples:

\- theorem proves a smaller \`M\` but novelty compares against larger \`M\`;  
\- theorem proves a different \`(v,k,t)\` or \`(n,d,w)\`;  
\- theorem proves \`True\`;  
\- theorem proves validity under a different predicate name;  
\- theorem uses a witness different from the novelty object;  
\- theorem statement is syntactically allowed but semantically detached from the canonical tuple.

That yields a false promoted \*ledger record\* even if Lean checked a true formal theorem.

\#\# Mandatory guard

Do not guard arbitrary source. Generate source.

Required architecture:

\`\`\`text  
ConstructionCandidate {  
  kind: CONSTRUCTION  
  domain: CWC | COVERING | ...  
  canonical\_params: typed tuple  
  witness: typed data  
  claimed\_bound: typed integer  
}  
\`\`\`

Then:

\`\`\`text  
trusted renderer:  
  source \= LOCKED\_PRELUDE\_BYTES \++ render\_theorem(canonical\_params, witness, claimed\_bound)  
\`\`\`

The candidate should not provide \`theorem\_src\` at all. At most, if it does, it is ignored or compared byte-for-byte against the trusted rendering.

The theorem should be a canonical existential witness theorem, e.g.:

\`\`\`lean  
theorem cwc\_record\_candidate :  
  ExistsCWC n d w M := by decide  
\`\`\`

or:

\`\`\`lean  
theorem covering\_candidate :  
  ExistsCovering v k t B := by decide  
\`\`\`

where \`ExistsCWC\` / \`ExistsCovering\` are fixed definitions in the locked prelude.

Avoid proving only:

\`\`\`lean  
validCWC witness \= true  
\`\`\`

unless the promulgated statement is exactly that. Better is to prove the constructive mathematical claim directly:

\`\`\`lean  
∃ code, code.length \= M ∧ validCWC n d w code  
\`\`\`

For covering designs:

\`\`\`lean  
∃ blocks, blocks.length \= B ∧ validCovering v k t blocks  
\`\`\`

That keeps the proof edge aligned with the human claim.

\#\# Textual guards I would not trust alone

These are not sufficient as the primary defense:

\- \`startswith(LOCKED\_PRELUDE)\`;  
\- counting \`theorem\`;  
\- counting \`:=\`;  
\- regex banning \`def\`, \`axiom\`, \`macro\`;  
\- checking there is “exactly one theorem” by string operations;  
\- checking that the theorem contains \`by decide\`.

If you still use source guards, they must be secondary defense only.

\#\# Concrete required checks

I would require all of the following:

1\. \*\*Typed construction marker\*\*  
   Branch chosen by \`expr.kind \== CONSTRUCTION\`, not source prefix.

2\. \*\*Trusted source generation\*\*  
   Construction source is generated from typed canonical params \+ witness data.

3\. \*\*Prelude hash\*\*  
   Store and assert:

   \`\`\`text  
   sha256(prelude\_bytes) \== EXPECTED\_HASH  
   \`\`\`

4\. \*\*Hermetic Lean environment\*\*  
   \- pinned Lean binary/image hash;  
   \- no mutable import path;  
   \- fresh temp directory;  
   \- no candidate-controlled imports;  
   \- no network;  
   \- timeout \= failure;  
   \- nonzero Lean exit \= failure;  
   \- warnings involving \`sorry\`/axioms \= failure or post-audited.

5\. \*\*Axiom audit\*\*  
   After checking, query theorem dependencies / axioms. Reject \`sorryAx\`, \`axiom\`, \`unsafe\`, and any non-whitelisted axiom. For finite \`by decide\` construction claims, the ideal whitelist is empty or extremely small and explicit.

6\. \*\*No trusted result from external checker\*\*  
   External Python/CP-SAT verifier may be audit evidence, but \`kernel\_verified=True\` must come only from the Lean run.

7\. \*\*Canonical tuple binding\*\*  
   The proof edge, novelty edge, and faithfulness edge must share one canonical object hash:

   \`\`\`text  
   H \= hash(domain, params, witness, claimed\_bound)  
   \`\`\`

   The theorem source must be rendered from that object. The novelty oracle must read the same object.

8\. \*\*Negative test corpus\*\*  
   CI must include attacks:  
   \- hollowed \`validCovering\`;  
   \- shadowed \`validCovering\`;  
   \- theorem for wrong cell;  
   \- theorem for smaller bound;  
   \- invalid witness;  
   \- second theorem after first;  
   \- \`axiom\`;  
   \- \`sorry\`;  
   \- \`opaque\`;  
   \- \`macro\`;  
   \- \`native\_decide\`;  
   \- stale Lean cache;  
   \- timeout;  
   \- malicious comments/strings containing \`theorem\`;  
   \- alternate namespace;  
   \- local instance changing decidability;  
   \- candidate source starting with locked prelude but proving \`True\`.

\---

\# 2\. Inlined locked prelude vs in-image library module

An inlined locked prelude is acceptable \*\*if\*\* it is hash-pinned, operator-owned, generated into the source by trusted code, and checked hermetically.

A library module is not automatically safer. It introduces its own risks:

\- import-path shadowing;  
\- Docker/image drift;  
\- stale \`.olean\` artifacts;  
\- unpinned module version;  
\- candidate-controlled \`LEAN\_PATH\`;  
\- mismatch between reviewed source and imported compiled module.

The original ADR’s library-module design is cleaner operationally because theorem source can be theorem-only, but it is not inherently more sound than an inlined, byte-locked prelude.

\#\# Bright line

Either mechanism is acceptable only if:

\`\`\`text  
reviewed prelude source hash \== checked prelude source hash  
Lean toolchain/image hash is pinned  
candidate cannot alter imports/search path  
post-check axiom audit passes  
construction theorem is generated from typed data  
\`\`\`

Inlining is acceptable for a first implementation. But do not sell it as “the kernel only saw the prelude, therefore safe.” The prelude becomes part of the TCB and must be reviewed like TCB.

\---

\# 3\. Detection

\`is\_construction \= theorem\_src.startswith(LOCKED\_PRELUDE)\` is not safe.

It is the wrong abstraction. Routing should not depend on source content.

Require an explicit typed marker:

\`\`\`text  
expr.kind \= CONSTRUCTION  
expr.domain \= CWC | COVERING  
expr.params \= ...  
expr.witness \= ...  
expr.claimed\_bound \= ...  
\`\`\`

Then \`discharge\` dispatches by \`expr.kind\`.

Source-prefix detection can be kept as a sanity assertion:

\`\`\`text  
assert generated\_source.startswith(LOCKED\_PRELUDE\_BYTES)  
\`\`\`

but not as the branch selector.

Why this matters:

\- a normal proof could be misrouted into construction logic;  
\- a construction could be misrouted into normal proof logic;  
\- source-content routing creates weird policy holes;  
\- future maintainers may add a more permissive construction path and accidentally expand what prefix-matched source can do.

Branching must be typed, not inferred from text.

\---

\# 4\. Tri-edge binding

Yes. This is mandatory.

The construction proof edge proves truth. Faithfulness and novelty use canonical parameters. If these are not bound together, you can get a true theorem laundering a false record claim.

Required invariant:

\`\`\`text  
proof\_edge.object\_hash \== faithfulness\_edge.object\_hash \== novelty\_edge.object\_hash  
\`\`\`

where:

\`\`\`text  
object\_hash \= hash(domain, canonical\_params, claimed\_bound, witness)  
\`\`\`

\`discharge\_construction\` should not merely parse theorem params and compare them. Better:

1\. receive canonical object;  
2\. render Lean theorem from canonical object;  
3\. run Lean;  
4\. record the object hash in the proof edge;  
5\. novelty oracle reads the same canonical object;  
6\. promulgation requires all edges over the same hash.

If you must parse, parsing should be done by a trusted parser over a constrained data format, not by regex over Lean source.

\---

\# 5\. Should you do this now?

I would defer the \`kernel\_verified\` writer edit unless there is a near-term record-beating construction path.

Current fact:

\> The infrastructure would be dormant because reachable CWC cells have no beat.

Editing the sole \`kernel\_verified\` writer for dormant capability is negative expected value unless it unlocks an imminent measured milestone.

\#\# Greenlight condition

I would greenlight only if all are true:

1\. A second-domain Gate B1 or equivalent has produced a plausible record-beating finite witness path.  
2\. Construction source is generated from typed data, not accepted as source.  
3\. The locked prelude has been separately reviewed and hash-pinned.  
4\. Axiom audit is implemented.  
5\. Tri-edge object-hash binding is implemented.  
6\. Full malicious corpus passes.  
7\. The construction branch is initially feature-flagged or dry-run-only until an actual beat.  
8\. \`kernel\_verified\` remains written in exactly one place.

\#\# Defer condition

Defer if any of these are true:

\- construction candidates still carry arbitrary \`theorem\_src\`;  
\- branch routing uses prefix detection;  
\- no tri-edge binding;  
\- no axiom/sorry audit;  
\- no public-record beat or imminent second-domain test;  
\- Lean environment is not hermetic;  
\- prelude review is incomplete.

A safer intermediate step:

\`\`\`text  
construction\_kernel\_checked \= true  
\`\`\`

in an audit-tier field, not \`kernel\_verified\`, with identical Lean checking. This exercises the path without changing promulgation semantics. Promote to PROOF edge only when a record beat exists and the guard suite is green.

\---

\# 6\. One thing you are likely getting wrong

You are treating “the prelude is locked” as the central safety property. The more important safety property is:

\> The theorem statement must be generated from the same canonical object used by faithfulness and novelty.

A locked prelude prevents hollowed predicates. It does not prevent proving the wrong canonical claim.

For record construction, the dangerous failure is not Lean accepting \`False\`. The dangerous failure is:

\`\`\`text  
Lean proves true theorem T₁  
novelty oracle evaluates claim C₂  
promulgation presents C₂ as Q.E.D.  
\`\`\`

That is a ledger-integrity failure, not a kernel failure. Object-hash binding is the fix.

\---

\# Feedback on the brief itself

The brief is good but should be tightened before sending to witnesses.

\#\# Add this explicit adversarial assumption

Right now the brief says:

\> Only the theorem's literals are witness-controlled.

But the mechanism says:

\> \`expr.theorem\_src\` starts with a locked prelude.

Those conflict. If \`expr.theorem\_src\` is candidate-supplied, more than literals are witness-controlled.

Revise to one of:

\`\`\`text  
A. Candidate supplies typed witness only; trusted renderer creates theorem\_src.  
\`\`\`

or:

\`\`\`text  
B. Candidate supplies theorem\_src, but it must byte-equal trusted rendering from typed witness.  
\`\`\`

Do not leave this ambiguous.

\#\# Add exact required threat tests

The prompt mentions examples, but I would append a required CI list:

\- invalid witness rejected by Lean;  
\- valid witness accepted;  
\- wrong cell rejected by tri-edge binding;  
\- theorem for smaller bound rejected;  
\- prelude byte mutation rejected;  
\- extra declaration rejected;  
\- \`sorry\` rejected;  
\- \`axiom\` rejected;  
\- \`native\_decide\` rejected;  
\- timeout rejected;  
\- table novelty mismatch rejected;  
\- stale cache cannot cause success.

\#\# Add the axiom/sorry issue explicitly

Lean can accept \`sorry\` as a warning in some workflows. Even if your guard bans it in the theorem, the prelude/imports can carry assumptions.

The prompt should ask:

\> Must \`discharge\_construction\` run an axiom-footprint check and reject \`sorryAx\` / non-whitelisted axioms?

My answer: yes.

\#\# Clarify \`check\_source\`

The phrase “runs the Lean kernel on the whole source” is imprecise. Source checking includes parser, elaborator, environment, imports, macros, typeclass inference, and the kernel.

Better wording:

\> runs the pinned Lean toolchain in a hermetic environment and accepts only if the target theorem is elaborated and kernel-checked, with an audited axiom footprint.

\#\# Clarify theorem shape

Specify whether the target theorem is:

\`\`\`lean  
validCovering witness \= true  
\`\`\`

or:

\`\`\`lean  
∃ blocks, blocks.length \= B ∧ validCovering v k t blocks  
\`\`\`

For promulgation, prefer the existential theorem.

\---

\#\# Minimal acceptable design

If I were approving the implementation, my minimum bar would be:

\`\`\`text  
\- explicit expr.kind \== CONSTRUCTION  
\- no candidate-supplied Lean source accepted  
\- trusted renderer generates source from typed witness/canonical tuple  
\- locked prelude hash-pinned  
\- theorem statement is canonical existential witness claim  
\- hermetic pinned Lean run  
\- timeout/nonzero/warning/sorryAx/non-whitelisted axiom \= fail  
\- proof/faithfulness/novelty edges share canonical object hash  
\- malicious regression corpus passes  
\- branch initially dry-run or feature-flagged until a record beat exists  
\`\`\`

Without those, I would not edit \`LeanVerifier.discharge\`.

# Fugu Ultra

\#\# Executive verdict

Do \*\*not\*\* implement the construction PROOF edge as described.

The objective is legitimate: finite construction witnesses should eventually be promotable when Lean verifies the relevant theorem. But the proposed mechanism — candidate/source begins with a byte-identical prelude, then a text/structure guard checks the suffix — is too fragile for the one function that writes \`kernel\_verified\`.

The safe version is:

\> \`discharge\_construction\` consumes a typed, canonical construction object; the verifier itself assembles the locked prelude and the theorem from trusted templates; the witness controls only data literals; Lean verifies the generated source; promotion requires proof/faithfulness/novelty receipts bound to the same canonical claim ID.

Until then, keep constructions audit-tier.

\---

\#\# 1\. Is the trusted-surface expansion sound?

Not as described.

The biggest risk is not that Lean proves \`False\`. The biggest risk is that Lean proves a \*\*true but wrong proposition\*\*, and the system attaches that proof edge to a different record claim.

Concrete attack shape:

\`\`\`lean  
\-- locked prelude

theorem claimed\_record : True := by decide  
\`\`\`

or:

\`\`\`lean  
\-- locked prelude

theorem claimed\_record :  
  (let validCovering := fun (\_v \_k \_t : Nat) (\_blocks : List (List Nat)) \=\> true  
   validCovering 100 10 5 badBlocks \= true) := by decide  
\`\`\`

This uses no top-level \`def\`, no \`axiom\`, no second theorem, and \`by decide\` succeeds. A token guard can pass while the theorem proves something irrelevant or locally shadowed. If the novelty/faithfulness edge separately says this is a record for \`(v,k,t,B)\`, you have a false ledger claim even though Lean behaved soundly.

Mandated guards:

1\. \*\*No candidate-supplied Lean source in the construction path.\*\*    
   The input should be typed data: domain, parameters, bound, canonical witness, prelude version, template version.

2\. \*\*Verifier-owned source generation.\*\*    
   The verifier builds:

   \`\`\`text  
   LOCKED\_PRELUDE\_BYTES \++ render\_theorem\_from\_canonical\_data(...)  
   \`\`\`

   The producer never supplies raw theorem syntax.

3\. \*\*Exact theorem template.\*\*    
   The theorem name, proposition shape, helper names, and proof skeleton are generated. The witness controls only integer/list literals after canonicalization.

4\. \*\*Expected theorem-type check.\*\*    
   After Lean elaborates the source, the receipt should say the expected theorem exists and its type matches the expected formal proposition. Do not rely only on text shape.

5\. \*\*Environment-diff check.\*\*    
   The checked source should add exactly the locked prelude declarations plus exactly one expected theorem. No extra constants, axioms, instances, attributes, macros, notation, imports, or auxiliary declarations.

6\. \*\*Axiom/sorry audit.\*\*    
   Reject \`sorryAx\`, \`axiom\`, \`constant\`, \`opaque\`, unsafe/native code, \`native\_decide\`, unreviewed imports, and unexpected axioms. For these finite witness theorems, the axiom closure should ideally be empty or a tiny explicit allowlist.

7\. \*\*Fail-closed \`check\_source\`.\*\*    
   Timeout, OOM, nonzero exit, killed process, parser failure, missing theorem, theorem-name mismatch, theorem-type mismatch, or inability to compute axiom closure must all be failure. Do not parse “absence of error text” as success.

8\. \*\*Semantic review of the prelude.\*\*    
   Byte-identical does not mean correct. A locked but wrong \`validCovering\`, \`validCWC\`, \`combs\`, distance function, or coverage predicate makes Lean prove the wrong formal claim. The prelude needs review, tests, and preferably kernel-checked bridge lemmas connecting optimized Boolean checks to the mathematical specification.

\---

\#\# 2\. Inlined locked prelude vs in-image library module

An inlined locked prelude is acceptable \*\*if\*\* it is operator-owned, hash-pinned, axiom-audited, and assembled by the verifier.

A library module is not automatically safer. \`import ConstructionPrelude\` is safe only if the Docker image, Lean version, module contents, dependency hashes, and import path are pinned and reproducible. Otherwise the trusted surface becomes a mutable image dependency.

Trade-off:

\- \*\*Inline prelude\*\*  
  \- Pros: self-contained, content-addressed, no import-path poisoning, easier replay.  
  \- Cons: larger source each time, slower checks, more temptation to use prefix-routing.

\- \*\*In-image module\*\*  
  \- Pros: cleaner theorem-only source, better long-term maintainability.  
  \- Cons: requires reproducible image discipline; import-by-name can hide supply-chain drift.

Bright line:

\> The prelude must be content-addressed, versioned, operator-owned, axiom-audited, and non-substitutable. Packaging is secondary.

But I would not accept “candidate provides source that starts with the prelude.” If inlining is used, the verifier should prepend the prelude itself.

\---

\#\# 3\. Detection

Prefix detection is not safe.

Do not define:

\`\`\`text  
is\_construction \= theorem\_src starts with LOCKED\_PRELUDE  
\`\`\`

Routing by source text lets an adversary or malformed artifact choose the trust path.

Use an explicit typed marker, for example:

\`\`\`text  
expr.kind \= CONSTRUCTION\_PROOF  
expr.domain \= CWC | COVERING  
expr.schema\_version \= ...  
expr.prelude\_version \= ...  
expr.template\_version \= ...  
\`\`\`

This marker should be assigned/validated by trusted ingestion code, not accepted as an unchecked producer claim.

Required behavior:

\- normal proof with a prelude prefix: reject or route through the normal path, but never infer construction status from text;  
\- construction object with malformed data: reject/quarantine;  
\- construction object that fails construction discharge: fail closed, no fallback to the single-declaration path;  
\- branch choice should not weaken checks. Ideally the construction branch is stricter than the normal path.

\---

\#\# 4\. Tri-edge binding

Yes, mandatory.

The proof edge, faithfulness edge, and novelty edge must all refer to the same canonical claim ID.

Example:

\`\`\`text  
claim\_id \= hash(  
  domain,  
  params,  
  inequality\_direction,  
  bound,  
  canonical\_witness\_hash,  
  prelude\_version,  
  theorem\_template\_version,  
  table\_snapshot\_id  
)  
\`\`\`

For CWC:

\`\`\`text  
(n, d, w, M, witness\_hash)  
\`\`\`

For covering designs:

\`\`\`text  
(v, k, t, B, witness\_hash)  
\`\`\`

Promotion should require:

\`\`\`text  
proof\_receipt.claim\_id \== faithfulness\_receipt.claim\_id \== novelty\_receipt.claim\_id  
\`\`\`

Do not parse theorem parameters out of candidate-authored Lean and then compare them. Make the canonical tuple the source of truth, generate the theorem from it, and have the novelty oracle compare that same tuple against the frozen table snapshot.

Otherwise a true theorem for an easy cell can launder a novelty claim for a hard cell.

\---

\#\# 5\. What should the theorem actually prove?

This is under-emphasized in the brief.

A theorem of the form:

\`\`\`lean  
validCovering v k t blocks \= true  
\`\`\`

does not literally prove:

\`\`\`text  
C(v,k,t) ≤ B  
\`\`\`

unless the formal system also defines the covering number or an equivalent existential bound predicate and proves the bridge.

You have two options:

\#\#\# Weak version

Lean proves only witness validity. The ledger then says the record claim follows externally.

I would not use this for Q.E.D. promulgation. It leaves the record inequality outside the kernel.

\#\#\# Strong version

The locked prelude defines the formal record claim or an equivalent finite existential predicate, then proves a bridge lemma:

\`\`\`text  
validCovering v k t blocks \= true  
∧ blocks.length \= B  
→ C(v,k,t) ≤ B  
\`\`\`

or, if avoiding a global minimum definition:

\`\`\`text  
∃ blocks, blocks.length \= B ∧ validCovering v k t blocks  
\`\`\`

Then the generated theorem asserts the actual finite construction claim.

This is the version I would require before a real PROOF edge.

\---

\#\# 6\. Should this be done now?

I would defer editing \`LeanVerifier.discharge\`.

Reason: the payoff is currently dormant, but the blast radius is maximal. You would be touching the one writer of \`kernel\_verified\` before there is a record-beating construction to promulgate.

What I would greenlight now:

\- build \`ConstructionVerifier.check\` as a \*\*non-promoting audit path\*\*;  
\- use typed construction objects;  
\- generate source from trusted templates;  
\- run Lean;  
\- emit structured receipts;  
\- perform axiom/environment/type checks;  
\- verify known/classical witnesses;  
\- run adversarial tests;  
\- do \*\*not\*\* set \`kernel\_verified\`.

Greenlight the real PROOF edge only when all are true:

1\. a genuine record-beating candidate exists;  
2\. construction verifier has passed adversarial tests;  
3\. source is verifier-generated, not candidate-authored;  
4\. prelude is content-addressed and axiom-audited;  
5\. theorem proves the actual construction/record claim, not merely an unrelated helper predicate;  
6\. proof/faithfulness/novelty share one canonical claim ID;  
7\. \`check\_source\` emits structured fail-closed receipts;  
8\. human ADR explicitly approves the TCB expansion.

\---

\#\# 7\. One thing you are likely getting wrong

You are over-focusing on byte-identical prelude locking.

A locked prelude prevents only one attack: replacing helper definitions. It does not prevent:

\- proving \`True\`;  
\- proving a theorem about the wrong parameters;  
\- local shadowing inside the theorem statement;  
\- a valid proof being attached to the wrong novelty cell;  
\- a timeout being interpreted as success;  
\- a wrong-but-locked prelude formalizing the wrong predicate;  
\- Docker/module drift if imports are later used.

The central invariant should be:

\> The verifier generated the exact theorem from the canonical witness and canonical record tuple; Lean verified that exact theorem; the proof, faithfulness, and novelty receipts all bind to the same claim ID.

\---

\#\# Suggested edits to the brief

Before sending this to witnesses, I would revise the brief in these ways:

1\. Replace “expanding the kernel’s trusted surface” with “expanding the verifier glue around the kernel.”    
   The kernel is not the main new risk; the renderer/router/harness/prelude are.

2\. Ask explicitly whether candidate-supplied Lean source should be accepted at all.    
   My answer: no.

3\. Add a question about whether the theorem proves the actual record claim or only witness validity.

4\. Add a question about \`check\_source\` success semantics: exit code, timeout, OOM, theorem lookup, theorem type, axiom closure.

5\. Require explicit typed construction markers instead of prefix detection.

6\. Require claim-ID binding across proof, faithfulness, and novelty.

7\. Fill in the internal adversarial review section before the panel sees the brief. Otherwise witnesses are reviewing an incomplete artifact.

\---

\#\# Final recommendation

Do not implement the PROOF edge via prefix-detected candidate \`theorem\_src\`; build a non-promoting construction verifier first, using typed construction objects, verifier-generated Lean, a hash-pinned semantic prelude, structured fail-closed receipts, expected-type/environment/axiom checks, and mandatory tri-edge claim binding, then enable promotion only when a real record beat exists and a human ADR approves the trust-core edit.

# Deepseek v4 Pro

I’ll review the proposed construction PROOF‑edge, the single most sensitive edit in the project. I’ll be adversarial, concrete, and hold the soundness line absolutely. Where I see attacks, I’ll name exact mechanisms and guards.

\---

\#\# 1\. Is the trusted‑surface expansion sound?

The strongest concrete attack is \*\*name‑shadowing of a prelude definition by a local binder in the theorem source\*\*.

Suppose the locked prelude defines:

\`\`\`lean  
def validCovering (blocks : List (List Nat)) (v k t size : Nat) : Prop := ...  
\`\`\`

The theorem part (witness‑controlled) is required to be exactly one theorem with \`:= by decide\`. But the witness could craft a statement such as:

\`\`\`lean  
theorem my\_thm :   
  (let validCovering := fun \_ \_ \_ \_ \_ \=\> True;   
   validCovering someBlocks v k t size) := by  
  decide  
\`\`\`

The Lean kernel will type‑check this as \`True\`, a trivial theorem. The \`kernel\_verified\` flag will be set, yet the proven statement does \*\*not\*\* assert the intended global property. The \`let\` shadows the prelude’s \`validCovering\` and the \`decide\` call trivially succeeds. The only restriction “no \`def\`/\`axiom\`/\`macro\`/\`native\_decide\`/… and exactly one \`theorem\`/one \`:=\`” does \*\*not\*\* block \`let\` binders in the type. It must.

A second attack is a \*\*\`have\` binder\*\* that proves a falsehood locally and then uses \`decide\`. For example:

\`\`\`lean  
theorem foo : validCovering blocks v k t size := by  
  have : False := by decide  
  exact False.elim this  
\`\`\`

Here \`by decide\` on \`False\` would fail, so this particular one is caught. But a more subtle \`have\` that assumes an impossible hypothesis and then uses \`decide\` on a decidable proposition could succeed if \`decide\` can handle it. The core issue is any binder that changes the local context. The theorem must be a pure proposition with no local binders in its statement, and the proof must be exactly \`by decide\` with no extra commands.

\*\*Mandated guards:\*\*

\- \*\*No binder that shadows any name defined in the prelude.\*\* The theorem part must be syntactically restricted: no \`let\`, \`have\`, \`fun\`, \`∀\`, \`∃\`, \`λ\`, or any binder that introduces a name identical to a name defined in the locked prelude. The simplest way is to put the prelude definitions in a dedicated namespace (e.g., \`Construction\`) and forbid the theorem from opening that namespace or using any name from it except fully qualified (e.g., \`Construction.validCovering\`). Then a local \`validCovering\` (unqualified) cannot shadow the prelude.  
\- \*\*Theorem body must be exactly \`by decide\`\*\* with no additional commands, no \`apply\`, no \`exact\`, no \`calc\`, etc. The structural guard must check this precisely.  
\- \*\*No \`import\` in the theorem part\*\* (the prelude already contains all needed imports).  
\- \*\*\`check\_source\` must run the full kernel on the concatenated source.\*\* Its exit code must be the sole determiner. The \`discharge\` must not make any assumption about success/timeouts; only a clean exit from the kernel is accepted.

With these guards, the expansion from “one declaration” to “locked prelude \+ one guarded theorem” is sound \*provided the prelude itself is sound and contains no axioms\*. The prelude is operator‑owned, so its soundness is a human‑review responsibility, and it must be as small as possible.

\---

\#\# 2\. Inlined locked prelude vs in‑image library module

The inlined approach verifies the full prelude every time by comparing a byte‑identical prefix. The library module approach would compile the prelude once into the Lean environment (as part of the trusted docker image) and then only check the theorem.

\*\*Trade‑off:\*\*  
\- \*\*Inlined:\*\* The entire checking is self‑contained and deterministic. There is no hidden environment state. The cost is repeated compilation (negligible for a small prelude). The risk is the prelude bytes comparison itself – a one‑character off‑by‑one in the checking code could invalidate the guard. It also means the prelude cannot be updated without a code change (which might be a feature).  
\- \*\*Library module:\*\* Clean separation: the theorem source is minimal. It requires maintaining a trusted base image, which is a larger operational burden (Dockerfile, builds, versioning). It also introduces a trust dependency on the image build process; a compromised image could replace the module, and \`check\_source\` would not detect it because the module is pre‑compiled.

\*\*Bright line:\*\* The inlined \+ \`check\_source\` approach is \*\*acceptable\*\* if the prelude is small (a few dozen lines) and the byte‑comparison is implemented in a simple, auditable way (e.g., using a hard‑coded constant \`bytes\` and a direct slice comparison). It avoids expanding the TCB into the build system. However, the prelude \*\*must be fully self‑contained\*\*: no imports that could change semantics with compiler versions, and it must be tested across Lean versions. Given the team’s “one TCB, minimal surface” philosophy, the inlined approach is safer than adding a docker‑image builder to the trusted base.

I would mandate that the prelude’s byte‑identical check uses a \*\*cryptographic hash\*\* of the original prelude, stored in the source code, and that \`discharge\` compares the hash of the received prefix, not the raw bytes at runtime (to avoid string‑manipulation bugs). The prelude itself is then embedded as a constant. This is cleaner.

\---

\#\# 3\. Detection: prefix‑detection vs explicit marker

Prefix‑detection (\`theorem\_src.startswith(LOCKED\_PRELUDE)\`) is \*\*fragile and dangerous\*\* as a routing mechanism.

An attacker could craft a non‑construction proof whose source, by coincidence or design, begins with the same bytes as the locked prelude. For example, they could embed the prelude as a comment (\`/-- ... \-/\`) or a doc‑string and then append a second theorem that is not a construction. If the structural guard only looks at the remainder after the prelude, it might accept the remainder and run \`check\_source\`, which would succeed, and the edge would be mis‑routed as a construction. While the prelude bytes are a specific, non‑trivial sequence, it is \*\*not impossible\*\* to engineer a collision. Moreover, any future change to the prelude would change the prefix, requiring careful coordination.

The safe design uses an \*\*explicit, separate field\*\* in the record, e.g., \`record\_type \= "construction"\` (or a dedicated database column). The \`discharge\` function then branches on that field, not on the content of the source. This is impossible to mis‑route by content manipulation. The field must be set by the system when the construction is produced, and the producer cannot override it.

I would mandate: add \`record\_type : enum { normal\_proof, construction }\` and use it for dispatch. Remove the prefix detection entirely.

\---

\#\# 4\. Tri‑edge binding: must the theorem’s params be bound to the canonical tuple?

Yes, absolutely. If the witness can control the entire theorem statement (not just the construction data), it could prove a true statement about a \*\*different\*\* set of parameters than the claimed record. For example, for a covering design claim \`C(10,4,2) ≤ 4\`, the witness could provide a theorem that proves a true statement about \`C(11,4,2) ≤ 4\` (a weaker or different bound), and the record would be mis‑attributed. The novelty oracle looks up \`(v,k,t)\` in the public table; if the proven theorem does not match those exact parameters, the edge is fraudulent.

The correct mechanism is: \*\*the witness only supplies the finite construction object\*\* (the list of blocks, the list of codewords, etc.). The system then generates the full theorem source by inserting that object into a fixed template that already contains the canonical parameters (derived from the target cell). \`discharge\_construction\` would know the cell’s parameters from the record metadata and can verify that the theorem’s statement exactly matches. This also eliminates the shadowing attack entirely because the template is controlled by the system.

I would require that the construction witness be a plain data object (e.g., a JSON array) and that the theorem source is built by a \*\*trusted template function\*\* that is part of the \`discharge\` logic (or a small, locked module within \`discharge\`). The template uses the canonical parameters and the witness data, and the resulting source is then checked. This means the witness is \*\*data, not code\*\*, and no code injection is possible.

\---

\#\# 5\. Should we do this at all now?

\*\*No.\*\*

The entire payoff is contingent on a record beat that does not exist and, by current measurement, is not reachable. Editing \`LeanVerifier.discharge\` — the \*\*sole\*\* function that ever sets \`kernel\_verified\` — for a dormant feature is an unjustified risk. Even a correct implementation adds attack surface (the new branch, the new guards, the template mechanism) that must be maintained and could be exploited in unforeseen ways.

The construction verification works today in audit tier (kernel re‑checked, not promulgated). If a record beat is ever achieved, the verified construction can be stored, and \*\*then\*\* the PROOF edge can be implemented and the record promulgated retroactively. There is no deadline.

I would \*\*greenlight\*\* this change only when:  
\- A genuine record‑beating construction has been produced by the system (or a human) and verified by the existing audit‑tier checker.  
\- The team decides it is worth the effort to stamp it with a full \`Q.E.D.\` edge.  
\- The implementation passes a full adversarial review (like this one) with \*\*independent\*\* penetration testing against the shadowing and routing attacks.

Otherwise, defer indefinitely. The security of the core invariant outweighs the convenience of having the edge ready.

\---

\#\# 6\. One thing we’re likely getting wrong

\*\*You are treating the \`discharge\` function as a feature to be extended, when it should be treated as a sealed cryptographically‑critical enclave.\*\* Every edit to it — even a well‑intentioned one — is a potential point of failure. The current single‑declaration invariant is beautifully simple and hard to break. Adding a construction branch with a prelude, guards, and template generation is a permanent expansion of the trusted surface. My most important warning:

\*\*The construction PROOF edge is a convenience for a use case that does not yet exist, and the cost is a permanently enlarged TCB. The right decision is to keep constructions as verified audit objects until the moment a record beat materialises, then implement the PROOF edge under extreme scrutiny, and then immediately seal the \`discharge\` function again. Do not edit it now.\*\*

# Kimi:Latest

\*\*This is a review of the PROOF-EDGE EXTERNAL WITNESS BRIEF, answering the six prompt questions as an adversarial witness.\*\*

\---

\#\#\# 1\. Is the trusted-surface expansion sound? Strongest concrete attack; exact guard.

\*\*No — expansion is not sound under the concrete mechanism described.\*\* The move from "one self-contained declaration" to "source-injected prelude \+ remainder guard" replaces a simple invariant with a complex one that is bypassable by comment/string hiding, parser mismatch, and environment smuggling.

\*\*Strongest concrete attack:\*\* The producer embeds a \*\*second declaration inside a \`/- ... \-/\` block or a string literal\*\* that your structural guard (if regex or token-count based) misses, introducing a new \`def validCovering' := ...\` or an \`axiom cheat : False\` in the theorem’s local scope. Because the guard enforces "exactly one \`theorem\`" and "no \`def\`" by \*textual\* or \*naive syntactic\* checks, a comment-shrouded declaration does not increment a naïve counter. After the guard passes, the combined source is fed to \`check\_source\`, where the smuggled declaration shadows or weakens the prelude’s predicate, causing \`by decide\` to prove a computationally equivalent but semantically hollow statement. A second variant: the theorem’s type uses \`native\_decide\` hidden behind a locked-prelude macro (if the prelude defines even benign tactics that can be tricked), or \`check\_source\` shares a mutable environment between calls, letting a previous (audit-tier) import persist.

\*\*Exact guard I would mandate (all mandatory, not optional):\*\*

1\. \*\*No runtime string prefix matching.\*\* The prelude is identified by a \*\*hardcoded SHA-256 hash\*\* in the verifier binary, verified after full UTF-8 normalization. Anything else is a bypass waiting to happen.  
2\. \*\*Parse, don’t scan.\*\* Feed the combined prelude+theorem to Lean’s actual parser. After elaboration, \*\*diff the \`Environment.constants\` map\*\* against a pristine environment obtained by parsing the hash-identical prelude alone. The diff must contain \*\*exactly one\*\* new constant, of kind \`Theorem\`. Zero new \`def\`, \`axiom\`, \`opaque\`, \`instance\`, \`inductive\`, \`structure\`, \`class\`, or \`abbrev\`.  
3\. \*\*Axiom audit.\*\* Prelude and final environment must each have zero axioms (\`env.constants.toList.filter (fun c \=\> c.isAxiom)\` is empty). This is checked offline for the prelude, and re-checked at runtime.  
4\. \*\*Tactic whitelisting via syntax.\*\* The theorem body is parsed; its syntax must be exactly \`:= by decide\` — no tactic combinators (\`\<;\>\`), no \`by decide ...\`, no alternative tactics, and the tactic name must be the bare identifier \`decide\` from \`Init.Core\`, not a local alias.  
5\. \*\*Heartbeat trap.\*\* Wrap \`check\_source\` in a deterministic timeout. Catch \`Lean.Exception.isMaxHeartbeat\` explicitly; any timeout yields \`kernel\_verified \= false\`, never \`true\`. An uncaught exception bubbling through a generic handler is an unsoundness bug.  
6\. \*\*No prelude definitions shadowable by theorem parameters.\*\* The theorem’s local binders must be alpha-renamed to avoid shadowing prelude names; better yet, the prelude names should be \`protected\` and referenced with fully qualified names in the theorem template.

\---

\#\#\# 2\. Inlined locked prelude vs. in-image library module.

\*\*In-image library module is the bright line; inlined is a trust regression you are proposing to avoid a build-artifact problem.\*\*

\*\*Trade-off:\*\* The ADR 0045 mechanism (library module, theorem-only source) removes the entire class of injection/concatenation attacks. The inlined alternative introduces runtime source composition, a larger parser surface, and a subtle dependency on \`check\_source\` parsing multi-command sources correctly in sequence. You are treating "no in-repo Dockerfile" as a hard environmental constraint; it is not. It is a one-time process cost. A project whose reason to exist is a minimal TCB should not weaken its kernel-side mechanism because a build file is missing.

\*\*Acceptability of inlined:\*\* Tolerable \*\*only if\*\* the SHA-256 \+ environment-diff guard above is implemented. But even then, it is inferior because the kernel now sees a source stream whose provenance is partially runtime-generated. If any downstream tooling (logging, replay, proof export) assumes single-declaration source files, the construction branch breaks that invariant silently.

\*\*My bright line:\*\* \*\*Build the Dockerfile / CI image and use the library module.\*\* The theorem source should be \*only\* the \`theorem … := by decide\`. If creating an in-repo build pipeline is genuinely blocked by process, then the mitigation must be \*\*a staged, operator-signed, hash-locked prelude file read from a read-only path at boot\*\*, not a string injected from the producer. But the library module remains the reviewed and approved ADR 0045 design; altering it in implementation without revisiting the ADR is architectural drift.

\---

\#\#\# 3\. Detection: prefix-detection safety.

\*\*Prefix detection is unacceptable.\*\* It creates a routing ambiguity where the decision of which trust/code path to execute depends on inspecting attacker-controlled text, not on an immutable, typed system property.

\*\*Concrete risk (misroute-in):\*\* A normal (non-construction) proof string begins with the locked prelude bytes (by accident or malice) and is routed to \`discharge\_construction\`. Even though the guard may then reject it, the parsing surface has changed: \`discharge\_construction\` relaxes the "one declaration" rule and may use a different \`check\_source\` configuration. If the normal proof contains valid Lean that happens to pass the construction guard (e.g., it is exactly one theorem because it was generated adversarially), it now enters a path that may handle namespaces or constants differently.

\*\*Concrete risk (misroute-out):\*\* A construction whose prelude is missing a trailing newline, or whose encoding differs in an invisible way, fails prefix detection, falls back to \`check\_proof\`, and is rejected. This is a false-negative, not unsound, but it poisons the operator’s telemetry.

\*\*Bright line:\*\* \`Expr\` must carry an explicit, typed field \`proof\_kind : { STANDARD | CONSTRUCTION }\`, set by the \*operator pipeline\* (ingestion or domain selector) and \*\*immutable thereafter\*\*. The router checks \`proof\_kind\`, not content. After routing, the verifier \*separately\* asserts that a \`CONSTRUCTION\` expr’s source contains the hash-locked prelude, and a \`STANDARD\` expr’s source does not. Routing and content validation are orthogonal.

\---

\#\#\# 4\. Tri-edge binding.

\*\*Yes — absolutely mandatory, and the current proposal under-specifies it.\*\* Without tri-edge binding, \`discharge\_construction\` proves a true theorem about the wrong cell, and the novelty oracle, inspecting only the metadata tuple \`(v,k,t,size)\`, falsely attributes the proof to a record it did not earn.

\*\*Mechanism:\*\* The theorem’s type must be \*\*verifier-generated or verifier-parsed\*\*, not producer-supplied. The best approach:

\- \*\*Option A (strongest):\*\* The verifier constructs the entire theorem string except the witness literal. It generates:  
  \`\`\`lean  
  theorem c\_\<v\>\_\<k\>\_\<t\> : validCovering \<v\> \<k\> \<t\> \<producer\_witness\> := by decide  
  \`\`\`  
  The producer is only permitted to supply the \`\<producer\_witness\>\` AST or s-expression. This eliminates laundering entirely.

\- \*\*Option B (if full-text generation is infeasible):\*\* The producer supplies the full text, but after parsing, the verifier walks the theorem’s type AST. It must find the constant \`validCovering\` (or equivalent) applied to exactly four arguments: numerals for \`v\`, \`k\`, \`t\`, and the witness term. These numerals must be \*\*syntactically identical\*\* to the canonical tuple integers. If any argument is a variable, a computed expression, or a mismatching numeral, reject.

Additionally, the theorem must prove a \*\*concrete bound\*\*, not an existential. A theorem of the form \`∃ blocks : List (Fin v), blocks.length ≤ B ∧ validCovering v k t blocks\` is easier to prove (unpack the witness and trivially prove the bound) but does not guarantee the actual cardinality. The type must be \`validCovering v k t blocks\` with \`blocks\` a concrete list, and the oracle separately computes \`size \= blocks.length\` to compare against the table.

\---

\#\#\# 5\. Should we do this at all now?

\*\*No. Defer.\*\* Editing \`LeanVerifier.discharge\` — the \*sole\* \`kernel\_verified\` writer — is a one-way, irreversible trust event. Doing it speculatively for dormant infrastructure violates the principle of minimal change to the TCB.

Your own measurement shows that in CWC, no reachable record beat exists; the second-domain decision (Gate B0) is not yet closed; and the audit-tier path already kernel-checks constructions without promulgation. Therefore the \*\*only\*\* thing this edit unlocks is public issuance of a record-beating witness. Since no such witness exists in hand, the edit is pure latent risk with zero immediate payoff.

\*\*Condition to greenlight:\*\* Exactly one of the following:  
\- An audit-tier construction has been kernel-verified, novelty-oracle confirmed, and operator-approved for promulgation, AND the current \`discharge\` cannot promulgate it because the single-declaration path rejects the multi-declaration proof. (If the audit path works, waiting costs nothing.)  
\- OR the second-domain program (Track B) produces a verified beat and the operator explicitly requests promulgation.

\*\*Condition to defer (current state):\*\* All other cases. That is now.

\---

\#\#\# 6\. One thing you're likely getting wrong.

\*\*You believe that \`by decide\` is intrinsically safe because it is "only computation," and therefore the prelude's definitions don't need the same verification rigor as a proof term.\*\* This is false. \`by decide\` reduces the goal using Lean's \*\*type-class machinery\*\* and \*\*definitional equality\*\*. A locked prelude that defines \`validCovering\` \*and\* a custom \`Decidable\` instance for it — or worse, an \`@\[inline\] abbrev\` that changes reduction behavior — can make \`decide\` return \`true\` for an invalid witness without introducing an explicit axiom. You are assuming the prelude is correct because you wrote it; that is exactly the "trusted because operator-owned" fallacy that the rest of the project is designed to eliminate.

The prelude must be treated with the same paranoia as the kernel: its definitions must be \*\*computably transparent\*\* (no \`opaque\`, no \`axiom\`, no classical reasoning), its \`Decidable\` instances must be derived algorithmically, and ideally, there should be a \*\*separate, offline kernel proof\*\* that \`validCovering\` is equivalent to the mathematical definition (coverage check against \`combs\`). Until that exists, \`by decide\` over the prelude is a mechanized appeal to authority, not a mechanized proof of correctness.

\---

\#\#\# Summary

The proposed inlined-prelude mechanism is a trust regression from the reviewed ADR 0045\. If you proceed, you must: (1) \*\*route via typed marker, not prefix\*\*; (2) \*\*verify prelude by cryptographic hash and environment diff, not string inspection\*\*; (3) \*\*bind the theorem parameters to the canonical tuple via verifier-generated types\*\*; and (4) \*\*defer the \`discharge\` edit until a verified record beat is in hand and ready for promulgation.\*\* The absence of a Dockerfile is not a justification for weakening the kernel boundary.

# GLM 5.2

1\. \*\*Is the trusted-surface expansion sound?\*\*  
No. The strongest concrete attack is \*\*Vacuous Satisfaction via Unchecked Literal Injection\*\*. You stated: "Only the theorem's literals are witness-controlled." This is the kill vector. If the witness controls the literals, a malicious/buggy producer can inject a witness that is vacuously true (e.g., an empty list, or a list of the wrong length) but whose literal parameters in the theorem statement claim a record for a different cell.   
For example, the producer submits the literal \`A(50, 10, 5\) ≥ 100\` for the novelty oracle, but the theorem it actually proves is \`validCWC \[\] := by decide\` (because \`validCWC\` evaluates to \`True\` for an empty list). The guard sees one \`theorem\`, one \`:=\`, \`by decide\`, and the prelude is byte-identical. The kernel verifies it. The oracle stamps a record for the (50,10,5) cell. You just stamped a false Q.E.D.  
\*Exact guard to mandate:\* The \`discharge\` function must not trust the theorem string's literals. It must parse the theorem's AST, extract the exact numeric literals, and assert strict equality against the canonical \`(v,k,t,size)\` tuple from the internal pipeline state. If the AST literals do not match the canonical tuple, \`kernel\_verified\` must be set to \`False\`.

2\. \*\*Inlined locked prelude vs in-image library module.\*\*  
\*\*In-image library module is mandatory.\*\* Inlining is unacceptable.  
\*Trade-off:\* Inlining saves you a Docker image rebuild but introduces a bespoke, fragile string-concatenation trust boundary. Lean's module system is designed exactly for this: to provide immutable, compiled definitions. \`import ConstructionPrelude\` guarantees the definitions are in the environment and cannot be shadowed or altered by subsequent text.  
\*Bright line:\* If the prelude is inlined, the trusted surface expands to include your custom string-concatenation logic, prefix-matching logic, and the assumption that Lean's \`check\_source\` processes concatenated strings identically to modular files (a dangerous assumption given Lean's macro expansion and namespace rules). If it's an imported library, the trusted surface remains \*only\* the Lean kernel's module resolution. Rebuild the Docker image.

3\. \*\*Detection.\*\*  
\*\*Prefix-detection is structurally unsafe.\*\* Routing core trust decisions based on \`startswith\` is a classic Confused Deputy vulnerability. An attacker/bug could prepend whitespace, a comment, or a Unicode BOM to the prelude. If it fails the prefix check, it routes to the normal single-declaration branch (which might fail safely, or might succeed if the attacker crafted a single-declaration exploit). If it passes a fuzzy prefix check, it routes incorrectly.  
\*Mandate:\* You must use an explicit, typed field in the expression/pipeline object (e.g., \`expr.is\_construction : Bool\`). The routing logic in \`discharge\` must branch on this typed field, never on string heuristics.

4\. \*\*Tri-edge binding.\*\*  
\*\*Unconditionally mandatory.\*\* As detailed in Q1, without tri-edge binding, you have a direct path to stamping Q.E.D. on a true theorem that lies about what it proved. The proof edge, faithfulness edge, and novelty edge must converge on the \*same\* canonical tuple. \`discharge\_construction\` must extract the parameters from the theorem AST, cross-reference them with the witness metadata, and abort on any mismatch. 

5\. \*\*Should we do this at all now?\*\*  
\*\*Defer. Absolutely defer.\*\*   
You are proposing to edit the \*single most critical line of code in the entire project\*—the sole writer of \`kernel\_verified\`—to add a new attack surface (multi-declaration parsing, literal injection, tri-edge binding) for a feature that has \*\*zero current utility\*\* (dormant infrastructure).   
\*Condition to greenlight:\* Only greenlight this edit when you have an actual, human-verified, record-beating witness in hand that \*requires\* promulgation. Right now, your audit-tier verification already runs the kernel check. The audit tier gives you 100% of the mathematical verification and 0% of the promulgation risk. The lack of a record beat is a producer problem, not a \`discharge\` problem. Do not risk the core invariant to build an empty promulgation highway.

6\. \*\*One thing we're likely getting wrong.\*\*  
You are conflating \*kernel verification\* with \*promulgation\*. You already have the kernel verifying constructions in the audit tier. The only thing \`discharge\_construction\` adds is setting the \`kernel\_verified=True\` flag so the daemon can autonomously promulgate it. You are risking the core invariant of the project ("nothing false is ever stamped") just to allow an autonomous daemon to publish a record without a human in the loop, for a record that doesn't exist yet. The risk/reward is completely inverted: you are taking maximum risk for zero current reward. Keep constructions in audit-tier until a human explicitly promotes one.

# Gemini 3.5 Thinking

## **Adversarial Witness Review: Construction PROOF-EDGE Expansion**

This review evaluates the proposed trust-surface expansion for the Leibniz daemon. It assumes a hard stance on maintaining absolute soundness: LLMs propose, mechanical checkers decide, and the single-writer integrity of LeanVerifier.discharge must not be compromised.

## **1\. Is the Trusted-Surface Expansion Sound?**

The proposed expansion from a single self-contained declaration to a "LOCKED prelude \+ one guarded theorem" is **unacceptable in its current form**. It relies on a critical misconception: that Lean 4 source text can be safely sanitized using string-level or regex-based structural guards.

### **The Strongest Concrete Attack: Macro/Command Redirection & Name Shadowing**

Lean 4 is a fully programmable, macro-driven meta-language. An attacker controlling the theorem's literals can bypass a text-based guard (like counting theorem and := or blocking def) in several ways:

* **Command Alternative Bypass:** The guard blocks def, axiom, and macro. An attacker can use abbrev, instance, inductive, or structure to inject arbitrary code, establish new types, or shadow definitions inside the locked prelude.  
* **Macro/Parser Exploitation:** Lean allows local notation and macro expansions. A malicious literal could manipulate Lean's parser or typeclass resolution mechanism inside the theorem definition to silently substitute a hollowed-out version of validCovering, even if the prelude text itself is byte-identical.  
* **Comment/String Literal Obfuscation:** Textual counts of theorem or := are trivially spoofed by hiding them inside multi-line comments (/- ... \-/) or string literals, tricking the pre-parser while presenting entirely different structures to the actual Lean compiler.

### **Mandated Guard**

If this path is taken, you must abandon textual filtering.  
**Mandate:** The guard must be an **AST-level invariant check** executed inside Lean's frontend. After parsing the combined source, you must programmatically inspect the resulting Environment object to verify it contains exactly *one* new TheoremVal constant, zero auxiliary axioms, and zero modification to the environment's existing macro definitions or typeclass instances.

## **2\. Inlined Locked Prelude vs. In-Image Library Module**

The substitution of an inlined prelude via check\_source to avoid a Docker infrastructure update introduces severe architectural fragility.

### **The Trade-Off**

* **Inlined Prelude:** Avoids modifying the operator's Docker deployment flow but forces the Lean compiler to re-parse and re-elaborate the prelude definitions for every single verification attempt. This opens up a Denial of Service (DoS) vector via typeclass resolution timeouts and maximizes the interaction surface between the untrusted theorem literals and the prelude text.  
* **In-Image Library Module (ADR 0045 Original):** Forces an upstream fix to the Docker build infrastructure but compiles the prelude into an immutable, binary .olean file.

### **The Bright Line**

**Inlining is a security regression.** The prelude must be a kernel-side library module imported by name (import Leibniz.Prelude). By isolating the helper definitions in a pre-compiled module, the environment is cleanly separated from the witness code. The witness source remains strictly a single declaration. If you do not have an in-repo Dockerfile to update the image, fix the repo infrastructure first—do not compromise the trust core to bypass a devops hurdle.

## **3\. Detection & Routing Safety**

### **The Danger of Prefix-Detection**

Using theorem\_src.starts\_with(LOCKED\_PRELUDE) to determine whether to route a file to the construction branch is highly vulnerable. If an attacker crafts a standard proof that happens to mimic or include the prelude as dead code or a comment, they can trick the system into routing a normal proof through the construction pipeline. Conversely, minor formatting or whitespace variations could misroute an actual construction out of its intended pipeline.

### **Mandated Design**

You must enforce an explicit, separate, strongly-typed metadata marker in the system's pipeline schema (e.g., proof\_tier: "standard" | "construction"). The routing logic inside LeanVerifier.discharge must read this explicit field.

## **4\. Tri-Edge Binding**

Theorem laundering is an existential threat to this architecture. If an LLM generates a mathematically valid construction for a trivial, known cell (e.g., a tiny covering design where $C(v,k,t) \\le B$), but the pipeline registers that proof edge against a highly valuable, record-beating tuple, the system will publish a false claim.

### **Mandated Binding Mechanism**

discharge\_construction cannot treat the theorem statement as an unexamined black box. It must explicitly bind the parameters:

1. The engine must programmatically inspect the type of the newly checked theorem using Lean's MetaM environment.  
2. It must extract the explicit argument expressions (the values for v, k, t, and size).  
3. It must assert an exact, hard-coded match against the canonical database tuple assigned to that verification job. If there is any mismatch, kernel\_verified must evaluate to False.

## **5\. Should We Do This at All Now?**

**Verdict: Defer Immediately.**  
Expanding the trusted surface of your sole kernel\_verified writer for **dormant infrastructure** is an anti-pattern. Because exact-solver escalation shows no reachable record beats currently exist, you are taking on active security debt and widening your primary attack surface for exactly zero operational payoff today.

### **Greenlight Conditions**

Keep constructions strictly at the **audit-tier** (where they are safely re-checked in isolation but never promulgated). You should only greenlight editing LeanVerifier.discharge when the following two conditions are met:

1. An audit-tier run produces a verified construction that genuinely beats a known record on a reachable cell.  
2. The Docker infrastructure is updated to support compiled library module imports, eliminating the inlined string-matching mechanism.

## **6\. One Thing You're Likely Getting Wrong**

You are treating **Lean 4 source code as a text-processing problem** rather than a compiler-frontend problem.  
Lean 4's syntax is so elastic and programmable that textual regexes, byte-prefix comparisons, and basic keyword counting are systematically bypassable. If you implement this change using string manipulation libraries instead of Lean's native Environment and Expr inspection APIs, malicious or corrupted LLM outputs will eventually find a way to trick your pre-parser into certifying an invalid theorem statement. Treat code as an abstract syntax tree, or do not trust it at all.  
Given that the current exact-solver measurements show no reachable record beats, what is the primary operational blocker preventing you from leaving this at the audit-tier while you fix the in-repo Dockerfile infrastructure?

# Qwen 3.7 Max

\*\*1. The Fatal Lean 4 Blind Spot (\`by decide\`)\*\*  
Your proposed mechanism relies on \`theorem ... := by decide\` to verify large combinatorial witnesses (e.g., covering designs, constant-weight codes) while keeping the TCB small. \*I know\* from Lean 4 kernel mechanics that \`by decide\` uses the kernel's internal reduction engine. For a non-trivial witness (e.g., checking all $\\binom{500}{2}$ pairs in a code), kernel reduction will predictably OOM or timeout. You cannot verify large finite objects in Lean 4 with pure \`by decide\` without using \`native\_decide\` (which expands the TCB to the C compiler/Lean's C backend) or writing a custom verified decision procedure. The prompt asks witnesses to attack the trust surface, but misses that the proposed mechanism is computationally non-viable for the exact use case it targets.  
\*Fix:\* You must explicitly surface this in the prompt. Ask the witnesses: "Given that pure \`by decide\` will OOM/timeout on large combinatorial witnesses, and \`native\_decide\` expands the TCB to the C backend, what is the actual TCB-safe mechanism for verifying large finite objects in Lean 4?"

\*\*2. The Parser vs. Regex Trap (Structural Guarding)\*\*  
The prompt specifies: \*"structural-guards the remainder to be exactly one \`theorem … := by decide\` … and exactly one \`theorem\`/one \`:=\`"\*. \*I guess with 99% confidence\* that the engineering team plans to implement this via string matching, regex, or simple token counting. This is trivially bypassed by placing \`theorem\` or \`:=\` inside a docstring (\`/-- theorem := \-/\`), a string literal, or a comment, allowing a malicious or hallucinating LLM to smuggle a second declaration or an \`axiom\`.   
\*Fix:\* Mandate in the prompt that the structural guard \*\*must\*\* operate on Lean's parsed \`Syntax\` AST, not raw text. String-level counting is a critical soundness vulnerability.

\*\*3. Critique and Rewrites of the 6 Questions\*\*

\*   \*\*Q1 (Trust Surface):\*\* Add the AST and OOM traps.   
    \*Rewrite:\* "What is the strongest concrete attack that yields a false \`kernel\_verified=True\`? Specifically, address: (a) bypassing the structural guard via docstrings/comments if implemented via string-matching rather than Lean's \`Syntax\` AST; (b) the computational reality that pure \`by decide\` will OOM/timeout on large witnesses, forcing a choice between hanging the kernel or expanding the TCB via \`native\_decide\`."  
\*   \*\*Q2 (Inlined vs. Imported):\*\* You missed the DoS/Compute vector. Inlining a 500-line prelude means the Lean kernel must re-parse, elaborate, and type-check the prelude from scratch for \*every single candidate\*.   
    \*Rewrite:\* "Is verifying a byte-identical inlined prelude acceptable given that it forces the kernel to re-elaborate the prelude for every candidate (a massive compute sink and DoS vector), versus the ADR's original in-image imported module? State the trade-off."  
\*   \*\*Q3 (Detection):\*\* Byte-identical prefix matching is notoriously brittle to line endings (CRLF vs LF), trailing whitespace, and Unicode normalization.   
    \*Rewrite:\* "Is byte-identical prefix detection safe, or is it too brittle to whitespace/encoding? Should we instead hash the normalized AST of the prelude, or require an explicit typed routing marker?"  
\*   \*\*Q4 (Tri-edge binding):\*\* Good question, but reiterate the AST requirement.  
    \*Rewrite:\* "Must \`discharge\_construction\` bind the theorem's parsed params to the canonical tuple via AST-level extraction (not regex) to prevent a true-but-different theorem from laundering a non-record?"  
\*   \*\*Q5 (Dormant Infrastructure):\*\* This is the most important question. Keep it as is, but frame it sharper.  
    \*Rewrite:\* "Given the promulgation payoff is contingent on a beat that does not exist, is editing the \*sole\* \`kernel\_verified\` writer for \*\*dormant\*\* infrastructure a YAGNI violation in a security-critical system? Should constructions stay audit-tier until a specific beat requires a specific verifier?"  
\*   \*\*Q6 (Warning):\*\* Keep as is.

\*\*4. The "Dormant Infrastructure" Trap (My honest call on Q5)\*\*  
You should \*\*defer\*\* this edit. Expanding the TCB and editing the sole \`kernel\_verified\` writer to support a generic "construction edge" when you have zero record-beating candidates is a textbook violation of minimal TCB principles. You are building a complex, fragile trust bridge to nowhere. When (and if) you actually find a record-beating candidate, you should build the \*specific, minimal\* verifier for that exact mathematical object, rather than a generic prelude-injection mechanism. Keep constructions audit-tier (verified but not promulgated) until the promulgation is strictly necessary.

\*\*5. One thing you're likely getting wrong\*\*  
You are treating the Lean kernel as a generic execution engine for large finite data. It is not. Lean is a proof assistant; its kernel is optimized for symbolic reduction, not crunching arrays of 10,000 integers. By trying to force large combinatorial witnesses through the kernel's native \`decide\` tactic to avoid expanding the TCB, you are creating a computational bottleneck that will silently kill your pipeline's throughput. The correct architecture for large finite witnesses is an external, untrusted fast-checker (e.g., in Rust/C++) that generates a \*small, symbolic\* proof certificate (like a trace or a hash) which the Lean kernel then verifies. 

Prioritized recommendation: Update the brief to explicitly surface the \`by decide\` OOM trap and the AST-vs-string parsing vulnerability, but strongly advise the operator to defer the \`discharge\` edit entirely until a specific, concrete record-beating candidate forces the design of a minimal, object-specific verifier.

# Nex AGI \- N2-Pro

Overall: this is a strong brief — clear stakes, good adversarial framing, and the right “human approves / no model decides” posture. I’d tighten it in a few places before sending it out.

\#\# Main feedback

\#\#\# 1\) Make source ownership explicit  
The biggest missing precision is this:

\- \*\*The witness should not control raw \`theorem\_src\`.\*\*  
\- The witness should provide \*\*only the finite witness parameters\*\*.  
\- The system should synthesize \`theorem\_src\` as:  
  \- locked prelude bytes  
  \- fixed theorem template  
  \- inserted numeric literals / tuple

Right now “Only the theorem’s literals are witness-controlled” is close, but I’d make it unambiguous. If raw source is accepted from the witness, the guard has to be much stronger.

\#\#\# 2\) Replace prefix/token counting with a parser-based grammar  
The proposed guard should be something like:

\- exact hash match for the locked prelude  
\- parse the whole source with Lean’s parser  
\- require \*\*exactly one theorem declaration after the prelude\*\*  
\- theorem body must be exactly \`by decide\`  
\- no \`import\`, \`axiom\`, \`constant\`, \`opaque\`, \`unsafe\`, \`native\_decide\`, \`admit\`, \`sorry\`, macros, extra commands  
\- theorem statement must parse to the expected predicate family and canonical tuple  
\- \`\#print axioms\` / equivalent must show no axioms  
\- run \`check\_source\` in a clean, pinned Lean env with timeouts

In other words: \*\*AST guard, not regex/counting guard.\*\*

\#\#\# 3\) Use an explicit construction marker, not prefix detection alone  
Prefix matching is okay as a secondary sanity check, but I would not make it the routing predicate.

Better:

\- explicit enum / typed field like \`proof\_kind \= construction\`  
\- plus locked-prelude hash  
\- plus parser validation

That avoids misrouting in either direction.

\#\#\# 4\) Bind the proof edge to the exact theorem, not just the proof  
The most important missing binding is:

\- predicate family  
\- canonical tuple  
\- theorem hash  
\- prelude hash  
\- Lean version  
\- witness hash / provenance

A false theorem can still be kernel-verified if it proves the wrong cell. So the proof edge should attest: “this exact theorem, with these exact params, passed this exact prelude.”

\#\#\# 5\) Inlined prelude vs library module  
Your trade-off framing is good. My take:

\- \*\*Inlined locked prelude is acceptable\*\* if it is immutable, hash-pinned, and checked in a clean environment.  
\- A library module is \*\*not automatically safer\*\* unless it is equally pinned and auditable.  
\- Bright line: no mutable imports, no axioms, no native/unsafe path.

\#\#\# 6\) Greenlight vs defer  
I’d greenlight only if:

\- the construction branch is feature-gated  
\- there is a real beat candidate or near-term need  
\- the guard is parser-based and hash-bound  
\- the proof edge is bound to the exact theorem \+ canonical tuple

Otherwise, defer. Dormant infrastructure is only worth it if the implementation is very small and well-contained.

\#\# One likely blind spot  
The thing you’re most likely getting wrong is \*\*theorem-statement laundering\*\*.

A theorem can be perfectly kernel-verified and still attest the wrong cell if the statement is not bound to the witness tuple. That’s the attack I’d focus on.