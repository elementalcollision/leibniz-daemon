/-!
Leibniz R1 Lean environment (core Lean 4, no Mathlib yet).

The daemon writes candidate theorem files to a scratch dir and runs
`lake env lean <file>` against this pinned toolchain; this library root just
anchors the lake package and doubles as a build-time kernel smoke test.
-/

/-- Sanity theorem: if this compiles, the toolchain and the Lean kernel are wired
correctly inside the container. -/
theorem leibniz_kernel_online : 1 + 1 = 2 := by decide
