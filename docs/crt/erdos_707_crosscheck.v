(*
  Erdős Problem 707 (Sidon-Extension Conjecture) — finite core, independent SECOND-KERNEL confirmation
  (ADR 0048). The Sidon property + non-extension at small orders that Leibniz's Lean census decided
  (PR #295), re-decided by the Rocq 9.0 kernel via vm_compute. Axiom-free (rocqchk: * Axioms: <none>).
  Disproof: Alexeev–Mixon arXiv:2510.19804; size-4 candidates: Niu arXiv:2604.25214. No trust surface.
*)
Require Import ZArith List Nat.
Import ListNotations.

Fixpoint membZ (x : Z) (l : list Z) : bool :=
  match l with | [] => false | y :: r => Z.eqb x y || membZ x r end.
Fixpoint nodupZ (l : list Z) : bool :=
  match l with | [] => true | x :: r => negb (membZ x r) && nodupZ r end.
Definition diffsZ (S : list Z) : list Z :=
  flat_map (fun a => flat_map (fun b => if Z.eqb a b then [] else [Z.sub b a]) S) S.

Fixpoint membN (x : nat) (l : list nat) : bool :=
  match l with | [] => false | y :: r => Nat.eqb x y || membN x r end.
Fixpoint nodupN (l : list nat) : bool :=
  match l with | [] => true | x :: r => negb (membN x r) && nodupN r end.
Definition diffsMod (S : list nat) (v : nat) : list nat :=
  flat_map (fun a => flat_map (fun b => if Nat.eqb a b then [] else [Nat.modulo (v + b - a) v]) S) S.
Definition isPDS (B : list nat) (v : nat) : bool := nodupN (diffsMod B v) && nodupN B.
(* S is non-extending at order n (v=n(n-1)+1) iff NO single adjoined residue makes a PDS. *)
Definition extends1 (S : list nat) (v : nat) : bool := existsb (fun x => isPDS (S ++ [x]) v) (seq 0 v).

(* A = {0, 1, 3, 11} — Sidon, non-extending at orders 4,5. *)
Example A_sidon : nodupZ (diffsZ [0%Z; 1%Z; 3%Z; 11%Z]) = true.
Proof. vm_compute. reflexivity. Qed.
Example A_no_order4 : isPDS [0; 1; 3; 11] 13 = false.
Proof. vm_compute. reflexivity. Qed.
Example A_no_order5 : extends1 [0; 1; 3; 11] 21 = false.
Proof. vm_compute. reflexivity. Qed.
(* B = {0, 1, 4, 11} — Sidon, non-extending at orders 4,5. *)
Example B_sidon : nodupZ (diffsZ [0%Z; 1%Z; 4%Z; 11%Z]) = true.
Proof. vm_compute. reflexivity. Qed.
Example B_no_order4 : isPDS [0; 1; 4; 11] 13 = false.
Proof. vm_compute. reflexivity. Qed.
Example B_no_order5 : extends1 [0; 1; 4; 11] 21 = false.
Proof. vm_compute. reflexivity. Qed.
(* AM5 = {1, 2, 4, 8, 13} — Sidon, non-extending at orders 5,6. *)
Example AM5_sidon : nodupZ (diffsZ [1%Z; 2%Z; 4%Z; 8%Z; 13%Z]) = true.
Proof. vm_compute. reflexivity. Qed.
Example AM5_no_order5 : isPDS [1; 2; 4; 8; 13] 21 = false.
Proof. vm_compute. reflexivity. Qed.
Example AM5_no_order6 : extends1 [1; 2; 4; 8; 13] 31 = false.
Proof. vm_compute. reflexivity. Qed.
(* Hall = {1, 3, 9, 10, 13} — Sidon, non-extending at orders 5,6. *)
Example Hall_sidon : nodupZ (diffsZ [1%Z; 3%Z; 9%Z; 10%Z; 13%Z]) = true.
Proof. vm_compute. reflexivity. Qed.
Example Hall_no_order5 : isPDS [1; 3; 9; 10; 13] 21 = false.
Proof. vm_compute. reflexivity. Qed.
Example Hall_no_order6 : extends1 [1; 3; 9; 10; 13] 31 = false.
Proof. vm_compute. reflexivity. Qed.
