/-
  A complex Hadamard matrix of order 94 exists -- kernel-attested structural core. Independent confirmation of
  Szollosi, "A complex Hadamard matrix of order 94" (arXiv:2603.09572, 2026), Theorem 1. The construction
  (Theorem 4) uses four circulant {-1,1}-matrices A,B,C,D of order 47, with A,B symmetric, satisfying
      A A^T + B B^T + C C^T + D D^T = 188 I ;
  they assemble into a complex Hadamard matrix of order 94. Because each Gram matrix G G^T of a circulant G is
  itself circulant (determined by its first row), eq (1) is equivalent to: the summed periodic autocorrelations
  of A,B,C,D vanish at every nonzero shift (and equal 4*47 = 188 at shift 0). The kernel decides that reduced
  form (a length-47 check) plus the symmetry of A,B -- the exact hypotheses of Theorem 4 -- for the two witnesses
  of the paper (Example 1 and Example 2), and a negative control (a single flipped sign breaks eq (1)).

    autocorr x s = sum_k x[k] * x[(k+s) mod 47]  ;  eq1 x = for all s: sum of the four autocorrs = (188 if s=0 else 0).

  (The assembled 94x94 identity H H* = 94 I is verified end-to-end by the exact integer procedure in
  scripts/verify_hadamard94.py; the dense 94x94 product hits the plain-`decide` wall.)

  Plain `decide` -- no `native_decide`, no `sorry`; every theorem depends on no axioms. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def rot (x : List Int) (s : Nat) : List Int := x.drop s ++ x.take s
def dotf (u v : List Int) : Int := (List.zipWith (fun a b => a * b) u v).foldl (fun t a => t + a) 0
def autocorr (x : List Int) (s : Nat) : Int := dotf x (rot x s)

def eq1 (a b c d : List Int) : Bool :=
  (List.range 47).all (fun s => autocorr a s + autocorr b s + autocorr c s + autocorr d s == (if s == 0 then 188 else 0))

def symrow (x : List Int) : Bool := (List.range 47).all (fun k => x.getD k 0 == x.getD ((47 - k) % 47) 0)

def a1 : List Int := [1, 1, 1, 1, -1, 1, -1, 1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, 1, 1, -1, 1, -1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1]
def b1 : List Int := [1, 1, -1, 1, -1, 1, 1, 1, -1, 1, -1, 1, 1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, 1, 1, 1, -1, 1, -1, -1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, -1, 1, -1, 1]
def c1 : List Int := [1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, 1, 1, -1, -1, 1, -1, -1, -1, -1, -1, 1, -1, -1, 1, 1, -1, 1, 1, 1, 1, -1, 1, 1, 1, -1, -1, 1, -1, 1, -1]
def d1 : List Int := [1, 1, 1, 1, 1, 1, -1, -1, 1, 1, 1, 1, -1, 1, 1, -1, 1, -1, 1, -1, -1, 1, 1, -1, 1, 1, -1, -1, -1, 1, -1, 1, 1, -1, 1, 1, 1, -1, -1, -1, 1, 1, -1, 1, 1, -1, -1]
def a2 : List Int := [1, -1, -1, 1, 1, -1, -1, -1, -1, 1, 1, 1, -1, -1, -1, 1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, 1, -1, -1, -1, 1, 1, 1, -1, -1, -1, -1, 1, 1, -1, -1]
def b2 : List Int := [1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, 1, -1, 1, 1, 1, 1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, 1, -1, -1, 1, 1, -1, -1, -1]
def c2 : List Int := [1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, 1, -1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, -1, -1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, -1, 1, 1, -1]
def d2 : List Int := [1, 1, 1, 1, 1, 1, -1, 1, -1, 1, 1, 1, 1, -1, 1, -1, 1, 1, -1, 1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1, 1, 1, -1, 1, -1, -1, -1, 1, -1, -1, 1, -1, -1, -1]
def a1bad : List Int := [-1, 1, 1, 1, -1, 1, -1, 1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, 1, 1, -1, 1, -1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1]

theorem had94_eq1_example1 : eq1 a1 b1 c1 d1 = true := by decide
theorem had94_sym_example1 : (symrow a1 && symrow b1) = true := by decide
theorem had94_eq1_example2 : eq1 a2 b2 c2 d2 = true := by decide
theorem had94_sym_example2 : (symrow a2 && symrow b2) = true := by decide
theorem had94_control : eq1 a1bad b1 c1 d1 = false := by decide

#print axioms had94_eq1_example1
#print axioms had94_sym_example1
#print axioms had94_eq1_example2
#print axioms had94_sym_example2
#print axioms had94_control
