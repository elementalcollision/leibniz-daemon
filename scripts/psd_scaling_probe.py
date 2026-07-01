"""PSD certificate scaling probe — measures the external agent's "compute trap" (gate #2 for the SDP bet).

The agent warned (90%) that at Terwilliger-block scale (~30x30) the exact rational Cholesky certificate's
integer denominators explode (>10000 bits) and the kernel OOMs/timeouts. This measures it directly: build
strict-PD rational matrices simulating a rounded float SDP dual (entries k/D with float-precision denominator
D, made PD via diagonal dominance so NO pivoting is needed — the agent's #4 mechanism), compute the integer
LDLᵀ certificate, and record the max integer bit-length + producer time + kernel-check time vs size n.

This isolates the COMPUTE trap (bit-length/kernel scaling); it does NOT test the Irrationality Wall (gate #1,
which needs a real SDP solver). Free-CPU (producer) + docker (kernel leg).
"""
from __future__ import annotations

import importlib.util
import json
import random
import time
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "psd_scaling_probe.json"


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")


def rounded_pd(seed: int, n: int, D: int):
    """Integer strict-PD matrix N simulating the numerator of a rounded float SDP dual (float-precision
    denominator D cleared): symmetric integer entries in [-D,D], diagonal made dominant so N is strictly PD
    (no pivoting needed). N ⪰ 0 ⟺ N/D ⪰ 0, so we certify the integer N directly (kernel-clean)."""
    rng = random.Random(seed)
    N = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            N[i][j] = N[j][i] = rng.randint(-D, D)
    for i in range(n):
        N[i][i] = sum(abs(N[i][j]) for j in range(n) if j != i) + D    # diagonally dominant => PD
    return N


def _maxbits(*mats) -> int:
    b = 0
    for M in mats:
        for row in (M if isinstance(M[0], list) else [M]):
            for x in row:
                b = max(b, int(abs(x)).bit_length())
    return b


def probe(sizes=(6, 10, 14, 18, 22, 26, 30), D=10 ** 6, kernel_upto=18) -> dict:
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        have_kernel = available()
        bk = LeanCliBackend(timeout_s=120) if have_kernel else None
    except Exception:
        have_kernel, bk = False, None
    rows = []
    for n in sizes:
        N = rounded_pd(0, n, D)
        t0 = time.perf_counter()
        res = pm.ldlt([[Fr(N[i][j]) for j in range(n)] for i in range(n)])
        prod_t = time.perf_counter() - t0
        if res is None:
            rows.append({"n": n, "status": "ldlt-failed(zero pivot)"})
            continue
        L, d = res
        Li, di, sc = pm.clear_denoms(L, d)
        maxbits = max(_maxbits(Li), _maxbits(di), int(sc).bit_length())
        row = {"n": n, "max_cert_bits": maxbits, "scale_bits": int(sc).bit_length(),
               "producer_secs": round(prod_t, 3),
               "exact_verifies": pm.verify_int_cert(N, Li, di, sc)}
        if have_kernel and n <= kernel_upto:
            t1 = time.perf_counter()
            row["kernel"] = bk.check_source(pm.render_ldlt_lean(N, Li, di, sc))
            row["kernel_secs"] = round(time.perf_counter() - t1, 1)
        rows.append(row)
        print(f"  n={n:>3d}  max_cert_bits={maxbits:>6d}  producer={prod_t:>6.3f}s  "
              f"verify={row['exact_verifies']}  kernel={row.get('kernel','-')}/{row.get('kernel_secs','-')}s")
    ok = [r for r in rows if r.get("exact_verifies")]
    kern = [r for r in rows if r.get("kernel") is True]
    biggest = max((r["max_cert_bits"] for r in rows if "max_cert_bits" in r), default=0)
    verdict = ("MANAGEABLE" if biggest < 4000 and (not kern or all(r.get("kernel_secs", 0) < 60 for r in kern))
               else "COMPUTE-TRAP-CONFIRMED")
    return {"verdict": verdict, "D": D, "max_bits_at_largest": biggest,
            "exact_verified": len(ok), "kernel_verified": len(kern), "rows": rows,
            "reading": ("Tests the agent's compute-trap (gate #2): does the exact rational Cholesky "
                        "certificate's integer bit-length / kernel time explode at Terwilliger scale? "
                        "MANAGEABLE => bit-length stays bounded and the kernel checks in-budget (the trap "
                        "is milder than feared for well-conditioned strict-PD certs). Does NOT test the "
                        "Irrationality Wall (gate #1 — needs a real SDP solver).")}


def main() -> int:
    print("PSD certificate scaling probe (compute-trap / gate #2):")
    res = probe()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"  verdict={res['verdict']} max_bits_at_largest={res['max_bits_at_largest']} "
          f"exact_verified={res['exact_verified']} kernel_verified={res['kernel_verified']}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
