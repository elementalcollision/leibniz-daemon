# Lean REPL image for Leibniz throughput (ADR 0011). Layers the leanprover-community
# REPL on top of the kernel image so Mathlib imports load ONCE per long-lived process
# instead of per `lake env lean` invocation.
#
# Build (from repo root):  docker build -f docker/lean-repl.Dockerfile -t leibniz-lean-repl:v4.31.0 .
# The base provides the pinned toolchain + Mathlib oleans; this only adds the repl exe.
FROM leibniz-lean:v4.31.0

RUN cd /work \
 && git clone --depth 1 --branch v4.31.0 https://github.com/leanprover-community/repl.git \
 && cd repl && lake build

# Run from the lean-project so `lake env` puts Mathlib on the repl's LEAN_PATH.
WORKDIR /work/lean-project
CMD ["bash", "-lc", "lake env /work/repl/.lake/build/bin/repl"]
