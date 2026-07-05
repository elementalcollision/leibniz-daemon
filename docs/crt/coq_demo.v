(*
  ADR 0048 — Coq / Rocq proof-edge decider, demonstration certificate.

  Real theorems, checked by the Rocq 9.0 kernel through leibniz.backends.coq_docker (report-only; the
  backend never touches Demonstratio.kernel_verified). Each theorem audits its own axiom footprint with
  `Print Assumptions` — the Coq analogue of Lean's `#print axioms`; a genuine proof reports
  "Closed under the global context" (no axioms). An `Admitted` proof would instead expose the theorem as
  an open axiom, which the backend rejects. Verification-amplification; no trust surface touched.
*)
Require Import Arith.
Require Import List.
Import ListNotations.

(* Addition on nat is commutative — by induction. *)
Theorem add_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m. induction n as [| n IH]; simpl.
  - rewrite <- plus_n_O. reflexivity.
  - rewrite IH. rewrite plus_n_Sm. reflexivity.
Qed.
Print Assumptions add_comm.

(* List append is associative — by induction on the first list. *)
Theorem app_assoc : forall (A : Type) (l m n : list A),
  (l ++ m) ++ n = l ++ (m ++ n).
Proof.
  intros A l m n. induction l as [| x xs IH]; simpl.
  - reflexivity.
  - rewrite IH. reflexivity.
Qed.
Print Assumptions app_assoc.

(* Reversing a list twice is the identity — by induction, via rev_app_distr. *)
Theorem rev_involutive : forall (A : Type) (l : list A), rev (rev l) = l.
Proof.
  intros A l. induction l as [| x xs IH]; simpl.
  - reflexivity.
  - rewrite rev_app_distr. rewrite IH. reflexivity.
Qed.
Print Assumptions rev_involutive.
