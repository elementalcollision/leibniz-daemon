# Leanstral 1.5, kernel-checked: a zero-code integration in the Leibniz theorem daemon

**Leibniz** is an autonomous theorem daemon built around one non-negotiable rule:

> **LLMs propose; only mechanical checkers — the Lean 4.31 kernel, Z3, and exact decision
> procedures — decide.** No "the proof looks right" is ever trusted.

We added **Leanstral 1.5** as a prover. It took **zero lines of code** — and it slotted straight
into the daemon's kernel-checked, N+1-consensus prover ensemble. Here's the whole thing.

---

## 1. The integration is three env lines

Leanstral speaks the OpenAI chat-completions API, so Leibniz's existing per-model gateway routing
reaches it by **config alone** — no new provider class, no touch to the trust core:

```bash
MISTRAL_API_KEY=<your key>
LEIBNIZ_GATEWAY_MISTRAL_URL=https://api.mistral.ai/v1/chat/completions
LEIBNIZ_PROVER_MODELS=labs-leanstral-1-5@mistral
```

That's it. `labs-leanstral-1-5@mistral` becomes a first-class prover in the ensemble, and every
draft it produces is re-verified by the Lean kernel before anything is trusted.

## 2. Propose → decide

The core loop is tiny: Leanstral drafts a Lean 4 proof; the kernel checks it against
`theorem := proof` **and** enforces Leibniz's axiom-clean bar (only Lean's canonical axioms — never
`sorry`, never `native_decide`).

```python
os.environ.setdefault("LEIBNIZ_GATEWAY_MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions")
os.environ.setdefault("LEIBNIZ_PROVER_MODELS", "labs-leanstral-1-5@mistral")

from leibniz.assembly import prover_ensemble
from leibniz.backends.lean_repl import LeanReplBackend
from leibniz.consensus import normalize_proof
from leibniz.types import Role

leanstral = prover_ensemble()[0]                 # labs-leanstral-1-5, via the Mistral gateway
kernel    = LeanReplBackend(timeout_s=180)

for src in THEOREMS:
    draft   = normalize_proof(leanstral.propose(Role.PROOF_DRAFT, src))  # Leanstral PROPOSES
    ok, why = kernel_accepts(kernel, src, draft)                          # the kernel DECIDES
    print(("✓ ACCEPT" if ok else "✗ REJECT"), src, "—", why)
```

A real run (full script: `leanstral_leibniz_poc.py`):

```
proposer : labs-leanstral-1-5
decider  : Lean 4.31 kernel + Leibniz axiom-clean bar (no native_decide, no sorry)

✓ ACCEPT  theorem t1 (n : Nat) : n + 0 = n
         kernel-verified, axiom-clean (propext)
         Leanstral proposed: 'by induction n with | zero => rfl | succ n ih => simp [ih]'

✓ ACCEPT  theorem t2 (l : List Nat) : l.reverse.reverse = l
         kernel-verified, axiom-clean (propext)
         Leanstral proposed: 'by induction l with | nil => rfl | cons x xs ih => simp [ih]'

✓ ACCEPT  theorem t3 (n : Nat) : n ≤ 2 * n
         kernel-verified, axiom-clean (propext, Classical.choice, Quot.sound)
         Leanstral proposed: 'by induction n with | zero => exact Nat.zero_le _ | succ n ih => ... omega ...'

✗ REJECT  theorem t4 : (2 : Nat) + 2 = 4
         proof uses `native_decide` (trusts the compiler, not the kernel — forbidden)
         Leanstral proposed: 'by native_decide'

✗ REJECT  theorem t5 (a b : Nat) : a + b = b + a
         kernel rejected the proof (does not elaborate)
         Leanstral proposed: 'by induction' a with a ih · simp · simp [add_succ, ih]'
```

Three real, axiom-clean induction proofs accepted — and **two rejections that show the guardrail
doing its job**:

- **`2 + 2 = 4` → rejected.** Leanstral reached for `native_decide`. Lean *elaborates* it, but
  `native_decide` trusts the compiled kernel (`Lean.ofReduceBool`), not the trusted kernel — so
  Leibniz's axiom-clean bar refuses it. Correct proof, wrong trust footprint.
- **`a + b = b + a` → rejected.** A wrong draft that simply doesn't elaborate.

Neither is trusted. That's the whole point: **a fast prover you can rely on precisely because
nothing rides on the model being right.**

## 3. As an ensemble voter (N+1 consensus)

We wired Leanstral as the *preferred* voter, ahead of DeepSeek-Prover-V2 and Goedel-Prover-V2, under
N+1 consensus (a claim promulgates only when ≥2 **distinct** models each produce a kernel-verified,
axiom-clean proof). Running the real cascade:

| goal | Leanstral | DeepSeek-V2 | Goedel-V2 | opus (witness) | consensus |
|---|:--:|:--:|:--:|:--:|:--:|
| `n ≤ 2*n` | ✓ (lead) | ✗ | ✗ | ✓ | **reached (2/2)** |
| `Even(n*(n+1))` | ✗ | ✗ | ✗ | ✓ | not reached (1/2) |

On the first goal Leanstral produced the **lead** proof and DeepSeek/Goedel missed it; on the second
Leanstral missed and the witness covered it. Different provers catch different goals — which is
exactly why Leanstral belongs *in* the ensemble.

## 4. Reach — honest numbers

On a graded 12-goal set through the daemon's real draft→repair loop:

- **pass@1 ≈ 58–66%**, best-of-5 ≈ 66% (fast — ~0.7 s/draft).
- Genuinely *proves*: it wrote a ring-based induction for `Even(n·(n+1))` and closed
  `∑_{i<n}(2i+1) = n²` cleanly — not just `simp`/`decide`.
- Blind spots (systematic, not sampling noise): it reproducibly botches `a + b = b + a`, and didn't
  one-shot the hard modular goals like `n(n+1)(2n+1) % 6 = 0`.

Bottom line: a strong, fast one-shot Lean prover — best deployed as one voter among several under
kernel-checked consensus, not run alone.

## 5. Two notes you might find useful

- **`temperature = 0` → HTTP 400.** `{"message":"top_p must be 1 when using greedy sampling.", "code":"3054"}`.
  Greedy decoding needs `top_p = 1`. (Leibniz's default path doesn't set `temperature`, so it's
  unaffected — but it surprised our best-of-k harness.)
- **Labs models are off by default.** The first call returned `403 labs_not_enabled`; enabling Labs at
  `admin.mistral.ai/plateforme/privacy` fixed it.

## Try it

```bash
git clone https://github.com/elementalcollision/leibniz-daemon && cd leibniz-daemon
pip install -e ".[verify,propose]"
export MISTRAL_API_KEY=...      # Labs models enabled
# Docker running (pinned Lean 4.31 kernel image)
python leanstral_leibniz_poc.py
```

Nice model — fast, genuinely proving, and it dropped in without a single line of new code. The Lean
kernel keeps the honesty; Leanstral brings the reach.
