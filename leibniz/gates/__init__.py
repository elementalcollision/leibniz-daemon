"""Decision gates: faithfulness, novelty, verification.

Each gate returns an EdgeEvidence with an honest TrustTier; the policy and the
invariant tests read that tier. A gate may quarantine a candidate but never
promote one — promotion is the VerificationGate's pure-function verdict.
"""
