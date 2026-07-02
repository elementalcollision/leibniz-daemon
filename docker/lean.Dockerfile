# Reproducible Lean 4 kernel environment for Leibniz R1 (ADR 0003).
#
# The pure-stdlib Leibniz daemon runs on the host (Python 3.14+); the Lean kernel
# lives here in the container (where LeanDojo, later, needs Python <3.12). R1a is
# core Lean only — Mathlib is added as a lake dependency in R1b.
#
# Build (from repo root):  docker build -f docker/lean.Dockerfile -t leibniz-lean:v4.31.0 .
# Smoke:                   docker run --rm leibniz-lean:v4.31.0 lake env lean --version
FROM debian:bookworm-slim

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# elan = Lean's toolchain manager. The exact Lean version is pinned by the
# project's lean-toolchain file (leanprover/lean4:v4.31.0), not here.
RUN curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -o /tmp/elan-init.sh \
 && sh /tmp/elan-init.sh -y --default-toolchain none \
 && rm /tmp/elan-init.sh
ENV PATH="/root/.elan/bin:${PATH}"

WORKDIR /work/lean-project
COPY lean-project/ /work/lean-project/

# elan auto-installs the toolchain named in lean-toolchain. Resolve + fetch the
# Mathlib dependency, pull its prebuilt oleans (never cold-compile Mathlib), then
# build our lib so the kernel + olean cache are baked into the image.
RUN lake update \
 && lake exe cache get \
 && lake build

# The cache tarballs ship per-module oleans but NOT the umbrella Mathlib.olean, so
# `import Mathlib` — the pipeline's default import set — fails: loudly under
# `lake env lean`, SILENTLY in the repl (it returns a coreless env with no error).
# Elaborate the umbrella explicitly (~15s warm; also fills in Batteries.olean).
RUN lake build Mathlib

CMD ["bash"]
