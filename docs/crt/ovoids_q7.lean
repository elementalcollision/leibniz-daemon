/-
  Low-degree ovoids of Q+(7,q) -- kernel-attested. Independent confirmation of the Kantor-ovoid facts in
  Bartoli, Durante, Grimaldi & Timpanella, "Ovoids of Q+(7,q) of low-degree" (arXiv:2502.02219, 2025). The
  Kantor ovoid (q = 2^h) is given, for q in {2,4,16}, by f1 = xy+z^2, f2 = xz+y^2+z^2, f3 = yz+x^2+y^2+z^2;
  at q = 8 these functions do NOT define an ovoid. O7(f1,f2,f3) is an ovoid iff Condition (3) holds:
    for all distinct P1=(x1,y1,z1), P2=(x2,y2,z2) in F_q^3,
      F = (x1-x2)(f3(P2)-f3(P1)) + (y1-y2)(f2(P2)-f2(P1)) + (z1-z2)(f1(P2)-f1(P1))  !=  0 .

  GF(2^h) = F_2[X]/(irreducible), elements as Nat bitmasks; char 2 so add = sub = XOR. `gmul` is the
  carryless multiply-and-reduce, computed in-kernel from (h, irreducible). The kernel decides:
    ovoid_q2  : Condition (3) holds for q = 2  (F_2,  8 points);
    ovoid_q4  : Condition (3) holds for q = 4  (F_4, 64 points, 4032 ordered distinct pairs) -> ovoid of Q+(7,4);
    ovoid_q8_fails : the explicit distinct pair (0,0,0),(0,1,3) has F = 0 at q = 8 -> NOT an ovoid (a
                     discriminating negative from the same source).

  Plain `decide` -- no `native_decide`, no `sorry`; #print axioms shows at most [propext]. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def gmulAux (h mod a b acc fuel : Nat) : Nat :=
  match fuel with
  | 0 => acc
  | Nat.succ fuel => if b == 0 then acc
      else let acc := if b % 2 == 1 then acc ^^^ a else acc
           let a2 := a <<< 1
           let a2 := if a2 &&& (1 <<< h) != 0 then a2 ^^^ mod else a2
           gmulAux h mod a2 (b / 2) acc fuel
def gmul (h mod a b : Nat) : Nat := gmulAux h mod a b 0 (h + 1)
def sq (h mod a : Nat) : Nat := gmul h mod a a
def f1 (h mod x y z : Nat) : Nat := (gmul h mod x y) ^^^ (sq h mod z)
def f2 (h mod x y z : Nat) : Nat := (gmul h mod x z) ^^^ (sq h mod y) ^^^ (sq h mod z)
def f3 (h mod x y z : Nat) : Nat := (gmul h mod y z) ^^^ (sq h mod x) ^^^ (sq h mod y) ^^^ (sq h mod z)
def form (h mod : Nat) (P1 P2 : Nat × Nat × Nat) : Nat :=
  let x1 := P1.1; let y1 := P1.2.1; let z1 := P1.2.2
  let x2 := P2.1; let y2 := P2.2.1; let z2 := P2.2.2
  (gmul h mod (x1 ^^^ x2) ((f3 h mod x2 y2 z2) ^^^ (f3 h mod x1 y1 z1))) ^^^
  (gmul h mod (y1 ^^^ y2) ((f2 h mod x2 y2 z2) ^^^ (f2 h mod x1 y1 z1))) ^^^
  (gmul h mod (z1 ^^^ z2) ((f1 h mod x2 y2 z2) ^^^ (f1 h mod x1 y1 z1)))
def pts (q : Nat) : List (Nat × Nat × Nat) :=
  (List.range q).flatMap (fun x => (List.range q).flatMap (fun y => (List.range q).map (fun z => (x, y, z))))
def condition3 (h mod q : Nat) : Bool :=
  (pts q).all (fun P1 => (pts q).all (fun P2 => (P1 == P2) || form h mod P1 P2 != 0))

theorem ovoid_q2 : condition3 1 3 2 = true := by decide

theorem ovoid_q4 : condition3 2 7 4 = true := by decide

theorem ovoid_q8_fails : (((0,0,0) : Nat × Nat × Nat) != (0,1,3) && form 3 11 (0,0,0) (0,1,3) == 0) = true := by decide

#print axioms ovoid_q2
#print axioms ovoid_q4
#print axioms ovoid_q8_fails
