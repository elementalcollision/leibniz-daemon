/-
Covering system with minimum modulus 7 and least common multiple 10080.

SOURCE  Zhang, S. & Zhang, J. (2026). A Distinct Covering System with Minimum Modulus 7 and
        Minimal Least Common Multiple 10080. arXiv:2607.19029, Section 7.

WHAT THIS FILE ESTABLISHES -- and what it does NOT.

  ESTABLISHED, by the Lean kernel: the 66 congruence classes below cover every
  integer n with 0 <= n. Their moduli are distinct, the least is 7, and their least
  common multiple is exactly 10080. This is the CONSTRUCTION half of the paper's Theorem 1.

  NOT ESTABLISHED HERE: that 10080 is MINIMAL -- the paper's actual theorem, L_min(7) = 10080.
  That direction rules out every smaller lcm and rests on complete Gurobi computations; nothing
  in this file speaks to it. Amplifying it is not in reach.

  Two further honesties. The statement is the daemon's canonical Z-box law, so it quantifies over
  0 <= n rather than all of Z; the system is periodic mod 10080, so covering the non-negatives does
  imply covering Z, but the KERNEL decided the boxed form and only that. And the congruence list
  was transcribed from the paper's PDF and verified exhaustively in Python (distinct moduli,
  minimum 7, lcm 10080, zero uncovered residues) before being handed to Lean.

PROVENANCE  Theorem and proof are GENERATED, not hand-written: leibniz.providers
        .mixed_modulus_prover.mixed_law renders the canonical law and the ADR 0060 LCM/castHom
        proof (decide over ZMod 10080, one intCast bridge per atom). Reproduce with
        scripts/export_covering10080_law.py.

NOTE  The paper's exhibited system contains a REDUNDANT congruence: dropping 233 (mod 1120)
      leaves 65 classes that still cover Z with distinct moduli, minimum modulus 7 and lcm 10080.
      That is not an error -- the paper's theorem is about the minimal lcm, not an irredundant
      witness -- but it refuted an earlier non-triviality criterion (see ADR 0089) and is recorded
      here so the next reader does not rediscover it as a defect.
-/
import Mathlib

theorem covering_min_modulus_7_lcm_10080 : ∀ (n : ℤ), (0 ≤ n) → (n ≥ 0) → (((Int.emod n 7) = 6) ∨ ((Int.emod n 8) = 7) ∨ ((Int.emod n 9) = 8) ∨ ((Int.emod n 10) = 6) ∨ ((Int.emod n 12) = 9) ∨ ((Int.emod n 14) = 8) ∨ ((Int.emod n 15) = 12) ∨ ((Int.emod n 16) = 3) ∨ ((Int.emod n 18) = 14) ∨ ((Int.emod n 20) = 0) ∨ ((Int.emod n 21) = 4) ∨ ((Int.emod n 24) = 13) ∨ ((Int.emod n 28) = 26) ∨ ((Int.emod n 30) = 24) ∨ ((Int.emod n 32) = 27) ∨ ((Int.emod n 35) = 33) ∨ ((Int.emod n 36) = 5) ∨ ((Int.emod n 40) = 11) ∨ ((Int.emod n 42) = 16) ∨ ((Int.emod n 45) = 2) ∨ ((Int.emod n 48) = 1) ∨ ((Int.emod n 56) = 52) ∨ ((Int.emod n 60) = 30) ∨ ((Int.emod n 63) = 7) ∨ ((Int.emod n 70) = 28) ∨ ((Int.emod n 72) = 29) ∨ ((Int.emod n 80) = 59) ∨ ((Int.emod n 84) = 10) ∨ ((Int.emod n 90) = 74) ∨ ((Int.emod n 96) = 43) ∨ ((Int.emod n 105) = 93) ∨ ((Int.emod n 112) = 73) ∨ ((Int.emod n 120) = 64) ∨ ((Int.emod n 126) = 112) ∨ ((Int.emod n 140) = 38) ∨ ((Int.emod n 144) = 65) ∨ ((Int.emod n 160) = 43) ∨ ((Int.emod n 168) = 121) ∨ ((Int.emod n 180) = 110) ∨ ((Int.emod n 210) = 18) ∨ ((Int.emod n 224) = 169) ∨ ((Int.emod n 240) = 185) ∨ ((Int.emod n 252) = 154) ∨ ((Int.emod n 280) = 248) ∨ ((Int.emod n 288) = 203) ∨ ((Int.emod n 315) = 128) ∨ ((Int.emod n 336) = 313) ∨ ((Int.emod n 360) = 209) ∨ ((Int.emod n 420) = 292) ∨ ((Int.emod n 480) = 75) ∨ ((Int.emod n 504) = 217) ∨ ((Int.emod n 560) = 404) ∨ ((Int.emod n 630) = 578) ∨ ((Int.emod n 672) = 505) ∨ ((Int.emod n 720) = 281) ∨ ((Int.emod n 840) = 472) ∨ ((Int.emod n 1008) = 553) ∨ ((Int.emod n 1120) = 233) ∨ ((Int.emod n 1260) = 532) ∨ ((Int.emod n 1440) = 875) ∨ ((Int.emod n 1680) = 124) ∨ ((Int.emod n 2016) = 281) ∨ ((Int.emod n 2520) = 2044) ∨ ((Int.emod n 3360) = 2153) ∨ ((Int.emod n 5040) = 5033) ∨ ((Int.emod n 10080) = 7193)) := by
  intro n _ _
  have key : ∀ (n : ZMod 10080), (((ZMod.castHom (show (7:ℕ) ∣ 10080 by decide) (ZMod 7)) (n) = 6) ∨ ((ZMod.castHom (show (8:ℕ) ∣ 10080 by decide) (ZMod 8)) (n) = 7) ∨ ((ZMod.castHom (show (9:ℕ) ∣ 10080 by decide) (ZMod 9)) (n) = 8) ∨ ((ZMod.castHom (show (10:ℕ) ∣ 10080 by decide) (ZMod 10)) (n) = 6) ∨ ((ZMod.castHom (show (12:ℕ) ∣ 10080 by decide) (ZMod 12)) (n) = 9) ∨ ((ZMod.castHom (show (14:ℕ) ∣ 10080 by decide) (ZMod 14)) (n) = 8) ∨ ((ZMod.castHom (show (15:ℕ) ∣ 10080 by decide) (ZMod 15)) (n) = 12) ∨ ((ZMod.castHom (show (16:ℕ) ∣ 10080 by decide) (ZMod 16)) (n) = 3) ∨ ((ZMod.castHom (show (18:ℕ) ∣ 10080 by decide) (ZMod 18)) (n) = 14) ∨ ((ZMod.castHom (show (20:ℕ) ∣ 10080 by decide) (ZMod 20)) (n) = 0) ∨ ((ZMod.castHom (show (21:ℕ) ∣ 10080 by decide) (ZMod 21)) (n) = 4) ∨ ((ZMod.castHom (show (24:ℕ) ∣ 10080 by decide) (ZMod 24)) (n) = 13) ∨ ((ZMod.castHom (show (28:ℕ) ∣ 10080 by decide) (ZMod 28)) (n) = 26) ∨ ((ZMod.castHom (show (30:ℕ) ∣ 10080 by decide) (ZMod 30)) (n) = 24) ∨ ((ZMod.castHom (show (32:ℕ) ∣ 10080 by decide) (ZMod 32)) (n) = 27) ∨ ((ZMod.castHom (show (35:ℕ) ∣ 10080 by decide) (ZMod 35)) (n) = 33) ∨ ((ZMod.castHom (show (36:ℕ) ∣ 10080 by decide) (ZMod 36)) (n) = 5) ∨ ((ZMod.castHom (show (40:ℕ) ∣ 10080 by decide) (ZMod 40)) (n) = 11) ∨ ((ZMod.castHom (show (42:ℕ) ∣ 10080 by decide) (ZMod 42)) (n) = 16) ∨ ((ZMod.castHom (show (45:ℕ) ∣ 10080 by decide) (ZMod 45)) (n) = 2) ∨ ((ZMod.castHom (show (48:ℕ) ∣ 10080 by decide) (ZMod 48)) (n) = 1) ∨ ((ZMod.castHom (show (56:ℕ) ∣ 10080 by decide) (ZMod 56)) (n) = 52) ∨ ((ZMod.castHom (show (60:ℕ) ∣ 10080 by decide) (ZMod 60)) (n) = 30) ∨ ((ZMod.castHom (show (63:ℕ) ∣ 10080 by decide) (ZMod 63)) (n) = 7) ∨ ((ZMod.castHom (show (70:ℕ) ∣ 10080 by decide) (ZMod 70)) (n) = 28) ∨ ((ZMod.castHom (show (72:ℕ) ∣ 10080 by decide) (ZMod 72)) (n) = 29) ∨ ((ZMod.castHom (show (80:ℕ) ∣ 10080 by decide) (ZMod 80)) (n) = 59) ∨ ((ZMod.castHom (show (84:ℕ) ∣ 10080 by decide) (ZMod 84)) (n) = 10) ∨ ((ZMod.castHom (show (90:ℕ) ∣ 10080 by decide) (ZMod 90)) (n) = 74) ∨ ((ZMod.castHom (show (96:ℕ) ∣ 10080 by decide) (ZMod 96)) (n) = 43) ∨ ((ZMod.castHom (show (105:ℕ) ∣ 10080 by decide) (ZMod 105)) (n) = 93) ∨ ((ZMod.castHom (show (112:ℕ) ∣ 10080 by decide) (ZMod 112)) (n) = 73) ∨ ((ZMod.castHom (show (120:ℕ) ∣ 10080 by decide) (ZMod 120)) (n) = 64) ∨ ((ZMod.castHom (show (126:ℕ) ∣ 10080 by decide) (ZMod 126)) (n) = 112) ∨ ((ZMod.castHom (show (140:ℕ) ∣ 10080 by decide) (ZMod 140)) (n) = 38) ∨ ((ZMod.castHom (show (144:ℕ) ∣ 10080 by decide) (ZMod 144)) (n) = 65) ∨ ((ZMod.castHom (show (160:ℕ) ∣ 10080 by decide) (ZMod 160)) (n) = 43) ∨ ((ZMod.castHom (show (168:ℕ) ∣ 10080 by decide) (ZMod 168)) (n) = 121) ∨ ((ZMod.castHom (show (180:ℕ) ∣ 10080 by decide) (ZMod 180)) (n) = 110) ∨ ((ZMod.castHom (show (210:ℕ) ∣ 10080 by decide) (ZMod 210)) (n) = 18) ∨ ((ZMod.castHom (show (224:ℕ) ∣ 10080 by decide) (ZMod 224)) (n) = 169) ∨ ((ZMod.castHom (show (240:ℕ) ∣ 10080 by decide) (ZMod 240)) (n) = 185) ∨ ((ZMod.castHom (show (252:ℕ) ∣ 10080 by decide) (ZMod 252)) (n) = 154) ∨ ((ZMod.castHom (show (280:ℕ) ∣ 10080 by decide) (ZMod 280)) (n) = 248) ∨ ((ZMod.castHom (show (288:ℕ) ∣ 10080 by decide) (ZMod 288)) (n) = 203) ∨ ((ZMod.castHom (show (315:ℕ) ∣ 10080 by decide) (ZMod 315)) (n) = 128) ∨ ((ZMod.castHom (show (336:ℕ) ∣ 10080 by decide) (ZMod 336)) (n) = 313) ∨ ((ZMod.castHom (show (360:ℕ) ∣ 10080 by decide) (ZMod 360)) (n) = 209) ∨ ((ZMod.castHom (show (420:ℕ) ∣ 10080 by decide) (ZMod 420)) (n) = 292) ∨ ((ZMod.castHom (show (480:ℕ) ∣ 10080 by decide) (ZMod 480)) (n) = 75) ∨ ((ZMod.castHom (show (504:ℕ) ∣ 10080 by decide) (ZMod 504)) (n) = 217) ∨ ((ZMod.castHom (show (560:ℕ) ∣ 10080 by decide) (ZMod 560)) (n) = 404) ∨ ((ZMod.castHom (show (630:ℕ) ∣ 10080 by decide) (ZMod 630)) (n) = 578) ∨ ((ZMod.castHom (show (672:ℕ) ∣ 10080 by decide) (ZMod 672)) (n) = 505) ∨ ((ZMod.castHom (show (720:ℕ) ∣ 10080 by decide) (ZMod 720)) (n) = 281) ∨ ((ZMod.castHom (show (840:ℕ) ∣ 10080 by decide) (ZMod 840)) (n) = 472) ∨ ((ZMod.castHom (show (1008:ℕ) ∣ 10080 by decide) (ZMod 1008)) (n) = 553) ∨ ((ZMod.castHom (show (1120:ℕ) ∣ 10080 by decide) (ZMod 1120)) (n) = 233) ∨ ((ZMod.castHom (show (1260:ℕ) ∣ 10080 by decide) (ZMod 1260)) (n) = 532) ∨ ((ZMod.castHom (show (1440:ℕ) ∣ 10080 by decide) (ZMod 1440)) (n) = 875) ∨ ((ZMod.castHom (show (1680:ℕ) ∣ 10080 by decide) (ZMod 1680)) (n) = 124) ∨ ((ZMod.castHom (show (2016:ℕ) ∣ 10080 by decide) (ZMod 2016)) (n) = 281) ∨ ((ZMod.castHom (show (2520:ℕ) ∣ 10080 by decide) (ZMod 2520)) (n) = 2044) ∨ ((ZMod.castHom (show (3360:ℕ) ∣ 10080 by decide) (ZMod 3360)) (n) = 2153) ∨ ((ZMod.castHom (show (5040:ℕ) ∣ 10080 by decide) (ZMod 5040)) (n) = 5033) ∨ (n = 7193)) := by
    set_option maxRecDepth 1000000 in
    set_option synthInstance.maxSize 4000 in
    set_option synthInstance.maxHeartbeats 4000000 in
    decide +kernel
  have hm0 : (Int.emod (n) 7 = 6) ↔ (((n : ℤ) : ZMod 7) = ((6:ℤ):ZMod 7)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 7 = 6) ↔ ((n) % 7 = 6 % 7)
    omega
  have hm1 : (Int.emod (n) 8 = 7) ↔ (((n : ℤ) : ZMod 8) = ((7:ℤ):ZMod 8)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 8 = 7) ↔ ((n) % 8 = 7 % 8)
    omega
  have hm2 : (Int.emod (n) 9 = 8) ↔ (((n : ℤ) : ZMod 9) = ((8:ℤ):ZMod 9)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 9 = 8) ↔ ((n) % 9 = 8 % 9)
    omega
  have hm3 : (Int.emod (n) 10 = 6) ↔ (((n : ℤ) : ZMod 10) = ((6:ℤ):ZMod 10)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 10 = 6) ↔ ((n) % 10 = 6 % 10)
    omega
  have hm4 : (Int.emod (n) 12 = 9) ↔ (((n : ℤ) : ZMod 12) = ((9:ℤ):ZMod 12)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 12 = 9) ↔ ((n) % 12 = 9 % 12)
    omega
  have hm5 : (Int.emod (n) 14 = 8) ↔ (((n : ℤ) : ZMod 14) = ((8:ℤ):ZMod 14)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 14 = 8) ↔ ((n) % 14 = 8 % 14)
    omega
  have hm6 : (Int.emod (n) 15 = 12) ↔ (((n : ℤ) : ZMod 15) = ((12:ℤ):ZMod 15)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 15 = 12) ↔ ((n) % 15 = 12 % 15)
    omega
  have hm7 : (Int.emod (n) 16 = 3) ↔ (((n : ℤ) : ZMod 16) = ((3:ℤ):ZMod 16)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 16 = 3) ↔ ((n) % 16 = 3 % 16)
    omega
  have hm8 : (Int.emod (n) 18 = 14) ↔ (((n : ℤ) : ZMod 18) = ((14:ℤ):ZMod 18)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 18 = 14) ↔ ((n) % 18 = 14 % 18)
    omega
  have hm9 : (Int.emod (n) 20 = 0) ↔ (((n : ℤ) : ZMod 20) = ((0:ℤ):ZMod 20)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 20 = 0) ↔ ((n) % 20 = 0 % 20)
    omega
  have hm10 : (Int.emod (n) 21 = 4) ↔ (((n : ℤ) : ZMod 21) = ((4:ℤ):ZMod 21)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 21 = 4) ↔ ((n) % 21 = 4 % 21)
    omega
  have hm11 : (Int.emod (n) 24 = 13) ↔ (((n : ℤ) : ZMod 24) = ((13:ℤ):ZMod 24)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 24 = 13) ↔ ((n) % 24 = 13 % 24)
    omega
  have hm12 : (Int.emod (n) 28 = 26) ↔ (((n : ℤ) : ZMod 28) = ((26:ℤ):ZMod 28)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 28 = 26) ↔ ((n) % 28 = 26 % 28)
    omega
  have hm13 : (Int.emod (n) 30 = 24) ↔ (((n : ℤ) : ZMod 30) = ((24:ℤ):ZMod 30)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 30 = 24) ↔ ((n) % 30 = 24 % 30)
    omega
  have hm14 : (Int.emod (n) 32 = 27) ↔ (((n : ℤ) : ZMod 32) = ((27:ℤ):ZMod 32)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 32 = 27) ↔ ((n) % 32 = 27 % 32)
    omega
  have hm15 : (Int.emod (n) 35 = 33) ↔ (((n : ℤ) : ZMod 35) = ((33:ℤ):ZMod 35)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 35 = 33) ↔ ((n) % 35 = 33 % 35)
    omega
  have hm16 : (Int.emod (n) 36 = 5) ↔ (((n : ℤ) : ZMod 36) = ((5:ℤ):ZMod 36)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 36 = 5) ↔ ((n) % 36 = 5 % 36)
    omega
  have hm17 : (Int.emod (n) 40 = 11) ↔ (((n : ℤ) : ZMod 40) = ((11:ℤ):ZMod 40)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 40 = 11) ↔ ((n) % 40 = 11 % 40)
    omega
  have hm18 : (Int.emod (n) 42 = 16) ↔ (((n : ℤ) : ZMod 42) = ((16:ℤ):ZMod 42)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 42 = 16) ↔ ((n) % 42 = 16 % 42)
    omega
  have hm19 : (Int.emod (n) 45 = 2) ↔ (((n : ℤ) : ZMod 45) = ((2:ℤ):ZMod 45)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 45 = 2) ↔ ((n) % 45 = 2 % 45)
    omega
  have hm20 : (Int.emod (n) 48 = 1) ↔ (((n : ℤ) : ZMod 48) = ((1:ℤ):ZMod 48)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 48 = 1) ↔ ((n) % 48 = 1 % 48)
    omega
  have hm21 : (Int.emod (n) 56 = 52) ↔ (((n : ℤ) : ZMod 56) = ((52:ℤ):ZMod 56)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 56 = 52) ↔ ((n) % 56 = 52 % 56)
    omega
  have hm22 : (Int.emod (n) 60 = 30) ↔ (((n : ℤ) : ZMod 60) = ((30:ℤ):ZMod 60)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 60 = 30) ↔ ((n) % 60 = 30 % 60)
    omega
  have hm23 : (Int.emod (n) 63 = 7) ↔ (((n : ℤ) : ZMod 63) = ((7:ℤ):ZMod 63)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 63 = 7) ↔ ((n) % 63 = 7 % 63)
    omega
  have hm24 : (Int.emod (n) 70 = 28) ↔ (((n : ℤ) : ZMod 70) = ((28:ℤ):ZMod 70)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 70 = 28) ↔ ((n) % 70 = 28 % 70)
    omega
  have hm25 : (Int.emod (n) 72 = 29) ↔ (((n : ℤ) : ZMod 72) = ((29:ℤ):ZMod 72)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 72 = 29) ↔ ((n) % 72 = 29 % 72)
    omega
  have hm26 : (Int.emod (n) 80 = 59) ↔ (((n : ℤ) : ZMod 80) = ((59:ℤ):ZMod 80)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 80 = 59) ↔ ((n) % 80 = 59 % 80)
    omega
  have hm27 : (Int.emod (n) 84 = 10) ↔ (((n : ℤ) : ZMod 84) = ((10:ℤ):ZMod 84)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 84 = 10) ↔ ((n) % 84 = 10 % 84)
    omega
  have hm28 : (Int.emod (n) 90 = 74) ↔ (((n : ℤ) : ZMod 90) = ((74:ℤ):ZMod 90)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 90 = 74) ↔ ((n) % 90 = 74 % 90)
    omega
  have hm29 : (Int.emod (n) 96 = 43) ↔ (((n : ℤ) : ZMod 96) = ((43:ℤ):ZMod 96)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 96 = 43) ↔ ((n) % 96 = 43 % 96)
    omega
  have hm30 : (Int.emod (n) 105 = 93) ↔ (((n : ℤ) : ZMod 105) = ((93:ℤ):ZMod 105)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 105 = 93) ↔ ((n) % 105 = 93 % 105)
    omega
  have hm31 : (Int.emod (n) 112 = 73) ↔ (((n : ℤ) : ZMod 112) = ((73:ℤ):ZMod 112)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 112 = 73) ↔ ((n) % 112 = 73 % 112)
    omega
  have hm32 : (Int.emod (n) 120 = 64) ↔ (((n : ℤ) : ZMod 120) = ((64:ℤ):ZMod 120)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 120 = 64) ↔ ((n) % 120 = 64 % 120)
    omega
  have hm33 : (Int.emod (n) 126 = 112) ↔ (((n : ℤ) : ZMod 126) = ((112:ℤ):ZMod 126)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 126 = 112) ↔ ((n) % 126 = 112 % 126)
    omega
  have hm34 : (Int.emod (n) 140 = 38) ↔ (((n : ℤ) : ZMod 140) = ((38:ℤ):ZMod 140)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 140 = 38) ↔ ((n) % 140 = 38 % 140)
    omega
  have hm35 : (Int.emod (n) 144 = 65) ↔ (((n : ℤ) : ZMod 144) = ((65:ℤ):ZMod 144)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 144 = 65) ↔ ((n) % 144 = 65 % 144)
    omega
  have hm36 : (Int.emod (n) 160 = 43) ↔ (((n : ℤ) : ZMod 160) = ((43:ℤ):ZMod 160)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 160 = 43) ↔ ((n) % 160 = 43 % 160)
    omega
  have hm37 : (Int.emod (n) 168 = 121) ↔ (((n : ℤ) : ZMod 168) = ((121:ℤ):ZMod 168)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 168 = 121) ↔ ((n) % 168 = 121 % 168)
    omega
  have hm38 : (Int.emod (n) 180 = 110) ↔ (((n : ℤ) : ZMod 180) = ((110:ℤ):ZMod 180)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 180 = 110) ↔ ((n) % 180 = 110 % 180)
    omega
  have hm39 : (Int.emod (n) 210 = 18) ↔ (((n : ℤ) : ZMod 210) = ((18:ℤ):ZMod 210)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 210 = 18) ↔ ((n) % 210 = 18 % 210)
    omega
  have hm40 : (Int.emod (n) 224 = 169) ↔ (((n : ℤ) : ZMod 224) = ((169:ℤ):ZMod 224)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 224 = 169) ↔ ((n) % 224 = 169 % 224)
    omega
  have hm41 : (Int.emod (n) 240 = 185) ↔ (((n : ℤ) : ZMod 240) = ((185:ℤ):ZMod 240)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 240 = 185) ↔ ((n) % 240 = 185 % 240)
    omega
  have hm42 : (Int.emod (n) 252 = 154) ↔ (((n : ℤ) : ZMod 252) = ((154:ℤ):ZMod 252)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 252 = 154) ↔ ((n) % 252 = 154 % 252)
    omega
  have hm43 : (Int.emod (n) 280 = 248) ↔ (((n : ℤ) : ZMod 280) = ((248:ℤ):ZMod 280)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 280 = 248) ↔ ((n) % 280 = 248 % 280)
    omega
  have hm44 : (Int.emod (n) 288 = 203) ↔ (((n : ℤ) : ZMod 288) = ((203:ℤ):ZMod 288)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 288 = 203) ↔ ((n) % 288 = 203 % 288)
    omega
  have hm45 : (Int.emod (n) 315 = 128) ↔ (((n : ℤ) : ZMod 315) = ((128:ℤ):ZMod 315)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 315 = 128) ↔ ((n) % 315 = 128 % 315)
    omega
  have hm46 : (Int.emod (n) 336 = 313) ↔ (((n : ℤ) : ZMod 336) = ((313:ℤ):ZMod 336)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 336 = 313) ↔ ((n) % 336 = 313 % 336)
    omega
  have hm47 : (Int.emod (n) 360 = 209) ↔ (((n : ℤ) : ZMod 360) = ((209:ℤ):ZMod 360)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 360 = 209) ↔ ((n) % 360 = 209 % 360)
    omega
  have hm48 : (Int.emod (n) 420 = 292) ↔ (((n : ℤ) : ZMod 420) = ((292:ℤ):ZMod 420)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 420 = 292) ↔ ((n) % 420 = 292 % 420)
    omega
  have hm49 : (Int.emod (n) 480 = 75) ↔ (((n : ℤ) : ZMod 480) = ((75:ℤ):ZMod 480)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 480 = 75) ↔ ((n) % 480 = 75 % 480)
    omega
  have hm50 : (Int.emod (n) 504 = 217) ↔ (((n : ℤ) : ZMod 504) = ((217:ℤ):ZMod 504)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 504 = 217) ↔ ((n) % 504 = 217 % 504)
    omega
  have hm51 : (Int.emod (n) 560 = 404) ↔ (((n : ℤ) : ZMod 560) = ((404:ℤ):ZMod 560)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 560 = 404) ↔ ((n) % 560 = 404 % 560)
    omega
  have hm52 : (Int.emod (n) 630 = 578) ↔ (((n : ℤ) : ZMod 630) = ((578:ℤ):ZMod 630)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 630 = 578) ↔ ((n) % 630 = 578 % 630)
    omega
  have hm53 : (Int.emod (n) 672 = 505) ↔ (((n : ℤ) : ZMod 672) = ((505:ℤ):ZMod 672)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 672 = 505) ↔ ((n) % 672 = 505 % 672)
    omega
  have hm54 : (Int.emod (n) 720 = 281) ↔ (((n : ℤ) : ZMod 720) = ((281:ℤ):ZMod 720)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 720 = 281) ↔ ((n) % 720 = 281 % 720)
    omega
  have hm55 : (Int.emod (n) 840 = 472) ↔ (((n : ℤ) : ZMod 840) = ((472:ℤ):ZMod 840)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 840 = 472) ↔ ((n) % 840 = 472 % 840)
    omega
  have hm56 : (Int.emod (n) 1008 = 553) ↔ (((n : ℤ) : ZMod 1008) = ((553:ℤ):ZMod 1008)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 1008 = 553) ↔ ((n) % 1008 = 553 % 1008)
    omega
  have hm57 : (Int.emod (n) 1120 = 233) ↔ (((n : ℤ) : ZMod 1120) = ((233:ℤ):ZMod 1120)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 1120 = 233) ↔ ((n) % 1120 = 233 % 1120)
    omega
  have hm58 : (Int.emod (n) 1260 = 532) ↔ (((n : ℤ) : ZMod 1260) = ((532:ℤ):ZMod 1260)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 1260 = 532) ↔ ((n) % 1260 = 532 % 1260)
    omega
  have hm59 : (Int.emod (n) 1440 = 875) ↔ (((n : ℤ) : ZMod 1440) = ((875:ℤ):ZMod 1440)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 1440 = 875) ↔ ((n) % 1440 = 875 % 1440)
    omega
  have hm60 : (Int.emod (n) 1680 = 124) ↔ (((n : ℤ) : ZMod 1680) = ((124:ℤ):ZMod 1680)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 1680 = 124) ↔ ((n) % 1680 = 124 % 1680)
    omega
  have hm61 : (Int.emod (n) 2016 = 281) ↔ (((n : ℤ) : ZMod 2016) = ((281:ℤ):ZMod 2016)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 2016 = 281) ↔ ((n) % 2016 = 281 % 2016)
    omega
  have hm62 : (Int.emod (n) 2520 = 2044) ↔ (((n : ℤ) : ZMod 2520) = ((2044:ℤ):ZMod 2520)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 2520 = 2044) ↔ ((n) % 2520 = 2044 % 2520)
    omega
  have hm63 : (Int.emod (n) 3360 = 2153) ↔ (((n : ℤ) : ZMod 3360) = ((2153:ℤ):ZMod 3360)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 3360 = 2153) ↔ ((n) % 3360 = 2153 % 3360)
    omega
  have hm64 : (Int.emod (n) 5040 = 5033) ↔ (((n : ℤ) : ZMod 5040) = ((5033:ℤ):ZMod 5040)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 5040 = 5033) ↔ ((n) % 5040 = 5033 % 5040)
    omega
  have hm65 : (Int.emod (n) 10080 = 7193) ↔ (((n : ℤ) : ZMod 10080) = ((7193:ℤ):ZMod 10080)) := by
    rw [ZMod.intCast_eq_intCast_iff']
    show ((n) % 10080 = 7193) ↔ ((n) % 10080 = 7193 % 10080)
    omega
  rw [hm0, hm1, hm2, hm3, hm4, hm5, hm6, hm7, hm8, hm9, hm10, hm11, hm12, hm13, hm14, hm15, hm16, hm17, hm18, hm19, hm20, hm21, hm22, hm23, hm24, hm25, hm26, hm27, hm28, hm29, hm30, hm31, hm32, hm33, hm34, hm35, hm36, hm37, hm38, hm39, hm40, hm41, hm42, hm43, hm44, hm45, hm46, hm47, hm48, hm49, hm50, hm51, hm52, hm53, hm54, hm55, hm56, hm57, hm58, hm59, hm60, hm61, hm62, hm63, hm64, hm65]
  push_cast
  have hk := key (n : ZMod 10080)
  simp only [map_add, map_sub, map_mul, map_pow, map_intCast, map_neg, map_ofNat, map_one, map_zero] at hk
  exact hk

#print axioms covering_min_modulus_7_lcm_10080
