/-
  Steiner systems S(2,8,225) and S(2,9,289) exist — kernel-attested. Independent confirmation of Hetman (2026),
  arXiv:2509.10673, resolving two of the 129 undecided cases in the Handbook of Combinatorial Designs. Each
  system is an explicit difference family: base blocks in an abelian group, developed by translation. A family
  is a (v,k,1)-difference family — hence develops to a Steiner 2-(v,k,1) design — iff the nonzero differences
  b−b′ within the base blocks hit every nonzero group element exactly once. `mods` gives the cyclic factors;
  `blocks` are the base blocks as points (component tuples). The kernel computes all k(k−1) differences per
  block and decides they are pairwise DISTINCT, all NONZERO, and number exactly v−1 — so (there being exactly
  v−1 nonzero elements) they are precisely the nonzero elements, once each.

    • steiner_S8_225 : ℤ₃×ℤ₃×ℤ₅×ℤ₅, 4 blocks of size 8 → 224 differences = all 224 nonzero elements.
    • steiner_S9_289 : ℤ₁₇×ℤ₁₇, 4 blocks of size 9 → 288 differences = all 288 nonzero elements.

  Plain `decide` — no `native_decide`, no `sorry`. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def subm : List Int → List Int → List Int → List Int
  | m :: ms, a :: as, b :: bs => ((a - b) % m) :: subm ms as bs
  | _, _, _ => []

def isNonzero (v : List Int) : Bool := v.any (fun x => x != 0)

def blockDiffs (mods : List Int) (B : List (List Int)) : List (List Int) :=
  B.flatMap (fun a => B.filterMap (fun b => if a == b then none else some (subm mods a b)))

def allDiffs (mods : List Int) (blocks : List (List (List Int))) : List (List Int) :=
  blocks.flatMap (blockDiffs mods)

def isDiffFamily (mods : List Int) (blocks : List (List (List Int))) (vm1 : Nat) : Bool :=
  let ds := allDiffs mods blocks
  (ds.length == vm1) && (ds.all isNonzero) && ds.Nodup

def mods8 : List Int := [3, 3, 5, 5]
def blocks8 : List (List (List Int)) := [[[0, 0, 0, 0], [0, 0, 0, 1], [0, 1, 0, 3], [1, 0, 0, 3], [1, 2, 1, 0], [1, 2, 4, 1], [2, 1, 1, 2], [2, 1, 4, 4]], [[0, 0, 0, 0], [0, 0, 0, 2], [0, 1, 2, 1], [0, 1, 3, 1], [0, 2, 2, 2], [0, 2, 3, 0], [2, 1, 0, 1], [2, 2, 0, 1]], [[0, 0, 0, 0], [0, 0, 1, 1], [1, 0, 0, 1], [1, 0, 1, 0], [1, 2, 3, 3], [2, 0, 2, 3], [2, 0, 4, 3], [2, 2, 3, 3]], [[0, 0, 0, 0], [0, 0, 1, 2], [1, 0, 3, 1], [1, 1, 2, 0], [1, 1, 4, 2], [2, 1, 3, 1], [2, 2, 2, 3], [2, 2, 4, 4]]]
def mods9 : List Int := [17, 17]
def blocks9 : List (List (List Int)) := [[[0, 0], [0, 1], [0, 3], [1, 3], [2, 2], [3, 3], [4, 10], [6, 16], [10, 14]], [[0, 0], [0, 4], [0, 9], [1, 15], [5, 9], [9, 13], [10, 8], [11, 16], [13, 9]], [[0, 0], [0, 6], [2, 15], [3, 11], [5, 8], [10, 9], [11, 14], [13, 1], [14, 11]], [[0, 0], [0, 7], [1, 4], [3, 15], [5, 10], [6, 2], [8, 9], [10, 5], [12, 10]]]

theorem steiner_S8_225 : isDiffFamily mods8 blocks8 224 = true := by decide

theorem steiner_S9_289 : isDiffFamily mods9 blocks9 288 = true := by decide

#print axioms steiner_S8_225
#print axioms steiner_S9_289
