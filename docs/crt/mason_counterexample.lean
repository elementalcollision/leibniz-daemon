/-
  Counterexample to Mason's matroid log-concavity conjecture — kernel-attested.
  Independent confirmation of "Counterexamples to two conjectures about matroids" (arXiv:2607.02208, 2026),
  Example 2.2. Mason conjectured the Whitney numbers of the second kind W_k (number of flats of rank k) of any
  matroid are log-concave: W_k² ≥ W_{k-1}·W_{k+1}. The graphic matroid of the theta graph Θ(1,26,26,26) (77
  vertices, rank 76) violates this at k=74.

  Flats of a graphic matroid ↔ partitions of the vertices into connected blocks (rank k ↔ 77−k blocks), so
  W_k counts connected partitions. `gsame`/`gdiff` are the per-path floating-block generating functions of one
  length-26 hub-to-hub path (produced and validated against brute-force enumeration by
  scripts/verify_mason_counterexample.py). The kernel assembles the three identical long paths by exact
  polynomial arithmetic (cubing), reads off the Whitney numbers W_75, W_74, W_73, confirms them, and decides
  the strict inequality W_74² < W_73·W_75 — Mason's conjecture is false.

  Plain `decide` — no `native_decide`, no `sorry`. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def padd : List Int → List Int → List Int
  | [], b => b
  | a, [] => a
  | x :: xs, y :: ys => (x + y) :: padd xs ys

def pmul : List Int → List Int → List Int
  | [], _ => []
  | x :: xs, b => padd (b.map (fun t => x * t)) ((0:Int) :: pmul xs b)

def gsame : List Int := [1, 325, 2600, 14950, 65780, 230230, 657800, 1562275, 3124550, 5311735, 7726160, 9657700, 10400600, 9657700, 7726160, 5311735, 3124550, 1562275, 657800, 230230, 65780, 14950, 2600, 325, 26, 1]
def gdiff : List Int := [26, 325, 2600, 14950, 65780, 230230, 657800, 1562275, 3124550, 5311735, 7726160, 9657700, 10400600, 9657700, 7726160, 5311735, 3124550, 1562275, 657800, 230230, 65780, 14950, 2600, 325, 26, 1]
def gs3 : List Int := pmul (pmul gsame gsame) gsame
def gd3 : List Int := pmul (pmul gdiff gdiff) gdiff
def W2 : Int := gs3.getD 1 0 + gd3.getD 0 0   -- W_75 (partitions into 2 connected blocks)
def W3 : Int := gs3.getD 2 0 + gd3.getD 1 0   -- W_74 (3 blocks)
def W4 : Int := gs3.getD 3 0 + gd3.getD 2 0   -- W_73 (4 blocks)

theorem mason_whitney_values :
    (W2 == 18551) && (W3 == 983775) && (W4 == 52954525) = true := by decide

theorem mason_log_concavity_fails : W3 * W3 < W4 * W2 := by decide

#print axioms mason_whitney_values
#print axioms mason_log_concavity_fails
