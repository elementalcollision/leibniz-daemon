/-
  Independent kernel verification of Ataka–Matsuoka (2026), "Normality of monomial ideals in three
  variables", arXiv:2602.01782v1, Example 4.5 / Remark 1.3.

  Their Main Theorem: an integrally closed monomial ideal I in k[x,y,z] with ht I = 3 and μ(I) ≤ 7
  is normal; the bound 7 is SHARP. The sharpness witness is I = closure(x⁷,y³,z²), which has EIGHT
  minimal generators and is NOT normal (I² ⊊ closure(I²), witnessed by x⁶y²z).

  We reproduce BOTH facts kernel-decidably from the Newton polyhedron (weights (6,14,21), L = 42):
    • the up-set {u : wt u ≥ 42} has exactly 8 minimal lattice points = the paper's generator list;
    • x⁶y²z ∈ closure(I²) (wt = 85 ≥ 2L = 84) but x⁶y²z ∉ I², so I is not normal (RRV, d=3).
  Kernel-decided by `decide`, no axioms. LLMs propose nothing; the kernel decides.
  Produced by scripts/verify_ataka_matsuoka.py (Leibniz daemon).
-/
import Mathlib.Tactic

namespace AtakaMatsuoka732

/-- L-cleared weighted degree for the corner ideal (x⁷,y³,z²); L = lcm = 42, weights (6,14,21). -/
def wt (a b c : ℕ) : ℕ := 6*a + 14*b + 21*c

/-- Newton polyhedron: x^u ∈ I = closure(x⁷,y³,z²) ⟺ wt u ≥ 42 (a rational-convex up-set). -/
def inI (a b c : ℕ) : Bool := 42 ≤ wt a b c

/-- u is a MINIMAL generator: in I, and dropping 1 from any positive coordinate leaves I. -/
def isMinGen (a b c : ℕ) : Bool :=
  inI a b c
    && (a == 0 || ! inI (a-1) b c)
    && (b == 0 || ! inI a (b-1) c)
    && (c == 0 || ! inI a b (c-1))

/-- Complete search box: a minimal generator cannot exceed the pure powers (7,3,2). -/
def box : List (ℕ × ℕ × ℕ) :=
  (List.range 8).flatMap fun a => (List.range 4).flatMap fun b =>
    (List.range 3).map fun c => (a, b, c)

/-- The minimal generators of closure(x⁷,y³,z²), in lexicographic order. -/
def gens : List (ℕ × ℕ × ℕ) := box.filter fun u => isMinGen u.1 u.2.1 u.2.2

/-- **Example 4.5 (generator count).** closure(x⁷,y³,z²) has exactly EIGHT minimal monomial
    generators — the fact that makes the μ(I) ≤ 7 normality bound sharp. -/
theorem eight_minimal_generators : gens.length = 8 := by decide

/-- …and they are EXACTLY the paper's list  x⁷, y³, z², x⁵y, x³y², x⁴z, y²z, x²yz  (exponent triples). -/
theorem generators_are_paper_list : gens = [(0,0,2), (0,2,1), (0,3,0), (2,1,1), (3,2,0), (4,0,1), (5,1,0), (7,0,0)] := by decide

/-- x^u ∈ I² ⟺ ∃ v ≤ u with 42 ≤ wt v ≤ wt u − 42 (I an up-set, wt linear). For u = (6,2,1),
    wt u = 85, so this seeks v ≤ (6,2,1) with 42 ≤ wt v ≤ 43 — there is none. -/
def inI2_at_witness : Bool :=
  (List.range 7).any fun a => (List.range 3).any fun b => (List.range 2).any fun c =>
    42 ≤ wt a b c && wt a b c ≤ 43

/-- **Example 4.5 (non-normality).** x⁶y²z ∈ closure(I²) (wt = 85 ≥ 2L = 84) but x⁶y²z ∉ I².
    By Reid–Roberts–Vitulli (d = 3 ⟹ check I and I²), closure(x⁷,y³,z²) is therefore NOT normal. -/
theorem not_normal_witness_x6y2z : 84 ≤ wt 6 2 1 ∧ inI2_at_witness = false := by decide

end AtakaMatsuoka732
