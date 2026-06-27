/-!
Leibniz — committed CWC witness (durable Q.E.D. artifact, ADR 0040 / Option E).

This is the first kernel-accepted result of the discovery arc, made RE-RUNNABLE: previously the
`A(7,4,3) >= 7` Q.E.D. existed only inside an ephemeral Docker session (PR #152). This file is the
exact output of `scripts/probe_beta_cwc_pilot.py::render_cwc_lean(7,4,3, FANO)` (a test pins the
match, so it cannot drift), and it kernel-checks under the pinned `lean-toolchain` (v4.31.0) with NO
Mathlib (minimal TCB). The witness IS the proof: `validCWC <code> 7 4 3 7 = true` is a faithful
encoding of A(7,4,3) >= 7, closed by `decide`.

Build/check:  (from lean-project/)  lake env lean CwcFanoWitness.lean    # exit 0 == kernel-accepted

NB (ADR 0040): a record-BEATING witness theorem is also closed by `decide`, which the promulgation
pipeline's triviality gate (`is_trivial`, novelty.py) would quarantine. The carve-out is documented
in ADR 0040 and deferred until a genuine beat exists. This file is a non-record (equals the Fano
optimum), so the gate is not exercised here.
-/

-- constant-weight-code witness checker (core Lean 4; no Mathlib)
def interLen (a b : List Nat) : Nat := (a.filter (fun x => b.contains x)).length
def distinctSyms (c : List Nat) : Bool := c.all (fun x => (c.filter (fun y => x == y)).length == 1)
def codewordOK (c : List Nat) (n w : Nat) : Bool :=
  (c.length == w) && c.all (fun x => decide (x < n)) && distinctSyms c
def distinctCodewords (C : List (List Nat)) : Bool :=
  C.all (fun c => (C.filter (fun c' => c == c')).length == 1)
def pairwiseDist (C : List (List Nat)) (d w : Nat) : Bool :=
  C.all (fun a => C.all (fun b => (a == b) || decide (d ≤ 2 * (w - interLen a b))))
def validCWC (C : List (List Nat)) (n d w M : Nat) : Bool :=
  (C.length == M) && distinctCodewords C && C.all (fun c => codewordOK c n w) && pairwiseDist C d w

theorem cwc_7_4_3_ge_7 :
    validCWC [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]] 7 4 3 7 = true := by
  decide
