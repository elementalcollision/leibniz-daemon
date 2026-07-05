/-
  Counterexample to the Brualdi–Friedland–Pothen sparse-basis conjecture — decided by the Lean kernel.
  Independent confirmation of Aliabadi (2026), arXiv:2605.30401 (refuting the SUFFICIENCY direction of
  Conjecture 2.1). Reconstructed from first principles by scripts/verify_bfp_counterexample.py; the general
  algebraically-independent case is verified symbolically over ℚ(a,…,l). This file kernel-checks a
  matroid-faithful integer specialization (its 39 basis 4×4 minors match the generic ones).

  `Arows` is the 4×8 matrix. `xs` are four elementary vectors of its row space with `combos`ₛ·A = xsₛ; `Jl`
  are their (0-indexed) zero-sets. `dvec` is an integer left-null vector of [x₁;…;x₄]. The kernel `decide`s:
    (1) membership  xsₛ = combosₛ·A;
    (2) Z(xsₛ) = Jlₛ  (support is exactly the complement);
    (3) each xsₛ is a genuine ELEMENTARY vector: rank A[:,Jₛ]=3 (a nonzero 3×3 minor) and every column outside
        Jₛ raises the rank to 4 (nonzero 4×4 minor) — i.e. the support is a cocircuit / minimal;
    (4) the BFP inequalities: the kernel decides the cardinality bound |⋂_{s∈P} Jₛ| ≤ 4−|P| for every nonempty
        P ⊆ [4], which yields the conjecture's rank inequality rank A[:,⋂Jₛ] ≤ 4−|P| because rank ≤ #columns;
        for the tight singleton cases (⋂ = Jₛ) leg (3) additionally certifies the exact rank is 3.
        (The exact rank values for every P are independently certified in the symbolic ℚ(a,…,l) / integer legs.)
    (5) dvec ≠ 0 and dvec·[x₁;…;x₄] = 0 — the elementary vectors are linearly DEPENDENT, so NOT a basis.
  (4)+(5): the inequalities hold yet the vectors are not a basis — sufficiency refuted.

  Plain `decide` (kernel reduction) — no `native_decide`, no `sorry`. `#print axioms` reports only `propext`
  (one of Lean's three canonical trusted axioms; NOT `sorryAx`, NOT compiler trust). Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def dot : List Int → List Int → Int
  | a :: as, b :: bs => a * b + dot as bs
  | _, _ => 0

def detN : Nat → List (List Int) → Int
  | 0, _ => 1
  | (n+1), M => match M with
    | [] => 0
    | row :: rest => (List.range (n+1)).foldl (fun acc j =>
        acc + (if j % 2 == 0 then (1:Int) else -1) * (row.getD j 0) * detN n (rest.map (fun r => r.eraseIdx j))) 0

def Arows : List (List Int) := [[2, 5, 7, 0, 0, 0, 0, 31], [0, 0, 0, 11, 0, 19, 0, 37], [3, 0, 0, 0, 0, 23, 29, 0], [0, 0, 0, 13, 17, 0, 0, 0]]
def submat (rs cs : List Nat) : List (List Int) :=
  rs.map (fun r => cs.map (fun c => (Arows.getD r []).getD c 0))
def xs : List (List Int) := [[-74, -185, -259, 341, 0, 589, 0, 0], [0, -285, -399, -506, 0, 0, 1102, -3469], [0, -3705, -5187, 0, 8602, 0, 14326, -45097], [962, 2405, 3367, 0, 5797, -7657, 0, 0]]
def combos : List (List Int) := [[-37, 31, 0, 0], [-57, -46, 38, 0], [-741, -598, 494, 506], [481, -403, 0, 341]]
def Acols : List (List Int) :=
  (List.range 8).map (fun t => (List.range 4).map (fun r => (Arows.getD r []).getD t 0))
def dvec : List Int := [598, 403, -31, 46]
def Xcols : List (List Int) := [[-74, 0, 0, 962], [-185, -285, -3705, 2405], [-259, -399, -5187, 3367], [341, -506, 0, 0], [0, 0, 8602, 5797], [589, 0, 0, -7657], [0, 1102, 14326, 0], [0, -3469, -45097, 0]]
def Jl : List (List Nat) := [[4, 6, 7], [0, 4, 5], [0, 3, 5], [3, 6, 7]]
def inter (a b : List Nat) : List Nat := a.filter (fun x => b.any (fun y => y == x))
def interP (P : List Nat) : List Nat :=
  (P.drop 1).foldl (fun acc i => inter acc (Jl.getD i [])) (Jl.getD (P.getD 0 0) [])
def subsets : List (List Nat) := [[0], [1], [2], [3], [0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3], [0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3], [0, 1, 2, 3]]

theorem bfp_counterexample :
    ( ((List.range 4).all (fun s => (List.range 8).all (fun t =>
          (xs.getD s []).getD t 0 == dot (combos.getD s []) (Acols.getD t []))))
    && ((List.range 4).all (fun s => (List.range 8).all (fun t =>
          (((xs.getD s []).getD t 0 == 0) == (Jl.getD s []).any (fun u => u == t)))))
    && (detN 3 (submat [0, 2, 3] [4, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 4, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [1, 4, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [2, 4, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [3, 4, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [4, 5, 6, 7]) != 0)
    && (detN 3 (submat [0, 1, 3] [0, 4, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 1, 4, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 2, 4, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 3, 4, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 4, 5, 6]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 4, 5, 7]) != 0)
    && (detN 3 (submat [0, 1, 2] [0, 3, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 1, 3, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 2, 3, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 3, 4, 5]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 3, 5, 6]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 3, 5, 7]) != 0)
    && (detN 3 (submat [0, 1, 2] [3, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [0, 3, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [1, 3, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [2, 3, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [3, 4, 6, 7]) != 0)
    && (detN 4 (submat [0,1,2,3] [3, 5, 6, 7]) != 0)
    -- (4) BFP inequalities: |⋂Jₛ| ≤ 4−|P| ⇒ rank A[:,⋂Jₛ] ≤ 4−|P| (rank ≤ #cols); singletons' rank=3 by (3)
    && (subsets.all (fun P => (interP P).length + P.length ≤ 4))
    && (dvec.any (fun v => v != 0))
    && (Xcols.all (fun col => dot dvec col == 0)) ) = true := by decide

#print axioms bfp_counterexample
