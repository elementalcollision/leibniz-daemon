# HANDOFF-NEXT — start here for a new Leibniz session

> This is the launchpad for a **fresh session**: continue the verification‑amplification loop
> and explore new concepts and the Leibniz ontology. It is deliberately self‑contained — a
> session with no prior memory can read this file and be productive. For the rung‑by‑rung
> porting history see the older [`HANDOFF.md`](HANDOFF.md); for trust rules see
> [`CLAUDE.md`](CLAUDE.md); for the mission see [`README.md`](README.md).

---

## 0. Read me first (operational)

- **The repo is now PUBLIC and hardened** (ADR 0049). Its history was rewritten on
  2026‑07‑06 to purge a committed `site/node_modules/` (~115 MB). **All commit hashes changed.**
- **Start from a fresh clone of `main`.** Any old local clone / worktree is on pre‑purge
  history and will diverge. Either:
  ```bash
  git clone https://github.com/elementalcollision/leibniz-daemon.git   # cleanest
  # or, in an existing clone:  git fetch origin && git checkout main && git reset --hard origin/main
  ```
- **PRs are merged by the operator only** (branch protection + code‑owner review + the
  required `invariants` CI check). You open PRs; you never merge to `main`, never push to
  `main`, never force‑push.
- **Only `main` exists** — stale feature branches were deleted. Branch each unit of work off
  `origin/main`.

---

## 1. What Leibniz is (the ontology)

> **Codex Calculemus is a reading‑room for the ledger of an autonomous theorem daemon,
> Leibniz. The daemon surveys a frontier, conjectures, formalizes each claim into Lean, and —
> where the claim survives the cheap gates — asks the kernel to *calculate* whether it holds.
> This site renders the laws that survived. It is read‑only, and it rebuilds whenever a new
> law is published.**

The one property that justifies the whole project:

> **LLMs propose; only mechanical checkers — the Lean 4.31 kernel, Z3, and exact
> rational / finite‑field / exact‑enumeration decision procedures — decide.** No "the proof
> looks right" ever reaches a promulgated law.

The daemon's vindicated role in practice is **verification‑amplification**: independently
*re‑deciding* recently published mathematical results with an exact mechanical decider, and
publishing the ones that survive as *Calculemus cycles*. Amplification comes in tiers —
kernel‑decided (Lean `decide`, axiom‑clean), exact‑procedure (finite‑field / exact‑rational /
exact enumeration), and cross‑kernel (the same finite core re‑decided in a second kernel,
Rocq/Coq). All sit behind the unchanged trust boundary.

---

## 2. The trust boundary — never weaken it

These are enforced by `leibniz/trust.py` and `tests/test_invariants.py` /
`tests/test_boundary_guards.py` / `tests/test_kernel_verified_writers.py`, and guarded at the
merge path by `CODEOWNERS` + branch protection. If a change you are about to make would
require editing those tests to pass, **stop — you are weakening the boundary.**

1. `Demonstratio.kernel_verified` is set **only** inside
   `leibniz/verifiers.py::LeanVerifier.discharge`; the proof edge is always
   `TrustTier.MECHANICAL`.
2. Never promulgate unless `TrustPolicy.validate_path` passes (called from
   `VerificationGate.is_promotable`).
3. LLMs occupy only the proposal roles; the sole place LLM judgment reaches a promulgated law
   is the budget‑bounded OPEN_FORM faithfulness fallback.
4. Novelty is settled by retrieval + a decision procedure, never by a judge.
5. `native_decide` is forbidden; `sorry`, admitted lemmas, and unaudited axioms are never
   accepted as kernel decisions. `#print axioms` should show only Lean's canonical trusted
   axioms (`propext`, and at most `Classical.choice` / `Quot.sound`) — **never `sorryAx`**.
6. New backends (Coq/Isabelle, ADR 0048) are **report‑only**: they may *observe* a kernel but
   must never set `kernel_verified`, mint a proof edge, or import `leibniz/trust.py`. Promotion
   is deferred and operator‑gated.

`ruff check .` must be clean; `pytest -q` green; the CI `invariants` job must never pass
vacuously (it asserts ≥ 11 tests collected).

---

## 3. Current state (as of 2026‑07‑06, late)

- **Post‑R6 optimization phase.** The rung climb R1→R6 is substantially complete (real Lean
  4.31 kernel via Docker; faithfulness + Z3; novelty retrieval; proposal models + ADR 0029
  repair panel; KFM / MAP‑Elites archive; the *Calculemus* reading‑room + operator publish
  gate). Binding constraint is **novelty/discovery yield**, not prover reach or the trust
  boundary. Live plan: `docs/optimization-roadmap.md`.
- **Ledger now runs to Cycle 34.** The most recent session shipped **Cycles 28–34** (all
  merged to `main`; trust boundary byte‑identical throughout; every kernel theorem
  `#print axioms`‑clean — `[propext]` at most, never `sorryAx`):

  | # | Result | Domain (new) | Decider |
  |---|---|---|---|
  | 28 | Minimal double blocking sets 3q−1 in PG(2,q) — **refutes a 1984 Hill conjecture** | Finite geometry | Lean `decide` |
  | 29 | PΓU(5,3) on H(4,9) non‑spreading — base case of the **open** Conjecture 4.1 | Finite polar spaces | Lean `decide` |
  | 30 | Markoff (1,1,1) 2‑adic divisibility → connected cage (two routes; Mersenne to 2³¹−1) | Arithmetic geometry | Lean `decide` |
  | 31 | Kissing number **k(19) ≥ 11948** (record, beats Cohn–Li by 256) | Sphere packing | Lean `decide` (BST min‑dist) |
  | 32 | Complex Hadamard matrix of **order 94** (previously open) | Complex Hadamard matrices | Lean + exact ℤ/ℤ[i] |
  | 33 | Low‑degree ovoids of Q⁺(7,q): Kantor at q=4, **fails at q=8** | Finite geometry (ovoids) | Lean `decide` (in‑kernel GF(2ʰ)) |
  | 34 | Simplest Kochen–Specker set (14 bases) — **disproof of a 2025 PRL conjecture** | Quantum contextuality | Lean `decide` (in‑kernel Z[ω] + backtracking UNSAT) |

  Highlights: a **record** (kissing k(19)), an **open‑existence** resolution (complex Hadamard 94),
  a **published‑conjecture disproof** (Cabello KS, fully in‑kernel incl. the uncolorability UNSAT via a
  ~1.2k‑node backtracking search), and three separate **faithfulness catches** (PGU origin non‑degeneracy;
  a kissing Table‑1 typo; a Cabello dropped‑minus‑sign) — the exact deciders doing real work.
- **Codex publication.** `elementalcollision/codex-calculemus` PR **#3** (`publish-cycles-16-31`, now
  extended to **16–34**) backfills the public ledger + `public/artifacts/` to a contiguous **1–34** —
  **awaiting operator merge** (publication stays operator‑gated). Mechanics: each cycle's
  `scripts/export_*_cycle.py` fragment → `ledger/calculemus.json` `cycles[]`; cert copied to
  `public/artifacts/cycle_0000NN/` with `sha256` pinned; `node scripts/sync-ledger.mjs` regenerates the
  Astro content. `laws[]`/`held_back[]` are untouched.
- **Deferred + queued targets — build these next** (from an adversarially‑vetted survey; all distinct
  from the ledger). The immediate one is **deferred, not rejected**:
  - **srg(1666,105,0,7) non‑existence** (Belousova–Makhnev–Tokbaeva 2026, *Vestnik Perm. Univ.*,
    DOI 10.17072/1993‑0550‑2026‑1‑29‑34; PDF: `press.psu.ru/index.php/Math/article/view/11312/7961`,
    Russian). **Deferred** because it is a proof‑reconstruction, not a self‑certifying witness: the
    parameter set is *feasible* by every standard bound (integer eigenvalues 7,−14; multiplicities
    1105,560), so non‑existence rests on the paper's **triple‑intersection‑number** argument (Vidali /
    Coolsaet–Jurišić method) for the bipartite DRG with array `{105,104,98,7,1;1,7,98,104,105}`,
    terminating in a single non‑negativity contradiction. Needs the Russian PDF read carefully; weak
    faithfulness anchor — give it a focused session, don't force it.
  - Other strong survey‑2 finalists still open: **shifted‑square Frobenius number** closed form
    (Hyun–Song, arXiv:2605.25542; self‑checking exact Apéry‑set census — cleanest fresh domain),
    **permutation‑trinomial disproof** (Bouyacoub–El‑Baz–Kihel, arXiv:2603.03368; one exact F₃₁ collision),
    **vertex‑minor Ramsey R_vm(4)=11** (Bae, arXiv:2604.13434; disproof of the 2ᵏ−1 bound — *scope to the
    lower‑bound witness only*), the **Shilla b=6** five‑array non‑existence batch (Makhnev et al.,
    UMJ 2025), and **cyclic PG(3,q) ovoids** (Abdukhalikov–Ball–Ho–Popatia, arXiv:2410.04126; F₄₀₉₆ tower).
- **Reusable pattern established this session (copy it):** for a target reducible to a small finite object,
  the kernel can compute the *field/structure itself* rather than baking tables — e.g. **in‑kernel GF(2ʰ)**
  multiplication (carryless multiply‑and‑reduce from the irreducible; Cycle 33), **in‑kernel GF(q²)** with
  Frobenius = X‑coord negation (Cycle 29), **Eisenstein ℤ[ω]** arithmetic (Cycle 34), and a **bounded
  backtracking search** for finite UNSAT / KS‑uncolorability when the search tree is small (~10³ nodes;
  Cycle 34) — this dodges the 2ⁿ brute‑force *and* the dense‑matrix `decide` wall. When a dense product is
  unavoidably large (e.g. 94×94 in Cycle 32, or an 819k‑pair census in Cycle 31), reduce via structure
  (circulant → first‑row autocorrelation) or push it to the exact procedure and kernel‑attest the core.
- **Prior run — Calculemus Cycles 17–27** (each a `scripts/verify_*.py` +
  a downloadable cert under `docs/crt/` + tests + a results doc under `docs/results/` + a
  `scripts/export_*_cycle.py`), spanning eleven fresh domains:

  | # | Result | Domain | Decider |
  |---|---|---|---|
  | 17 | Cross‑kernel Guo–Krattenthaler q‑divisibility | Number theory | Rocq |
  | 18 | Skew‑Hadamard difference family (1252) | Design theory | exact GF(5⁴) |
  | 19 | Cross‑kernel Erdős‑707 Sidon core | Combinatorics | Rocq |
  | 20 | **Disproof of Stanley's 1985 dimer conjecture** (k=13) | Combinatorics | Lean |
  | 21 | **Disproof of Brualdi–Friedland–Pothen** (Aliabadi) | Comb. matrix theory | Lean |
  | 22 | **Disproof of Ziegler's cross‑polytope conjecture** (Kaibel–Pokutta) | Discrete geometry | Lean |
  | 23 | **Disproof of Mason's log‑concavity conjecture** (Larson) | Matroid theory | Lean |
  | 24 | First EFX‑nonexistence counterexample (Akrami et al.) | Fair division | exact census |
  | 25 | Cap‑set subgroups of finite fields (SET / EvenQuads) | Additive combinatorics | Lean |
  | 26 | Steiner S(2,8,225) & S(2,9,289) exist (Hetman) | Design theory | Lean |
  | 27 | Sun's determinant congruence (Zhang–Yang) | Determinantal number theory | Lean |

  Four kernel‑attested **disproofs of published conjectures**, two resolutions of open
  existence questions, plus cross‑kernel and exact‑procedure amplifications. All merged; trust
  boundary byte‑identical throughout.

---

## 4. The working loop (how a cycle gets built)

1. **Survey** a fresh frontier for a target (spawn a background research agent; see the filters
   in §5). Vet the returned candidates yourself.
2. **Get ground truth from the primary source** — fetch the paper (arXiv abstract → HTML →
   *read the PDF yourself* for exact data). Never trust an LLM's transcription of a matrix,
   table, or graph.
3. **Verify from first principles** with an exact decider (Python: exact ℚ / GF(pᵏ) / exact
   enumeration / Berlekamp–Massey). Reproduce any statistic the paper reports (an f‑vector, a
   "272 of 5796", a Whitney number) — a match is a strong *faithfulness* check on your data.
4. **Kernel‑attest** the finite core in Lean 4.31 via plain `decide` if it fits the budget
   (§6). Add a **negative control** (a corrupted witness the kernel must *reject*).
5. **Package** the standard five artifacts + branch off `origin/main`, commit, push, open a PR.
   Publish it as the next Calculemus cycle via the exporter.

**File pattern for a cycle** (copy an existing one, e.g. `verify_capset_subgroups.py` /
`verify_steiner_designs.py`):

```
scripts/verify_<name>.py         # producer + verifier; builds & self-checks the cert
docs/crt/<name>.lean             # the downloadable Lean certificate (plain decide)
tests/test_<name>.py             # CI-safe exact checks + cert well-formedness; Docker-gated kernel leg
docs/results/<name>-YYYY-MM-DD.md# the results doc (honest scope!)
docs/results/<name>_verification.json
scripts/export_<name>_cycle.py   # emits the Calculemus cycle fragment (producer only)
```

The `cycle_payload(...)` / `downloadable_artifact(...)` helpers live in
`leibniz/calculemus_site.py`; audit/verification/refutation kinds MUST cite references
(`requires_references`).

---

## 5. Hard‑won playbook (read before picking a target)

**Survey filters — rank candidates by all three:**
- **(A) Cheap kernel core.** Prefer a target whose exact core is *one small object*: a ≤ 8×8
  determinant, one polynomial identity / squarefree / resultant check, a modest‑order
  recurrence, one big‑integer inequality, a few thousand exact comparisons. Estimate the
  `decide` cert size up front.
- **(B) Exact, unambiguous, obtainable data.** Best: printed in the paper, or reconstructible
  from stated axioms (e.g. "the fourth powers of GF(81)"). **Avoid**: data only in a large
  external artifact (SAT/DRAT dumps), data given only as a *schematic figure* needing
  ambiguous graph reconstruction, and any numerically‑certified *interval* (not an exact
  object).
- **(C) Credible provenance.** Peer‑reviewed / established authors. Avoid self‑published,
  AI‑generated notes whose statements aren't independently corroborated.

**Faithfulness traps that actually bit this run — learn from them:**
- The survey's paraphrase can be *wrong*. (Sun's congruence was stated as an "iff"; it is
  one‑directional. Always fetch the exact theorem.)
- Data can be hidden in a 198 MB artifact (EFX) — pull it via WebDAV `PROPFIND`, extract just
  the small file, read it yourself.
- Data can be only in schematic figures with parallel edges (S₁₀/S₁₂ edge‑colouring) — those
  are unreconstructible; drop them.
- Beware over‑claiming *your own* observations (a "vₚ = 2 always" that fails at p=11,13). Ship
  only what you verified.

**Lean `decide` patterns & walls:**
- Compact `List.foldl` / `List.zipWith` encodings reduce where a *flat* big‑int conjunction
  walls (~1000–1600 terms). `detN` on **literal** matrices is fast; on *lazily‑computed*
  matrices it blows up — feed literals or split.
- Large certs: split into **several theorems in one file**, or run each theorem in its **own
  REPL exchange** (cumulative memory pressure kills a monolithic `decide`).
- `X == 0 = true` **mis‑parses** — write `(X == 0) = true`.
- `#print axioms` reporting `[propext]` is fine (canonical trusted axiom); the negative
  control appearing as `sorryAx` proves your check is discriminating.
- The `decide`/big‑literal wall (order‑N PSD blocks) is documented in **ADR 0047** and the
  `large-block-psd-*` docs — consult before attempting a heavy in‑kernel census.

**Environment gotchas:**
- An editable install (`pip install -e`) can point at a *different* checkout than your cwd; in
  scripts, `sys.path.insert(0, <repo_root>)` and run tests with explicit paths.
- Lean REPL: `from leibniz.backends.lean_repl import LeanReplBackend, available`;
  `bk._run(src, ("Mathlib...",))`; header `set_option maxHeartbeats 0` /
  `set_option maxRecDepth 1000000`; strip `import` lines. If it reports "unavailable",
  clear orphaned containers:
  `docker ps -aq --filter ancestor=leibniz-lean-repl:v4.31.0 | xargs -r docker rm -f`.
- Cross‑kernel Coq: `rocq/rocq-prover:9.0`, `rocq compile` + `rocqchk -o` axiom audit,
  authenticated by an unforgeable nonce (`leibniz/backends/coq_docker.py`). Report‑only.
- `docker`/OrbStack must be up for any kernel leg; `docker` unavailable → return `None`
  (unavailable, not rejected).

---

## 6. New explorations — concepts & ontology to push on

The binding constraint is discovery yield, so most value is in **new targets** and in
**deepening the ontology**. Candidate directions:

**Untouched target domains** (avoid the ledger's covered set — coding theory, monomial‑ideal
normality, GK q‑divisibility, dimer recurrence, Sidon/skew‑Hadamard, BFP, Ziegler, Mason, EFX,
cap sets, Steiner, Sun determinant):
- spectral / algebraic graph theory (equiangular lines, SRG feasibility with an explicit
  adjacency matrix, eigenvalue interlacing, Ramanujan certificates);
- finite geometry (ovoids, spreads, blocking sets, arcs, generalized‑quadrangle configs);
- quadratic forms & lattices (explicit Gram matrices, theta‑series identities, kissing configs);
- Diophantine / arithmetic geometry (elliptic‑curve rank/torsion finite checks, permutation
  polynomials over F_q, Markoff‑triple orbits);
- quantum info feasibility (small MUB / SIC with exact or algebraic entries);
- numerical / affine semigroups (Frobenius, Wilf‑type inequalities).

**Ontology / concept work** (the part you specifically asked to explore):
- **Formalize the amplification tiers.** Make "kernel‑decided vs exact‑procedure vs
  cross‑kernel" a first‑class attribute of a cycle, with an explicit *confidence ladder*, so
  the reading‑room can render *how* a law survived, not just that it did. (ADRs 0017/0048 are
  the anchor points.)
- **Origination vs amplification.** Every cycle so far *re‑decides* a published result. Can the
  daemon *originate* — conjecture a genuinely new finite fact (e.g. a new small design, a new
  cap, a new counterexample) and kernel‑decide it — while staying inside the trust boundary?
  This is the sharpest open question for the ontology.
- **Novelty against the ledger.** Add a mechanical dedup/novelty check so a new target is
  provably distinct from Cycles 8–27 (retrieval + a decision procedure, never a judge — see
  invariant #4).
- **Break the kernel‑reach wall** (ADR 0047): proof‑term certificates, using Mathlib lemmas
  instead of raw `decide`, or a certificate format that scales the PSD‑block / large‑census
  cases the exact procedure currently carries alone.
- **Promote the report‑only backends.** Coq/Isabelle promotion (verifier + registry +
  target_checker, and the `KERNEL_PRODUCERS` edit) is designed but deferred and operator‑gated
  (ADR 0048). A cross‑kernel tier as a formal confidence signal is the natural next step.
- **The reading‑room** (`site/`, Astro): render the new tiers, the negative controls, and the
  provenance chain for each law.

---

## 7. Commands & map

```bash
pip install -e ".[verify,propose,dev]"   # core is stdlib-only; extras add Z3/Lean/LLM
pytest -q                                 # trust invariants must stay green
ruff check .                              # lint (repo is ruff-clean)
python demo.py                            # one deterministic circadian cycle
```

- **Trust core:** `leibniz/{trust,verifiers,types,propositio,pipeline}.py`,
  `leibniz/gates/{faithfulness,novelty,verification}.py`, `tests/test_invariants.py`.
- **Cycle machinery:** `leibniz/calculemus_site.py`; producers in `scripts/`; certs in
  `docs/crt/`; results in `docs/results/`.
- **Backends:** `leibniz/backends/{lean_repl,coq_docker,isabelle_docker}.py`.
- **Decisions:** `docs/adr/` (charter 0001; faithfulness 0002; cross‑kernel deciders 0048;
  PSD/decide wall 0047; public hardening 0049). Live plan: `docs/optimization-roadmap.md`.
- **Governance:** `LICENSE.md` (PolyForm Noncommercial 1.0.0 — source‑available),
  `SECURITY.md`, `CONTRIBUTING.md`, `.github/CODEOWNERS`.

*Calculemus.* — LLMs propose; the kernel decides.
