/-
  The Markoff special point (1,1,1) and the connected cage — kernel-attested. Independent confirmation of the
  arithmetic core of Bellah, Dunn, Naidu & Wells, "Connectedness of Special Points in the Markoff mod p Graphs"
  (arXiv:2511.23401, 2025). The rotation order ord_{p}(1,1,1) equals the order of A = [[0,1],[-1,3]] in
  GL₂(F_p) (companion matrix of T²−3T+1, discriminant 5). Their Theorem 2.10 (at (1,1,1)): if p ≡ ±2 (mod 5)
  — so x=1 is elliptic and (5/p) = −1 — then 2^{ν₂(p+1)} ∣ ord_{p}(1,1,1); and (Prop 3.3) ord_{p}(1,1,1) = π(p)/2.

  Self-contained certificate of 2^{ν₂(p+1)} ∣ ord (no exact order needed): A^{p+1} = I forces ord ∣ p+1 (the
  elliptic torus), and then A^{(p+1)/2} ≠ I forces 2^{ν₂(p+1)} ∣ ord. Matrices are Nat 4-tuples mod p; `mpow`
  is binary fast-exponentiation. For Mersenne primes p = 2ⁿ − 1, p+1 = 2ⁿ, so ν₂(p+1) = n and ord = p+1.

    • markoff_div_small    : the divisibility certificate for a spread of primes p ≡ ±2 (mod 5).
    • markoff_div_mersenne : the same for the Mersenne primes 127, 524287, 2147483647 (= 2³¹−1).
    • markoff_pisano       : the second route — ord(A) = π(p)/2 (Prop 3.3) for p ∈ {7,127}, both computed by
                             direct iteration (matrix order vs the Fibonacci Pisano period).
    • markoff_control      : a prime p ≡ ±1 (mod 5) (x=1 hyperbolic) has A^{p+1} ≠ I — the order does NOT divide
                             p+1, so the ellipticity hypothesis is load-bearing (a discriminating negative control).

  Plain `decide` — no `native_decide`, no `sorry`; every theorem depends on no axioms. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

abbrev Mat := Nat × Nat × Nat × Nat   -- [[a,b],[c,d]]

def Iden : Mat := (1, 0, 0, 1)
def Amat (p : Nat) : Mat := (0, 1, p - 1, 3 % p)          -- [[0,1],[-1,3]] mod p

def mmul (p : Nat) (X Y : Mat) : Mat :=
  let a := X.1; let b := X.2.1; let c := X.2.2.1; let d := X.2.2.2
  let e := Y.1; let f := Y.2.1; let g := Y.2.2.1; let h := Y.2.2.2
  ((a*e + b*g) % p, (a*f + b*h) % p, (c*e + d*g) % p, (c*f + d*h) % p)

def mpowAux (p : Nat) (base : Mat) (e : Nat) (fuel : Nat) (acc : Mat) : Mat :=
  match fuel with
  | 0 => acc
  | Nat.succ fuel => if e == 0 then acc
                     else mpowAux p (mmul p base base) (e / 2) fuel (if e % 2 == 1 then mmul p acc base else acc)
def mpow (p : Nat) (X : Mat) (e : Nat) : Mat := mpowAux p X e 64 Iden

/-- p ≡ ±2 mod 5 (hypothesis); A^{p+1}=I (ord ∣ p+1); A^{(p+1)/2}≠I (2^{ν₂(p+1)} ∣ ord). -/
def posCheck (p : Nat) : Bool :=
  (p % 5 == 2 || p % 5 == 3) && (mpow p (Amat p) (p + 1) == Iden) && (mpow p (Amat p) ((p + 1) / 2) != Iden)
def allPos (ps : List Nat) : Bool := ps.all posCheck

def matOrderAux (p : Nat) (A cur : Mat) (d fuel : Nat) : Nat :=
  match fuel with
  | 0 => 0
  | Nat.succ fuel => if cur == Iden then d else matOrderAux p A (mmul p cur A) (d + 1) fuel
def matOrder (p : Nat) : Nat := matOrderAux p (Amat p) (Amat p) 1 (p + 2)

def pisanoAux (p a b n fuel : Nat) : Nat :=
  match fuel with
  | 0 => 0
  | Nat.succ fuel => let a' := b; let b' := (a + b) % p
                     if a' == 0 && b' == 1 then n + 1 else pisanoAux p a' b' (n + 1) fuel
def pisano (p : Nat) : Nat := pisanoAux p 0 1 0 (3 * p + 10)

theorem markoff_div_small : allPos [7, 13, 17, 23, 43, 47] = true := by decide

theorem markoff_div_mersenne : allPos [127, 524287, 2147483647] = true := by decide

theorem markoff_pisano : (pisano 7 == 2 * matOrder 7 && pisano 127 == 2 * matOrder 127) = true := by decide

theorem markoff_control : ((11 % 5 == 1) && (mpow 11 (Amat 11) (11 + 1) != Iden)) = true := by decide

#print axioms markoff_div_small
#print axioms markoff_div_mersenne
#print axioms markoff_pisano
#print axioms markoff_control
