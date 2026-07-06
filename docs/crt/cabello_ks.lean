/-
  The simplest Kochen-Specker set -- kernel-attested. Independent confirmation of Cabello, "Simplest
  Kochen-Specker Set" (Phys. Rev. Lett. 135, 190203, 2025; arXiv:2508.07335): 33 qutrit vectors with 14
  orthogonal bases that admit NO KS {0,1}-assignment -- a record-low number of bases (previous record 16),
  refuting Conjecture 2 of Phys. Rev. Lett. 134, 010201 (2025). Vectors have Eisenstein-integer components
  (w = e^{2 pi i/3}, w^2 = -1-w), stored as pairs (a,b) = a + b w; conj(a+bw) = (a-b) - b w. The kernel decides:
    cabello_bases_orth  : each of the 14 bases is mutually orthogonal (Hermitian inner product 0 over Z[w]);
    cabello_uncolorable : no KS assignment exists -- a bounded backtracking search (exactly-one per basis +
                          at-most-one per orthogonal edge) returns no solution (~1.2k nodes; no external SAT dump);
    cabello_control     : removing one basis makes the reduced set colorable (a discriminating negative control).

  Plain `decide` -- no `native_decide`, no `sorry`; #print axioms shows at most [propext]. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 4000000

abbrev Eis := Int × Int
def emul (p q : Eis) : Eis := (p.1 * q.1 - p.2 * q.2, p.1 * q.2 + p.2 * q.1 - p.2 * q.2)
def econj (p : Eis) : Eis := (p.1 - p.2, - p.2)
def eadd (p q : Eis) : Eis := (p.1 + q.1, p.2 + q.2)
def herm (u v : List Eis) : Eis := (List.zipWith (fun a b => emul (econj a) b) u v).foldl eadd (0, 0)
def orth (u v : List Eis) : Bool := herm u v == (0, 0)

def ray (rays : List (List Eis)) (i : Nat) : List Eis := rays.getD i []
def orthI (rays : List (List Eis)) (i j : Nat) : Bool := orth (ray rays i) (ray rays j)
def pickable (rays : List (List Eis)) (ones zeros : List Nat) (v : Nat) : Bool :=
  !(zeros.contains v) && !(ones.any (fun o => orthI rays o v))
def solve (rays : List (List Eis)) (bs : List (Nat × Nat × Nat)) (ones zeros : List Nat) (fuel : Nat) : Bool :=
  match fuel with
  | 0 => false
  | Nat.succ fuel => match bs with
    | [] => true
    | (a, b, c) :: rest =>
      let cnt := (if ones.contains a then 1 else 0) + (if ones.contains b then 1 else 0) + (if ones.contains c then 1 else 0)
      if cnt > 1 then false
      else if cnt == 1 then solve rays rest ones (([a,b,c].filter (fun v => !ones.contains v)) ++ zeros) fuel
      else [a,b,c].any (fun v => pickable rays ones zeros v &&
             solve rays rest (v :: ones) (([a,b,c].filter (fun w => w != v)) ++ zeros) fuel)

def rays : List (List Eis) := [[(0, 0), (0, 0), (1, 0)], [(0, 0), (1, 0), (0, 0)], [(1, 0), (0, 0), (0, 0)], [(1, 0), (0, 1), (-1, -1)], [(1, 0), (1, 0), (1, 0)], [(-1, -1), (0, 1), (1, 0)], [(1, 0), (0, 1), (1, 1)], [(1, 0), (1, 0), (-1, 0)], [(-1, -1), (0, 1), (-1, 0)], [(1, 0), (0, -1), (-1, -1)], [(1, 0), (-1, 0), (1, 0)], [(-1, -1), (0, -1), (1, 0)], [(-1, 0), (0, 1), (-1, -1)], [(-1, 0), (1, 0), (1, 0)], [(1, 1), (0, 1), (1, 0)], [(1, 0), (1, 0), (0, 0)], [(1, 0), (-1, 0), (0, 0)], [(1, 0), (0, 1), (0, 0)], [(1, 0), (0, -1), (0, 0)], [(0, 1), (1, 0), (0, 0)], [(0, 1), (-1, 0), (0, 0)], [(1, 0), (0, 0), (1, 0)], [(1, 0), (0, 0), (-1, 0)], [(1, 0), (0, 0), (0, 1)], [(1, 0), (0, 0), (0, -1)], [(0, 1), (0, 0), (1, 0)], [(0, 1), (0, 0), (-1, 0)], [(0, 0), (1, 0), (1, 0)], [(0, 0), (1, 0), (-1, 0)], [(0, 0), (1, 0), (0, 1)], [(0, 0), (1, 0), (0, -1)], [(0, 0), (0, 1), (1, 0)], [(0, 0), (0, 1), (-1, 0)]]
def bases : List (Nat × Nat × Nat) := [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11), (12, 13, 14), (0, 15, 16), (0, 17, 18), (0, 19, 20), (1, 21, 22), (1, 23, 24), (1, 25, 26), (2, 27, 28), (2, 29, 30), (2, 31, 32)]
def basesDrop1 : List (Nat × Nat × Nat) := [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11), (12, 13, 14), (0, 15, 16), (0, 17, 18), (0, 19, 20), (1, 21, 22), (1, 23, 24), (1, 25, 26), (2, 27, 28), (2, 29, 30)]

theorem cabello_bases_orth : bases.all (fun t => orthI rays t.1 t.2.1 && orthI rays t.1 t.2.2 && orthI rays t.2.1 t.2.2) = true := by decide

theorem cabello_uncolorable : solve rays bases [] [] 30 = false := by decide

theorem cabello_control : solve rays basesDrop1 [] [] 30 = true := by decide

#print axioms cabello_bases_orth
#print axioms cabello_uncolorable
#print axioms cabello_control
