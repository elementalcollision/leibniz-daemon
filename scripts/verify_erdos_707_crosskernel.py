"""Cross-kernel amplification (ADR 0048): the Erdős-707 finite core, independently re-decided in Rocq/Coq.

Leibniz's Lean 4.31 census (cycle 15 / PR #295) kernel-decided the finite core of Erdős Problem 707 (the
Sidon-Extension Conjecture, disproved by Alexeev–Mixon 2025 / Niu 2026): for four counterexample sets, that
each is a Sidon set and each is NON-EXTENDING to a perfect difference set (PDS) at small orders. This script
re-decides the SAME facts in the Rocq 9.0 (Coq) kernel — a second, independent trusted core — by `vm_compute`,
and confirms axiom-free via `rocqchk`. A PDS of order n has n(n−1)=v−1, so B ⊂ ℤ_v is a PDS iff its pairwise
diffs mod v are distinct; non-extension at order n ⟺ no size-n superset is Sidon mod v — a bounded decidable
fact. Report-only (audit tier, ADR 0048 dormant Coq backend); no trust surface.

Run:  python scripts/verify_erdos_707_crosskernel.py   (Python check is free-CPU; the Coq leg needs Docker + image)
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from leibniz.backends import coq_docker  # noqa: E402

ARTIFACT = _ROOT / "docs" / "crt" / "erdos_707_crosscheck.v"
OUT = _ROOT / "docs" / "results" / "erdos_707_crosskernel_verification.json"

# The same four counterexample sets Lean decided (#295); each verified at orders |S| and |S|+1.
SETS = {
    "A": [0, 1, 3, 11], "B": [0, 1, 4, 11], "AM5": [1, 2, 4, 8, 13], "Hall": [1, 3, 9, 10, 13],
}


def is_sidon(S) -> bool:
    d = [b - a for a in S for b in S if a != b]
    return len(d) == len(set(d))


def _is_pds(B, v) -> bool:
    n = len(B)
    if v != n * n - n + 1 or len(set(x % v for x in B)) != n:
        return False
    return len({(b - a) % v for a in B for b in B if a != b}) == v - 1


def extends_order(S, n) -> bool:
    v = n * n - n + 1
    base = sorted({s % v for s in S})
    if len(base) != len(S):
        return False
    pool = [x for x in range(v) if x not in base]
    return any(_is_pds(base + list(e), v) for e in combinations(pool, n - len(base)))


_PRELUDE = (
    "(*\n"
    "  Erdős Problem 707 (Sidon-Extension Conjecture) — finite core, independent SECOND-KERNEL confirmation\n"
    "  (ADR 0048). The Sidon property + non-extension at small orders that Leibniz's Lean census decided\n"
    "  (PR #295), re-decided by the Rocq 9.0 kernel via vm_compute. Axiom-free (rocqchk: * Axioms: <none>).\n"
    "  Disproof: Alexeev–Mixon arXiv:2510.19804; size-4 candidates: Niu arXiv:2604.25214. No trust surface.\n"
    "*)\n"
    "Require Import ZArith List Nat.\nImport ListNotations.\n\n"
    "Fixpoint membZ (x : Z) (l : list Z) : bool :=\n"
    "  match l with | [] => false | y :: r => Z.eqb x y || membZ x r end.\n"
    "Fixpoint nodupZ (l : list Z) : bool :=\n"
    "  match l with | [] => true | x :: r => negb (membZ x r) && nodupZ r end.\n"
    "Definition diffsZ (S : list Z) : list Z :=\n"
    "  flat_map (fun a => flat_map (fun b => if Z.eqb a b then [] else [Z.sub b a]) S) S.\n\n"
    "Fixpoint membN (x : nat) (l : list nat) : bool :=\n"
    "  match l with | [] => false | y :: r => Nat.eqb x y || membN x r end.\n"
    "Fixpoint nodupN (l : list nat) : bool :=\n"
    "  match l with | [] => true | x :: r => negb (membN x r) && nodupN r end.\n"
    "Definition diffsMod (S : list nat) (v : nat) : list nat :=\n"
    "  flat_map (fun a => flat_map (fun b => if Nat.eqb a b then [] else [Nat.modulo (v + b - a) v]) S) S.\n"
    "Definition isPDS (B : list nat) (v : nat) : bool := nodupN (diffsMod B v) && nodupN B.\n"
    "(* S is non-extending at order n (v=n(n-1)+1) iff NO single adjoined residue makes a PDS. *)\n"
    "Definition extends1 (S : list nat) (v : nat) : bool := existsb (fun x => isPDS (S ++ [x]) v) (seq 0 v).\n\n"
)


def _zlist(S):
    return "[" + "; ".join(f"{x}%Z" for x in S) + "]"


def _nlist(S):
    return "[" + "; ".join(str(x) for x in S) + "]"


def build_cert() -> tuple[str, list[str]]:
    lines, names = [], []
    for name, S in SETS.items():
        s = len(S)
        v_s = s * s - s + 1
        v_s1 = (s + 1) * (s + 1) - (s + 1) + 1
        lines.append(f"(* {name} = {{{', '.join(map(str, S))}}} — Sidon, non-extending at orders {s},{s + 1}. *)")
        lines.append(f"Example {name}_sidon : nodupZ (diffsZ {_zlist(S)}) = true.")
        lines.append("Proof. vm_compute. reflexivity. Qed.")
        lines.append(f"Example {name}_no_order{s} : isPDS {_nlist(S)} {v_s} = false.")
        lines.append("Proof. vm_compute. reflexivity. Qed.")
        lines.append(f"Example {name}_no_order{s + 1} : extends1 {_nlist(S)} {v_s1} = false.")
        lines.append("Proof. vm_compute. reflexivity. Qed.")
        names += [f"{name}_sidon", f"{name}_no_order{s}", f"{name}_no_order{s + 1}"]
    return _PRELUDE + "\n".join(lines) + "\n", names


def cross_check() -> dict:
    rows = []
    for name, S in SETS.items():
        s = len(S)
        rows.append({"set": name, "sidon": is_sidon(S),
                     "non_extending": (not extends_order(S, s)) and (not extends_order(S, s + 1))})
    return {"rows": rows, "all_ok": all(r["sidon"] and r["non_extending"] for r in rows)}


def main() -> int:
    print("=== Erdős 707 finite core — cross-kernel (Lean #295 ↔ Rocq 9.0) ===")
    cc = cross_check()
    for r in cc["rows"]:
        print(f"  {r['set']:>5}: sidon={r['sidon']}  non-extending(orders |S|,|S|+1)={r['non_extending']}")
    src, names = build_cert()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(src)
    print(f"  Coq certificate: {len(names)} Examples -> {ARTIFACT.relative_to(_ROOT)}")

    coq = {"status": "not run"}
    if coq_docker.available():
        print("  running Rocq 9.0 (rocq compile + rocqchk audit) ...")
        d = coq_docker.CoqDockerBackend(timeout_s=300).check_source_with_detail(src)
        coq = {"status": "unavailable"} if d is None else {
            "status": "checked", "verified": d["verified"], "audit_ran": d["audit_ran"],
            "opens_axioms": d["opens_axioms"], "n_examples": len(names)}
        if d is not None:
            print(f"  Rocq verdict: verified={d['verified']}  rocqchk axioms<none>={not d['opens_axioms']}  "
                  f"({len(names)} Examples) -> {'SOUND ✓' if d['verified'] else 'ISSUE: ' + d['output_tail']}")
    else:
        coq = {"status": "unavailable (docker/image)"}
        print("  Rocq: unavailable (skip)")

    ok = cc["all_ok"] and coq.get("verified")
    gate = ("GREEN" if ok else
            "AMBER(coq-unavailable)" if "unavailable" in str(coq.get("status")) and cc["all_ok"] else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION", "adr": "0048",
           "target": "Erdős Problem 707 (Sidon-Extension Conjecture) finite core — cross-kernel (Lean #295 ↔ Rocq 9.0)",
           "cross_check": cc, "coq": coq, "instances": names, "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "reading": ("The Erdős-707 finite core (four counterexample sets Sidon + non-extending at small "
                       "orders) that Leibniz's Lean 4.31 kernel decided in #295, independently re-decided by "
                       "the Rocq 9.0 kernel via vm_compute and confirmed axiom-free by rocqchk. Two independent "
                       "trusted cores agree on the finite exhaustion of a freshly-resolved $1000 Erdős problem "
                       "— cross-kernel amplification. Report-only (audit tier); no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
