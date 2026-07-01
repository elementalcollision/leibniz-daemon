"""Bank the Delsarte LP certificate architecture as an audit-tier UPPER-BOUND verification asset.

The reach probe established plain LP is a sound, scalable VERIFICATION tool (not a discovery engine). This
banks that: it builds a durable, reproducible corpus of **kernel-verified Delsarte upper-bound certificates**
for A(n,d) — the upper-bound analog of the covering/CWC amplification corpus. Each entry is an exact integer
Delsarte dual certificate (q; p_1..p_n) that the Lean 4.31 kernel independently re-checks (recomputing
Krawtchouk itself), proving A(n,d) <= bound.

POSTURE (identical to amplify.py): audit-tier. It never sets kernel_verified, never promulgates. The
kernel checks the certificate's VALIDITY; the certOK => A(n,d) <= f(0) step is Delsarte's theorem (cited,
not yet formalized in core Lean — the bridge lemma is a deferred slice, exactly like the pending
validCovering => C(v,k,t) <= B bridge). Novelty is record-relative against the (unvetted) best-known UB
snapshot; a cert below the snapshot would be flagged for authoritative review, never auto-claimed.

RUNS WHERE: free-CPU (ortools) for the LP + certificate; docker (Lean image) for the kernel re-check. On the
operator machine / self-hosted lean runner. Emits docs/results/delsarte_ub_corpus.json + reading-room MD.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
CORPUS = _ROOT / "docs" / "results" / "delsarte_ub_corpus.json"
READING = _ROOT / "docs" / "results" / "delsarte_ub_reading_room.md"


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dl = _load("delsarte_lp_probe", "scripts/delsarte_lp_probe.py")

# Cells where the Delsarte LP certificate reproduces the best-known A(n,d) UB (from P1 + the reach probe):
# a clean, kernel-checkable UB-certificate set. best_known merged from the two probes' vetted values.
CELLS = [(5, 3), (6, 3), (7, 3), (6, 4), (8, 4), (8, 5), (9, 5), (10, 5), (11, 5),
         (13, 3), (13, 5), (13, 7), (14, 3), (14, 5), (14, 7), (15, 3), (15, 5), (15, 7)]
BEST_KNOWN = {**dl.KNOWN,
              (13, 3): 512, (13, 5): 64, (13, 7): 8, (14, 3): 1024, (14, 5): 128, (14, 7): 16,
              (15, 3): 2048, (15, 5): 256, (15, 7): 32}


def build(run_kernel: bool = True) -> dict:
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        have_kernel = run_kernel and available()
        bk = LeanCliBackend(timeout_s=180) if have_kernel else None
    except Exception:
        have_kernel, bk = False, None

    rows = []
    for (n, d) in CELLS:
        sol = dl.solve_dual_lp(n, d)
        cert = dl.rationalize_and_verify(n, d, sol[0]) if sol else None
        if cert is None:
            rows.append({"cell": f"A({n},{d})", "n": n, "d": d, "skipped": "no exact certificate"})
            continue
        p, bound, q, _D = cert
        ok, b, _ = dl.verify_integer_cert(n, d, p, q)
        if not (ok and b == bound):
            rows.append({"cell": f"A({n},{d})", "n": n, "d": d, "skipped": "exact re-check failed"})
            continue
        kernel = "not run"
        if have_kernel:
            v = bk.check_source(dl.render_cert_lean(n, d, q, p, bound))
            kernel = "KERNEL-VERIFIED" if v is True else "KERNEL-REJECTED" if v is False else "unavailable"
        ubk = BEST_KNOWN.get((n, d))
        rows.append({"cell": f"A({n},{d})", "n": n, "d": d, "claim": f"A({n},{d}) <= {bound}",
                     "bound": bound, "cert_q": q, "cert_p": p, "kernel": kernel,
                     "best_known": ubk,
                     "novelty": ("reproduces best-known" if ubk == bound
                                 else "TIGHTENS best-known (INVESTIGATE vs authoritative table)" if ubk is not None and bound < ubk
                                 else "above best-known" if ubk is not None else "untabulated"),
                     "source": "delsarte-lp + Lean kernel", "method": "Delsarte LP dual certificate"})
    verified = [r for r in rows if r.get("kernel") == "KERNEL-VERIFIED"]
    return {"n_entries": len(rows), "kernel_verified": len(verified),
            "posture": "AUDIT-TIER: kernel-checked certificate VALIDITY; certOK=>bound is Delsarte's "
                       "theorem (bridge lemma deferred). NOT promulgated; kernel_verified never set.",
            "rows": rows}


def render_reading_room(res: dict) -> str:
    ver = [r for r in res["rows"] if r.get("kernel") == "KERNEL-VERIFIED"]
    out = ["# Calculemus — Audit Annex: Delsarte upper-bound certificates", "",
           "*Kernel-verified Delsarte LP **dual** certificates for binary codes A(n,d) — the UPPER-bound "
           "analog of the construction amplification annex. Each row: an untrusted LP solver proposed an "
           "exact integer dual certificate; the Lean 4.31 kernel independently re-checked it (recomputing "
           "Krawtchouk), proving A(n,d) <= bound. **Audit-tier — kernel-checked certificate validity, not "
           "promulgated laws**; the certOK => bound step is Delsarte's theorem (bridge lemma deferred). "
           "Novelty is record-relative vs an unvetted best-known snapshot.*", "",
           f"**{len(ver)}/{res['n_entries']} kernel-verified.**", "",
           "| cell | claim | kernel | novelty | method |", "|---|---|---|---|---|"]
    for r in res["rows"]:
        if "skipped" in r:
            continue
        out.append(f"| {r['cell']} | {r['claim']} | {r.get('kernel','?')} | {r.get('novelty','?')} | "
                   f"{r['method']} |")
    return "\n".join(out) + "\n"


def main() -> int:
    res = build()
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    CORPUS.write_text(json.dumps(res, indent=2) + "\n")
    READING.write_text(render_reading_room(res))
    print(f"Delsarte UB certificate bank: {res['kernel_verified']}/{res['n_entries']} kernel-verified")
    for r in res["rows"]:
        if "skipped" in r:
            print(f"  {r['cell']:9s} skipped: {r['skipped']}")
        else:
            print(f"  {r['cell']:9s} {r['claim']:18s} {r.get('kernel',''):16s} {r.get('novelty','')}")
    print(f"  -> {CORPUS}\n  -> {READING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
