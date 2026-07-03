-- P4: value-assign (Def 14) is NOT a type-preserving specialization of
-- count-update (Defs 1-2). Kernel-checked in Lean 4.31 + Mathlib (env: import Mathlib).
-- Verdict: 0 errors, 0 warnings, 0 sorries. Negative control (asserting the
-- opposite) is only closable by `sorry`, so the result is non-vacuous.
import Mathlib

namespace MCR_P4

/-- Def 2's count-update per-cell WRITE, in an ordered additive monoid, is
    *strictly increasing*: it adds a positive unit, so `x < u x` for all `x`. -/
def IsCountUpdateShape {V : Type*} [LT V] (u : V → V) : Prop :=
  ∀ x : V, x < u x

/-- Def 14's value-assign per-cell WRITE is *constant in the pre-state*
    (it ignores the current cell and stores the supplied target). -/
def IsValueAssignShape {V : Type*} (u : V → V) : Prop :=
  ∀ x y : V, u x = u y

/-- CORE NON-DERIVABILITY.  On any linearly ordered value type, if one unary
    map `u` inhabits BOTH the count-update shape (strictly increasing) and the
    value-assign shape (constant), the type is a subsingleton (`∀ a b, a = b`).
    Contrapositive: on any nontrivial value type the two update primitives are
    not the same operation, so value-assign is not a type-preserving
    specialization of count-update. -/
theorem not_derivable
    {V : Type*} [LinearOrder V] (u : V → V)
    (hcount : IsCountUpdateShape u) (hassign : IsValueAssignShape u) :
    ∀ a b : V, a = b := by
  intro a b
  have hstrict : u a < u (u a) := hcount (u a)
  have hconst : u (u a) = u a := hassign (u a) a
  rw [hconst] at hstrict
  exact absurd hstrict (lt_irrefl _)

/-- The two update SIGNATURES are literally different types: count-update takes
    (table, key, key) — no value supplied; value-assign takes (table, key,
    value). -/
def CountUpdateSig (Tbl K : Type*) : Type _ := Tbl → K → K → Tbl
def ValueAssignSig (Tbl K V : Type*) : Type _ := Tbl → K → V → Tbl

/-- Concrete nontrivial instantiation on `Int` (the intended `N` embeds here):
    NO `u : Int → Int` is both strictly increasing and constant, since that
    forces `(0:Int) = 1`. -/
theorem not_derivable_on_Int (u : Int → Int)
    (hcount : IsCountUpdateShape u) (hassign : IsValueAssignShape u) : False := by
  have h : (0 : Int) = 1 := not_derivable u hcount hassign 0 1
  exact absurd h (by decide)

end MCR_P4
