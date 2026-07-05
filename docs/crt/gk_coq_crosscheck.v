(*
  Guo–Krattenthaler binomial divisibilities — independent SECOND-KERNEL confirmation (ADR 0048).
  The exact instances Leibniz's Lean 4.31 census (PR #293) decided, re-decided here by the Rocq 9.0
  kernel over binary N, each `vm_compute; reflexivity`. Axiom-free: the rocqchk whole-development audit
  reports `* Axioms: <none>`. Report-only cross-check; no trust surface. Produced by
  scripts/verify_gk_crosskernel.py.
*)
Require Import NArith.
Open Scope N_scope.

(* exact incremental binomial over binary N: C(n,i) = C(n,i-1) * (n-(i-1)) / i (each partial an integer) *)
Fixpoint binom_from (n : N) (i j : nat) (acc : N) : N :=
  match j with
  | O => acc
  | S j' => binom_from n (S i) j' (acc * (n - N.of_nat i) / N.of_nat (S i))
  end.
Definition binom (n : N) (k : nat) : N := binom_from n O k 1.

(* (5) | C(12,3) — Lean-decided in #293 *)
Example div_12_3_n1 : (binom 12 3) mod 5 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (11) | C(24,6) — Lean-decided in #293 *)
Example div_12_3_n2 : (binom 24 6) mod 11 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (17) | C(36,9) — Lean-decided in #293 *)
Example div_12_3_n3 : (binom 36 9) mod 17 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (23) | C(48,12) — Lean-decided in #293 *)
Example div_12_3_n4 : (binom 48 12) mod 23 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (29) | C(60,15) — Lean-decided in #293 *)
Example div_12_3_n5 : (binom 60 15) mod 29 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (35) | C(72,18) — Lean-decided in #293 *)
Example div_12_3_n6 : (binom 72 18) mod 35 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (41) | C(84,21) — Lean-decided in #293 *)
Example div_12_3_n7 : (binom 84 21) mod 41 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (47) | C(96,24) — Lean-decided in #293 *)
Example div_12_3_n8 : (binom 96 24) mod 47 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (5) | C(12,4) — Lean-decided in #293 *)
Example div_12_4_n1 : (binom 12 4) mod 5 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (11) | C(24,8) — Lean-decided in #293 *)
Example div_12_4_n2 : (binom 24 8) mod 11 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (17) | C(36,12) — Lean-decided in #293 *)
Example div_12_4_n3 : (binom 36 12) mod 17 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (23) | C(48,16) — Lean-decided in #293 *)
Example div_12_4_n4 : (binom 48 16) mod 23 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (29) | C(60,20) — Lean-decided in #293 *)
Example div_12_4_n5 : (binom 60 20) mod 29 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (35) | C(72,24) — Lean-decided in #293 *)
Example div_12_4_n6 : (binom 72 24) mod 35 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (41) | C(84,28) — Lean-decided in #293 *)
Example div_12_4_n7 : (binom 84 28) mod 41 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (47) | C(96,32) — Lean-decided in #293 *)
Example div_12_4_n8 : (binom 96 32) mod 47 = 0.
Proof. vm_compute. reflexivity. Qed.
(* (65) | C(330,88) — Lean-decided in #293 *)
Example div_330_88_n1 : (binom 330 88) mod 65 = 0.
Proof. vm_compute. reflexivity. Qed.
