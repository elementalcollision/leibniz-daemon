"""Concrete backends behind the verifier/gate Protocols (the R1+ seams).

These live outside the trust-guarded core on purpose: a backend may only *report*
what a mechanical checker decided. The trust verdicts are still assembled in
leibniz.verifiers / leibniz.gates, and kernel_verified is still written only in
LeanVerifier.discharge.
"""
