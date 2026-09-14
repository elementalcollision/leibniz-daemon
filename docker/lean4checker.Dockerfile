# ADR 0098 — the kernel replay.
#
# `lean-axcheck` reads the axiom closure out of the ENVIRONMENT; it never re-runs the kernel over
# it. ADR 0097 round 8 showed why that is not enough on its own: a `run_cmd` can assemble
# `debug.skipKernelTC` from string fragments at elaboration time and `addDecl` a self-referential
# `unsafe` constant of type `False`. No text scan can see that (there is no string to match) and
# the footprint is genuinely empty, so both existing layers pass it honestly.
#
# `lean4checker` replays a compiled environment through a bare kernel, which is exactly the check
# neither layer performs. On our exploit it exits 1 with
#     lean4checker found a problem in Mint
#     uncaught exception: (kernel) unknown constant 'evilConst'
# because the self-loop cannot be re-added by a kernel that is actually running.
#
# Upstream is pinned to a SHA and carries a two-line patch: Lean v4.34 inserted a
# `maxRecDepth : USize` parameter into `Environment.addDeclCore`, and upstream's newest branch
# targets v4.29. Upstream's own test suite (AddFalse, ReplaceAxiom, the private-conflict cases)
# passes on the patched build -- those tests exist for precisely this attack class, so they are
# the evidence the port is sound rather than merely compiling.
#
# Build:  docker build -f docker/lean4checker.Dockerfile -t leibniz-lean-verify:v4.34.0-rc2 .
# Layered on the axcheck image so ONE compiled olean serves BOTH checks: the axiom
# closure (what the environment says) and the kernel replay (whether the environment
# is one the kernel would accept). They answer different questions; neither subsumes
# the other, and round 8 is the measured proof of that.
FROM leibniz-lean-axcheck:v4.34.0-rc2

ARG LEAN4CHECKER_SHA=91a7f0e8e9dffe927089f5a6edcfeeb8a0e07709

WORKDIR /work
RUN git clone https://github.com/leanprover/lean4checker.git \
 && cd lean4checker \
 && git checkout "${LEAN4CHECKER_SHA}"

COPY docker/patches/lean4checker-v4.34.0-rc2.patch /tmp/
RUN cd /work/lean4checker \
 && git apply --verbose /tmp/lean4checker-v4.34.0-rc2.patch \
 && lake build \
 && lake test          # upstream's own suite must pass on the port, or the image does not build

WORKDIR /work/lean-project
CMD ["bash"]
