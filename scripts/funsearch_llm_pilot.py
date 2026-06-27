"""LLM FunSearch pilot for CWC records — the billable proposer, wired to the sandbox harness.

Operator-authorized (GO: small CPU-first tranche). An LLM proposes construction PROGRAMS; each runs in
the UNTRUSTED-CODE SANDBOX (scripts/funsearch_sandbox.py); fitness is verify_cwc-valid code size;
novelty is judged against the post-Rosin oracle floor; and a candidate beat is RE-CHECKED by the Lean
kernel (scripts/cwc_check.py). Nothing is promulgated — a kernel-verified beat is recorded for the
ADR 0040 carve-out + operator review.

Hard caps + pre-registration: docs/funsearch-pilot-preregistration.md (+ the machine-readable targets
in docs/results/funsearch_pilot_targets.json). `--fake` swaps in a deterministic no-LLM proposer so the
ENTIRE pipeline (proposer -> sandbox -> evaluator -> kernel) can be validated with ZERO spend.

Trust: the LLM only PROPOSES; the kernel + automated oracle DECIDE. The pilot never sets
kernel_verified and never promulgates. Programs are untrusted and never run outside the sandbox.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import cwc_table_oracle as ora  # noqa: E402
import funsearch_sandbox as sandbox  # noqa: E402
from funsearch_loop import effective_best_known  # noqa: E402

TARGETS = _ROOT / "docs" / "results" / "funsearch_pilot_targets.json"

_SYSTEM = (
    "You write Python construction functions for binary constant-weight codes. A constant-weight code "
    "A(n,d,w) is a set of w-subsets of {0..n-1} (codewords) with pairwise Hamming distance >= d, i.e. "
    "any two codewords share at most w - ceil(d/2) elements. Output ONLY one Python code block defining "
    "`construct(n, d, w)` that RETURNS a list of codewords (each a list/tuple of w distinct ints in "
    "[0,n)), as LARGE as possible. CRITICAL: the sandbox is CPython 3.12 with the STANDARD LIBRARY "
    "ONLY — there is NO numpy, scipy, networkx, sympy, or any third-party package; importing one "
    "raises ImportError and scores 0. Use only stdlib (e.g. itertools, random, math). No prose, no "
    "I/O, no file/network access. You PROPOSE; a verifier and the Lean kernel DECIDE — never claim "
    "correctness."
)

_CODE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def extract_program(text: str) -> str:
    """Pull the Python program from an LLM reply. Prefers the LAST fenced code block that defines
    `construct` (handles replies with explanation + multiple blocks, or a reasoning trace followed by
    the final program); falls back to the last block, then the raw text."""
    text = text or ""
    blocks = _CODE_RE.findall(text)
    if blocks:
        for b in reversed(blocks):
            if "def construct" in b:
                return b.strip()
        return blocks[-1].strip()
    return text.strip()


def _parse_completion(data: dict) -> str:
    """Robustly pull the assistant text from an OpenAI/OpenRouter chat response. Handles: an error
    object; an empty `choices`; and a null `content` (common for REASONING models that put output in
    `reasoning`/`reasoning_content`, or that hit the token cap mid-reasoning). Raises a descriptive
    error (incl. finish_reason) rather than letting a None reach the regex — that null-content case is
    exactly what voided the first pilot run."""
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"API error: {str(data['error'])[:300]}")
    choices = (data or {}).get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices in response: {str(data)[:200]}")
    ch = choices[0]
    msg = ch.get("message") or {}
    content = msg.get("content") or msg.get("reasoning") or msg.get("reasoning_content")
    if not content:
        raise RuntimeError(f"empty content (finish_reason={ch.get('finish_reason')}); the model may be "
                           "a reasoning model that exhausted the token budget — raise --max-tokens or "
                           "choose a non-reasoning code model via LEIBNIZ_FUNSEARCH_MODEL")
    return content


def _prompt(n: int, d: int, w: int, floor: int, exemplars: list[tuple[str, int]]) -> str:
    lines = [f"Task: construct(n={n}, d={d}, w={w}). The current record is {floor}; produce MORE than "
             f"{floor} valid codewords (a genuine improvement). Pairwise intersection must be <= "
             f"{w - (d + 1) // 2}."]
    if exemplars:
        lines.append("\nHere are prior programs and the code SIZE they achieved; write a NEW, "
                     "different, better construction (exploit structure — cyclic/affine shifts, "
                     "difference families, recursive/greedy-with-backtracking, etc.):")
        for src, score in exemplars:
            lines.append(f"\n# achieved {score} codewords:\n{src}")
    else:
        lines.append("\nWrite a first construction. Exploit algebraic/combinatorial structure, not just "
                     "naive greedy.")
    return "\n".join(lines)


class FakeProposer:
    """Deterministic no-LLM proposer for no-spend validation: cycles through a few canned programs
    (a greedy and a cyclic-shift construction). Ignores exemplars. Never calls any API."""

    _PROGS = [
        ("def construct(n, d, w):\n"
         "    from itertools import combinations\n"
         "    cap = w - (d + 1) // 2\n"
         "    code = []\n"
         "    for c in combinations(range(n), w):\n"
         "        s = set(c)\n"
         "        if all(len(s & set(e)) <= cap for e in code):\n"
         "            code.append(c)\n"
         "    return code\n"),
        ("def construct(n, d, w):\n"
         "    cap = w - (d + 1) // 2\n"
         "    base = list(range(w))\n"
         "    code = []\n"
         "    for k in range(n):\n"
         "        cw = sorted((x + k) % n for x in base)\n"
         "        if all(len(set(cw) & set(e)) <= cap for e in code):\n"
         "            code.append(cw)\n"
         "    return code\n"),
    ]

    def __init__(self):
        self.calls = 0

    def propose(self, n, d, w, floor, exemplars) -> str:
        src = self._PROGS[self.calls % len(self._PROGS)]
        self.calls += 1
        return src


class LLMProposer:
    """OpenRouter LLM proposer (stdlib urllib; OPENROUTER_API_KEY). Counts calls so the caller can
    enforce the pre-registered budget cap."""

    def __init__(self, model: str, max_tokens: int = 4096, timeout_s: int = 120):
        self.model, self.max_tokens, self.timeout_s = model, max_tokens, timeout_s
        self.calls = 0

    def propose(self, n, d, w, floor, exemplars) -> str:
        import urllib.request
        from leibniz.providers import USER_AGENT, ssl_context
        key = __import__("os").environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set (load .env)")
        payload = {"model": self.model, "max_tokens": self.max_tokens,
                   "messages": [{"role": "system", "content": _SYSTEM},
                                {"role": "user", "content": _prompt(n, d, w, floor, exemplars)}]}
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                     "User-Agent": USER_AGENT}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_s, context=ssl_context()) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
        self.calls += 1
        return extract_program(data["choices"][0]["message"]["content"])


def run_cell(proposer, n, d, w, snap, *, per_cell: int, budget_left: int,
             wall_deadline: float, top_k: int = 3) -> dict:
    """FunSearch over one cell: propose -> sandbox-eval -> keep best programs as exemplars -> repeat.
    Stops on a verified+kernel-checked beat, the per-cell cap, the global budget, or the deadline."""
    floor = effective_best_known(n, d, w, snap)
    db: list[tuple[str, int]] = []          # (program_src, fitness) sorted desc, untrusted
    best = {"size": 0, "valid": False}
    used = 0
    beat = None
    diag = {"sandbox_fail": 0, "invalid": 0, "valid": 0, "samples": []}  # so a best=0 is diagnosable
    for _ in range(min(per_cell, budget_left)):
        if time.time() > wall_deadline:
            break
        exemplars = sorted(db, key=lambda t: t[1], reverse=True)[:top_k]
        try:
            src = proposer.propose(n, d, w, floor, exemplars)
        except Exception as e:                                   # proposer failure is not a crash
            return {"n": n, "d": d, "w": w, "floor": floor, "programs": used,
                    "best_size": best["size"], "beat": None, "diag": diag, "error": f"proposer: {e}"}
        used += 1
        ev = sandbox.evaluate_program(src, n, d, w, snap)        # UNTRUSTED -> sandbox
        if not ev["sandbox_ok"]:
            diag["sandbox_fail"] += 1
            if len(diag["samples"]) < 5:
                diag["samples"].append({"kind": "sandbox", "msg": str(ev.get("sandbox_error"))[:240],
                                        "src": (src or "")[:200]})
        elif not ev["valid"]:
            diag["invalid"] += 1
            if len(diag["samples"]) < 5:
                diag["samples"].append({"kind": "invalid", "msg": str(ev.get("verify_reason"))[:240],
                                        "src": (src or "")[:200]})
        else:
            diag["valid"] += 1
            db.append((src, ev["fitness"]))
            if ev["size"] > best["size"]:
                best = {"size": ev["size"], "valid": True}
            if floor is not None and ev["size"] > floor:         # candidate beat -> kernel re-check
                witness = _rerun_for_witness(src, n, d, w)
                # the KERNEL-CONFIRMED witness must ITSELF strictly exceed the floor: a nondeterministic
                # program can pass the first eval but re-run to a smaller (floor-sized) code, which the
                # kernel would still validate as a true-but-not-record theorem. Require len > floor here.
                if (witness is not None and len(witness) > floor
                        and _kernel_confirms(witness, n, d, w)):
                    beat = {"size": len(witness), "floor": floor, "witness": witness, "program": src}
                    break
    return {"n": n, "d": d, "w": w, "floor": floor, "programs": used,
            "best_size": best["size"], "beat": beat, "diag": diag}


def _rerun_for_witness(src, n, d, w):
    """Re-run the program in the sandbox to recover the actual codewords for the kernel check."""
    res = sandbox.run_program(src, n, d, w)
    return res.code if res.ok else None


def _kernel_confirms(witness, n, d, w) -> bool:
    """Lean kernel re-check of a candidate beat (audit-only; never sets kernel_verified)."""
    try:
        from cwc_check import check
        rep = check(n, d, w, witness, run_kernel=True)
        return rep.get("kernel") == "KERNEL-VERIFIED"
    except Exception:
        return False


def load_targets() -> list[dict]:
    return json.loads(TARGETS.read_text())["targets"]


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM FunSearch pilot for CWC records (pre-registered, gated).")
    ap.add_argument("out", nargs="?", default="docs/results/funsearch_pilot_result.json")
    ap.add_argument("--fake", action="store_true", help="deterministic no-LLM proposer (no spend)")
    ap.add_argument("--model", default=__import__("os").environ.get("LEIBNIZ_FUNSEARCH_MODEL",
                    "anthropic/claude-3.5-sonnet"))
    ap.add_argument("--max-programs", type=int, default=240)
    ap.add_argument("--per-cell", type=int, default=20)
    ap.add_argument("--wall-min", type=float, default=60.0)
    ap.add_argument("--max-tokens", type=int, default=4096,
                    help="per-call token cap (raise for reasoning models that return null content)")
    args = ap.parse_args()

    if not args.fake:
        from leibniz.env import load_env
        load_env()
    snap, _ = ora.load_snapshot()
    proposer = FakeProposer() if args.fake else LLMProposer(args.model, max_tokens=args.max_tokens)
    targets = load_targets()
    deadline = time.time() + args.wall_min * 60
    rows, budget = [], args.max_programs
    beats = []
    for t in targets:
        if budget <= 0 or time.time() > deadline:
            break
        r = run_cell(proposer, t["n"], t["d"], t["w"], snap, per_cell=args.per_cell,
                     budget_left=budget, wall_deadline=deadline)
        budget -= r["programs"]
        rows.append(r)
        if r.get("beat"):
            beats.append(r["beat"])
        tag = "*** KERNEL-VERIFIED BEAT ***" if r.get("beat") else "no beat"
        dg = r.get("diag") or {}
        print(f"   A({t['n']},{t['d']},{t['w']}) floor={r['floor']} best={r['best_size']} "
              f"programs={r['programs']} [valid={dg.get('valid', 0)} invalid={dg.get('invalid', 0)} "
              f"sandbox_fail={dg.get('sandbox_fail', 0)}] -> {tag}")
        if dg.get("samples") and r["best_size"] == 0:            # surface WHY a cell got nothing
            for s in dg["samples"][:2]:
                print(f"       {s['kind']}: {s['msg']}")
                if s.get("src"):
                    print(f"         sent-src[:200]: {s['src']!r}")
        if r.get("beat"):                                        # stop rule: one verified beat ends it
            break
    summary = {"mode": "fake" if args.fake else f"llm:{args.model}", "cells": len(rows),
               "programs_used": args.max_programs - budget, "beats": len(beats),
               "beats_detail": beats, "rows": rows}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2))
    print(f"  BEATS: {len(beats)} | programs used: {summary['programs_used']} -> {args.out}")
    if beats:
        print("  NOTE: a kernel-verified beat is NOT promulgated — record for ADR 0040 carve-out "
              "+ operator review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
