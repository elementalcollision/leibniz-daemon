/-
  Subgroups of finite fields as cap sets — kernel-attested. Independent confirmation of Kable, Mills & Wright
  (2026), arXiv:2604.26989. A cap set contains no full "line" of its affine geometry: in AG(k,3) (the SET game)
  a line is three distinct points summing to 0; in AG(k,2) (EvenQuads) a "quad" is four distinct points summing
  to 0. `set81` lists the 20 nonzero fourth powers of GF(81) as vectors in (F₃)⁴; `eq64` lists the 9 nonzero
  seventh powers of GF(64) as vectors in (F₂)⁶ (both reconstructed from the field axioms by
  scripts/verify_capset_subgroups.py; the cap property is independent of the field model). The kernel decides:
    • capset_set81  : no three distinct elements of `set81` sum to 0 mod 3 — a maximal SET-cap of size 20;
    • capset_eq64   : no four distinct elements of `eq64` sum to 0 mod 2 — a maximal EvenQuads-cap of size 9.
  Plain `decide` — no `native_decide`, no `sorry`. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def addm (m : Nat) : List Int → List Int → List Int
  | a :: as, b :: bs => ((a + b) % (m : Int)) :: addm m as bs
  | _, _ => []

def nonzero (v : List Int) : Bool := v.any (fun x => x != 0)

def set81 : List (List Int) := [[0, 1, 2, 2], [0, 2, 1, 1], [1, 0, 0, 0], [1, 0, 0, 2], [1, 0, 1, 0], [1, 0, 1, 2], [1, 1, 1, 0], [1, 2, 0, 0], [1, 2, 0, 1], [1, 2, 1, 2], [1, 2, 2, 2], [2, 0, 0, 0], [2, 0, 0, 1], [2, 0, 2, 0], [2, 0, 2, 1], [2, 1, 0, 0], [2, 1, 0, 2], [2, 1, 1, 1], [2, 1, 2, 1], [2, 2, 2, 0]]
def eq64 : List (List Int) := [[0, 0, 1, 0, 1, 0], [0, 0, 1, 1, 1, 0], [0, 1, 0, 1, 1, 0], [0, 1, 0, 1, 1, 1], [0, 1, 1, 0, 0, 0], [1, 0, 0, 0, 0, 0], [1, 1, 0, 1, 0, 0], [1, 1, 0, 1, 1, 1], [1, 1, 1, 1, 1, 0]]

-- SET-cap: no three distinct fourth-powers of GF(81) sum to 0 (mod 3)
theorem capset_set81 :
    (List.range 20).all (fun i => (List.range 20).all (fun j => (List.range 20).all (fun k =>
      (!(i < j && j < k)) || nonzero (addm 3 (addm 3 (set81.getD i []) (set81.getD j [])) (set81.getD k []))))) = true := by decide

-- EvenQuads-cap: no four distinct seventh-powers of GF(64) sum to 0 (mod 2)
theorem capset_eq64 :
    (List.range 9).all (fun i => (List.range 9).all (fun j => (List.range 9).all (fun k =>
      (List.range 9).all (fun l => (!(i < j && j < k && k < l)) ||
        nonzero (addm 2 (addm 2 (addm 2 (eq64.getD i []) (eq64.getD j [])) (eq64.getD k [])) (eq64.getD l [])))))) = true := by decide

#print axioms capset_set81
#print axioms capset_eq64
