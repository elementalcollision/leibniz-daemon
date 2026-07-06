/-
  Kernel-attested AUDIT of Belousova, Makhnev, Tokbaeva, "A strongly regular graph with parameters
  (1666, 105, 0, 7) does not exist" (Vestnik Perm. Univ. 1(72), 2026, 29-34; DOI
  10.17072/1993-0550-2026-1-29-34; Russian). The array {105,104,98,7,1; 1,7,98,104,105} is the
  bipartite double of the putative srg(1666,105,0,7).

  The paper's Theorem 1 proof compares two computations of the mean lambda of the auxiliary graph
  Lambda (distance-2 graph on Gamma_2(u); degree p^2_22=1461 on k_2=1560 vertices). Done correctly
  BOTH equal 1999388/1461; the printed gap (1362.905 vs 1368.09) is an artifact of two compensating
  arithmetic errors -- 104 for the true non-neighbour count 1560-1-1461=98, and dividing by 1560
  instead of 1461. The kernel re-decides the finite core (plain `decide`, exact Int arithmetic):

    srg1666_contradiction_vacuous : the two mean-lambda sums are EQUAL (1461*1460-98*1364 = 98*97+1461*1362).
    srg1666_row_identity          : [222]_L2 + [224]_L2 = p^2_22  (1364+97=1461) -- why S1=S2.
    srg1666_paper_gap_from_104    : the paper's 104 manufactures the gap.
    srg1666_lemma3_feasible       : all 8 Lemma-3 triple witnesses (r1=0..7) satisfy every marginal,
                                    all zero-Krein equations, and non-negativity => the (2,2,2) system
                                    is feasible => the triple-intersection method does NOT rule out the array.
    srg1666_lemma2_feasible       : the unique Lemma-2 witness satisfies its marginals + Krein + non-negativity.
    srg1666_control_r1_8          : r1=8 breaks non-negativity (a discriminating negative control).

  Report-only, audit tier: this shows the given proof does not decide the parameter set (treat as OPEN);
  it does NOT claim the graph exists or does not exist. Plain `decide`; no native_decide, no sorry;
  #print axioms shows at most [propext].
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

abbrev Tri := Nat × Nat × Nat × Int          -- (i, j, h, value); unlisted entries are 0
abbrev Tbl := List Tri

-- data lookups (flattened 6x6 tables, row-major index 6*i+j)
def look (xs : List Int) (i j : Nat) : Int := xs.getD (6 * i + j) 0

def tget (T : Tbl) (i j h : Nat) : Int :=
  (T.filter (fun e => e.1 == i && e.2.1 == j && e.2.2.1 == h)).foldl (fun a e => a + e.2.2.2) 0

def margI (T : Tbl) (j h : Nat) : Int :=
  (T.filter (fun e => e.2.1 == j && e.2.2.1 == h)).foldl (fun a e => a + e.2.2.2) 0
def margJ (T : Tbl) (i h : Nat) : Int :=
  (T.filter (fun e => e.1 == i && e.2.2.1 == h)).foldl (fun a e => a + e.2.2.2) 0
def margH (T : Tbl) (i j : Nat) : Int :=
  (T.filter (fun e => e.1 == i && e.2.1 == j)).foldl (fun a e => a + e.2.2.2) 0

def allPairs : List (Nat × Nat) :=
  (List.range 6).flatMap (fun i => (List.range 6).map (fun j => (i, j)))

-- marginals against p-slices pU,pV,pW; non-negativity; and all zero-Krein equations (Q3 = 3*Q)
def marginalsOK (T : Tbl) (pU pV pW : List Int) : Bool :=
  allPairs.all (fun p => (margI T p.1 p.2 == look pU p.1 p.2)
                      && (margJ T p.1 p.2 == look pV p.1 p.2)
                      && (margH T p.1 p.2 == look pW p.1 p.2))
def nonnegOK (T : Tbl) : Bool := T.all (fun e => decide (0 <= e.2.2.2))
def kreinOK (T : Tbl) (Q3 : List Int) (zk : List (Nat × Nat × Nat)) : Bool :=
  zk.all (fun z =>
    (T.foldl (fun a e => a + look Q3 e.1 z.1 * look Q3 e.2.1 z.2.1 * look Q3 e.2.2.1 z.2.2 * e.2.2.2) 0) == 0)
def validTbl (T : Tbl) (pU pV pW Q3 : List Int) (zk : List (Nat × Nat × Nat)) : Bool :=
  marginalsOK T pU pV pW && nonnegOK T && kreinOK T Q3 zk

def p2 : List Int := [0, 0, 1, 0, 0, 0, 0, 7, 0, 98, 0, 0, 1, 0, 1461, 0, 98, 0, 0, 98, 0, 1461, 0, 1, 0, 0, 98, 0, 7, 0, 0, 0, 0, 1, 0, 0]
def p4 : List Int := [0, 0, 0, 0, 1, 0, 0, 0, 0, 104, 0, 1, 0, 0, 1456, 0, 104, 0, 0, 104, 0, 1456, 0, 0, 1, 0, 104, 0, 0, 0, 0, 1, 0, 0, 0, 0]
def Q3 : List Int := [3, 1680, 3315, 3315, 1680, 3, 3, 224, 221, -221, -224, -3, 3, 14, -17, -17, 14, 3, 3, -14, -17, 17, 14, -3, 3, -224, 221, 221, -224, 3, 3, -1680, 3315, -3315, 1680, -3]
def zk : List (Nat × Nat × Nat) := [(1, 1, 1), (1, 1, 3), (1, 1, 5), (1, 2, 2), (1, 2, 4), (1, 2, 5), (1, 3, 1), (1, 3, 3), (1, 3, 5), (1, 4, 2), (1, 4, 4), (1, 5, 1), (1, 5, 2), (1, 5, 3), (1, 5, 5), (2, 1, 2), (2, 1, 4), (2, 1, 5), (2, 2, 1), (2, 2, 3), (2, 2, 5), (2, 3, 2), (2, 3, 4), (2, 4, 1), (2, 4, 3), (2, 4, 5), (2, 5, 1), (2, 5, 2), (2, 5, 4), (2, 5, 5), (3, 1, 1), (3, 1, 3), (3, 1, 5), (3, 2, 2), (3, 2, 4), (3, 3, 1), (3, 3, 3), (3, 3, 5), (3, 4, 2), (3, 4, 4), (3, 4, 5), (3, 5, 1), (3, 5, 3), (3, 5, 4), (3, 5, 5), (4, 1, 2), (4, 1, 4), (4, 2, 1), (4, 2, 3), (4, 2, 5), (4, 3, 2), (4, 3, 4), (4, 3, 5), (4, 4, 1), (4, 4, 3), (4, 4, 5), (4, 5, 2), (4, 5, 3), (4, 5, 4), (4, 5, 5), (5, 1, 1), (5, 1, 2), (5, 1, 3), (5, 1, 5), (5, 2, 1), (5, 2, 2), (5, 2, 4), (5, 2, 5), (5, 3, 1), (5, 3, 3), (5, 3, 4), (5, 3, 5), (5, 4, 2), (5, 4, 3), (5, 4, 4), (5, 4, 5), (5, 5, 1), (5, 5, 2), (5, 5, 3), (5, 5, 4), (5, 5, 5)]
def w0 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 7), (1, 3, 3, 98), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1362), (2, 2, 4, 98), (2, 4, 2, 98), (3, 1, 3, 98), (3, 3, 1, 98), (3, 3, 3, 1362), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 98), (4, 4, 4, 7), (5, 3, 3, 1)]
def w1 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 6), (1, 1, 3, 1), (1, 3, 1, 1), (1, 3, 3, 97), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1363), (2, 2, 4, 97), (2, 4, 2, 97), (2, 4, 4, 1), (3, 1, 1, 1), (3, 1, 3, 97), (3, 3, 1, 97), (3, 3, 3, 1363), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 97), (4, 2, 4, 1), (4, 4, 2, 1), (4, 4, 4, 6), (5, 3, 3, 1)]
def w2 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 5), (1, 1, 3, 2), (1, 3, 1, 2), (1, 3, 3, 96), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1364), (2, 2, 4, 96), (2, 4, 2, 96), (2, 4, 4, 2), (3, 1, 1, 2), (3, 1, 3, 96), (3, 3, 1, 96), (3, 3, 3, 1364), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 96), (4, 2, 4, 2), (4, 4, 2, 2), (4, 4, 4, 5), (5, 3, 3, 1)]
def w3 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 4), (1, 1, 3, 3), (1, 3, 1, 3), (1, 3, 3, 95), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1365), (2, 2, 4, 95), (2, 4, 2, 95), (2, 4, 4, 3), (3, 1, 1, 3), (3, 1, 3, 95), (3, 3, 1, 95), (3, 3, 3, 1365), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 95), (4, 2, 4, 3), (4, 4, 2, 3), (4, 4, 4, 4), (5, 3, 3, 1)]
def w4 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 3), (1, 1, 3, 4), (1, 3, 1, 4), (1, 3, 3, 94), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1366), (2, 2, 4, 94), (2, 4, 2, 94), (2, 4, 4, 4), (3, 1, 1, 4), (3, 1, 3, 94), (3, 3, 1, 94), (3, 3, 3, 1366), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 94), (4, 2, 4, 4), (4, 4, 2, 4), (4, 4, 4, 3), (5, 3, 3, 1)]
def w5 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 2), (1, 1, 3, 5), (1, 3, 1, 5), (1, 3, 3, 93), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1367), (2, 2, 4, 93), (2, 4, 2, 93), (2, 4, 4, 5), (3, 1, 1, 5), (3, 1, 3, 93), (3, 3, 1, 93), (3, 3, 3, 1367), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 93), (4, 2, 4, 5), (4, 4, 2, 5), (4, 4, 4, 2), (5, 3, 3, 1)]
def w6 : Tbl := [(0, 2, 2, 1), (1, 1, 1, 1), (1, 1, 3, 6), (1, 3, 1, 6), (1, 3, 3, 92), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1368), (2, 2, 4, 92), (2, 4, 2, 92), (2, 4, 4, 6), (3, 1, 1, 6), (3, 1, 3, 92), (3, 3, 1, 92), (3, 3, 3, 1368), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 92), (4, 2, 4, 6), (4, 4, 2, 6), (4, 4, 4, 1), (5, 3, 3, 1)]
def w7 : Tbl := [(0, 2, 2, 1), (1, 1, 3, 7), (1, 3, 1, 7), (1, 3, 3, 91), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1369), (2, 2, 4, 91), (2, 4, 2, 91), (2, 4, 4, 7), (3, 1, 1, 7), (3, 1, 3, 91), (3, 3, 1, 91), (3, 3, 3, 1369), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 91), (4, 2, 4, 7), (4, 4, 2, 7), (5, 3, 3, 1)]
def w8 : Tbl := [(0, 2, 2, 1), (1, 1, 1, -1), (1, 1, 3, 8), (1, 3, 1, 8), (1, 3, 3, 90), (2, 0, 2, 1), (2, 2, 0, 1), (2, 2, 2, 1370), (2, 2, 4, 90), (2, 4, 2, 90), (2, 4, 4, 8), (3, 1, 1, 8), (3, 1, 3, 90), (3, 3, 1, 90), (3, 3, 3, 1370), (3, 3, 5, 1), (3, 5, 3, 1), (4, 2, 2, 90), (4, 2, 4, 8), (4, 4, 2, 8), (4, 4, 4, -1), (5, 3, 3, 1)]
def wL2 : Tbl := [(0, 2, 2, 1), (1, 1, 3, 7), (1, 3, 1, 7), (1, 3, 3, 91), (2, 0, 4, 1), (2, 2, 2, 1364), (2, 2, 4, 97), (2, 4, 0, 1), (2, 4, 2, 97), (3, 1, 3, 97), (3, 1, 5, 1), (3, 3, 1, 97), (3, 3, 3, 1364), (3, 5, 1, 1), (4, 2, 2, 91), (4, 2, 4, 7), (4, 4, 2, 7), (5, 3, 3, 1)]
def lemma3wits : List Tbl := [w0, w1, w2, w3, w4, w5, w6, w7]

theorem srg1666_row_identity : (1364 : Int) + 97 = 1461 := by decide

theorem srg1666_contradiction_vacuous : (1461*1460 - 98*1364 : Int) = 98*97 + 1461*1362 := by decide

theorem srg1666_paper_gap_from_104 : (1461*1460 - 104*1364 : Int) ≠ 98*97 + 1461*1362 := by decide

theorem srg1666_lemma3_feasible : lemma3wits.all (fun T => validTbl T p2 p2 p2 Q3 zk) = true := by decide

theorem srg1666_lemma2_feasible : validTbl wL2 p4 p2 p2 Q3 zk = true := by decide

theorem srg1666_control_r1_8 : validTbl w8 p2 p2 p2 Q3 zk = false := by decide

#print axioms srg1666_row_identity
#print axioms srg1666_contradiction_vacuous
#print axioms srg1666_paper_gap_from_104
#print axioms srg1666_lemma3_feasible
#print axioms srg1666_lemma2_feasible
#print axioms srg1666_control_r1_8
