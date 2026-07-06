# Leanstral 1.5 × Leibniz — Proof-of-Concept

A minimal, runnable demonstration that **Leanstral 1.5** drops into the [Leibniz][leibniz] theorem
daemon as a kernel-checked prover with **zero code changes** — it proposes Lean 4 proofs; the Lean
4.31 kernel decides.

- **`leanstral_leibniz_poc.py`** — the runnable PoC (Leanstral proposes → kernel + axiom-clean bar decides).
- **`leanstral-leibniz-post.md`** — a short write-up with a real run, the ensemble/consensus result, honest reach numbers, and two API notes.

## Run

```bash
git clone https://github.com/elementalcollision/leibniz-daemon && cd leibniz-daemon
pip install -e ".[verify,propose]"
export MISTRAL_API_KEY=...          # a Mistral key with Labs models enabled
                                    # (admin.mistral.ai/plateforme/privacy)
# Docker must be running (the pinned Lean 4.31 kernel REPL image).
python /path/to/leanstral_leibniz_poc.py
```

## What it shows

Leanstral drafts proofs; each is re-checked by the Lean kernel under Leibniz's real bar — the proof
must **elaborate** *and* be **axiom-clean** (only Lean's canonical axioms; never `sorry`, never
`native_decide`). Valid proofs are accepted; a wrong draft or a compiler-trusting `native_decide`
shortcut is refused. **LLMs propose; only the kernel decides.**

[leibniz]: https://github.com/elementalcollision/leibniz-daemon
