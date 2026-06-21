"""Structural trust-boundary guards (pure stdlib; always run in CI).

These complement test_invariants.py by pinning *who may write* the two most
security-relevant fields, so a stray writer added during a later rung's backend
wiring is caught mechanically rather than by review alone:

- ``kernel_verified`` must be assigned only in LeanVerifier.discharge
  (CLAUDE.md invariant 1; the R1 "no second kernel writer" guard).
- ``promulgated = True`` must be set only in the two promotion paths that route
  through TrustPolicy (the R5 write-guard risk, pulled forward).
"""
from __future__ import annotations

import ast
import pathlib

_PKG = pathlib.Path(__file__).resolve().parent.parent / "leibniz"


class _AttrAssignFinder(ast.NodeVisitor):
    """Record (function-name) of every `<something>.<attr> = ...` assignment."""

    def __init__(self, attr: str) -> None:
        self.attr = attr
        self._funcs: list[str] = []
        self.hits: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._funcs.append(node.name)
        self.generic_visit(node)
        self._funcs.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == self.attr:
                self.hits.append(self._funcs[-1] if self._funcs else "<module>")
        self.generic_visit(node)


def _writers(attr: str) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in _PKG.rglob("*.py"):
        finder = _AttrAssignFinder(attr)
        finder.visit(ast.parse(path.read_text()))
        for func in finder.hits:
            found.add((str(path.relative_to(_PKG)), func))
    return found


def test_kernel_verified_has_a_single_writer():
    # Only LeanVerifier.discharge may set kernel_verified. No backend, cache, or
    # retry path may write it directly.
    assert _writers("kernel_verified") == {("verifiers.py", "discharge")}


def test_promulgated_is_set_only_in_policy_routed_paths():
    # Promulgate.run and VerificationGate.finalize both gate on is_promotable ->
    # TrustPolicy.validate_path. A new writer here would bypass the policy.
    assert _writers("promulgated") == {
        ("pipeline.py", "run"),
        ("gates/verification.py", "finalize"),
    }


class _ProofEdgeConstructorFinder(ast.NodeVisitor):
    """Record every function that constructs ``EdgeEvidence(edge=PROOF_EDGE, ...)``
    (literal PROOF_EDGE, positional or keyword)."""

    def __init__(self) -> None:
        self._funcs: list[str] = []
        self.hits: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._funcs.append(node.name)
        self.generic_visit(node)
        self._funcs.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "EdgeEvidence":
            edge_val = node.args[0] if node.args else None
            for kw in node.keywords:
                if kw.arg == "edge":
                    edge_val = kw.value
            if isinstance(edge_val, ast.Name) and edge_val.id == "PROOF_EDGE":
                self.hits.append(self._funcs[-1] if self._funcs else "<module>")
        self.generic_visit(node)


def test_proof_edge_is_constructed_only_in_kernel_paths():
    # ADR 0013 §3: bound WHO may mint a proof edge. Only LeanVerifier.discharge
    # (the kernel) and ProofConsensus.prove (which copies discharge's edge) may
    # construct an EdgeEvidence on PROOF_EDGE. Any other construction site would let
    # a non-kernel verdict masquerade as a proof — caught here structurally, closing
    # the producer=None gap that the runtime provenance check alone cannot.
    found: set[tuple[str, str]] = set()
    for path in _PKG.rglob("*.py"):
        finder = _ProofEdgeConstructorFinder()
        finder.visit(ast.parse(path.read_text()))
        for func in finder.hits:
            found.add((str(path.relative_to(_PKG)), func))
    assert found == {("verifiers.py", "discharge"), ("consensus.py", "prove")}
