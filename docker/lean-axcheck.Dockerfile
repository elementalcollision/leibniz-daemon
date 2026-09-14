# ADR 0097 — the compiled axiom reporter.
#
# `#print axioms` is a COMMAND, and a proposer-authored proof in the same file can redefine its
# elaborator (`elab_rules : command | `(#print axioms $i:ident) => ...`) or simply print a
# report-shaped line. Both were demonstrated against the pinned kernel and both yielded
# `kernel_verified=True` on a compiler-trusted proof. This binary answers the same question
# WITHOUT elaborating any proposer syntax: it imports the compiled module and reads the axiom
# closure out of `ConstantInfo` data via `Lean.collectAxioms`, then prints it tagged with a nonce
# the caller supplies. Compiled HERE, at image-build time, so nothing the proposer later writes
# can change what it does.
#
# Layered on the kernel image, so it adds only the executable — no Mathlib rebuild.
# Build:  docker build -f docker/lean-axcheck.Dockerfile -t leibniz-lean-axcheck:v4.34.0-rc2 .
FROM leibniz-lean:v4.34.0-rc2

WORKDIR /work/axcheck
COPY lean-axcheck/ /work/axcheck/
RUN lake build axcheck

WORKDIR /work/lean-project
CMD ["bash"]
