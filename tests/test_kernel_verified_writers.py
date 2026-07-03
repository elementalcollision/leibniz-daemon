"""H0 (trust-integrity) — the sole-fresh-writer guard. Enforces the charter invariant that
`Demonstratio.kernel_verified` is written only by sanctioned sites: `LeanVerifier.discharge` MINTS the fresh
verdict from a real kernel check, and `runtime._row_to_prop` only REPLAYS a persisted verdict via the
`Demonstratio` constructor (a recall, not a decision). Any new write site — an attribute assignment
`x.kernel_verified = …` or a constructor kwarg `Demonstratio(kernel_verified=…)` anywhere in `leibniz/` — is a
trust-boundary red flag and fails this guard.

The roadmap critique (2026-07-03) flagged that no mechanical guard enforced this. This is that guard. Pure
AST, CI-safe, no compute. It edits no guarded core file — it only *observes* them."""
from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# The ONLY sanctioned kernel_verified write sites, keyed by (repo-relative path, enclosing qualname, kind) so
# the guard is robust to line-number drift. Adding to this set is itself a trust decision — do not do it lightly.
_WHITELIST = {
    ("leibniz/verifiers.py", "LeanVerifier::discharge", "attr_assign"),  # MINTS the fresh verdict (the kernel check)
    ("leibniz/runtime.py", "_row_to_prop", "ctor_kwarg"),                # REPLAYS a persisted verdict (recall only)
}


def _scan_source(tree: ast.AST, relpath: str) -> set:
    """Every kernel_verified write in one module: attribute assignments and constructor kwargs, with the
    enclosing function/class qualname."""
    sites: set = set()
    stack: list = []

    class V(ast.NodeVisitor):
        def _scoped(self, n):
            stack.append(n.name)
            self.generic_visit(n)
            stack.pop()
        visit_FunctionDef = _scoped
        visit_AsyncFunctionDef = _scoped
        visit_ClassDef = _scoped

        def visit_Assign(self, n):
            for t in n.targets:
                if isinstance(t, ast.Attribute) and t.attr == "kernel_verified":
                    sites.add((relpath, "::".join(stack) or "<module>", "attr_assign"))
            self.generic_visit(n)

        def visit_AnnAssign(self, n):
            if isinstance(n.target, ast.Attribute) and n.target.attr == "kernel_verified" and n.value is not None:
                sites.add((relpath, "::".join(stack) or "<module>", "attr_assign"))
            self.generic_visit(n)

        def visit_Call(self, n):
            for kw in n.keywords:
                if kw.arg == "kernel_verified":
                    sites.add((relpath, "::".join(stack) or "<module>", "ctor_kwarg"))
            self.generic_visit(n)

    V().visit(tree)
    return sites


def _scan_leibniz() -> set:
    found: set = set()
    for p in sorted((_ROOT / "leibniz").rglob("*.py")):
        found |= _scan_source(ast.parse(p.read_text(), filename=str(p)), p.relative_to(_ROOT).as_posix())
    return found


def test_only_sanctioned_kernel_verified_writers():
    found = _scan_leibniz()
    unexpected, missing = found - _WHITELIST, _WHITELIST - found
    assert found == _WHITELIST, (
        f"kernel_verified write sites changed. UNEXPECTED (new writers — a trust-boundary red flag): "
        f"{sorted(unexpected)}; MISSING (a sanctioned site moved/vanished — update the whitelist deliberately): "
        f"{sorted(missing)}. Only LeanVerifier.discharge may MINT a fresh verdict from a kernel check; "
        f"_row_to_prop only REPLAYS a persisted one. Route any new proof-verdict through discharge.")


def test_guard_detects_a_planted_attribute_writer():
    # A second attribute-assign writer must be caught (and it is NOT whitelisted, so the guard would fail).
    planted = "def sneaky(d):\n    d.kernel_verified = True\n"
    sites = _scan_source(ast.parse(planted), "leibniz/sneaky.py")
    assert ("leibniz/sneaky.py", "sneaky", "attr_assign") in sites
    assert ("leibniz/sneaky.py", "sneaky", "attr_assign") not in _WHITELIST


def test_guard_detects_a_planted_constructor_kwarg():
    planted = "def sneaky2():\n    return Demonstratio(proof_obligation='p', kernel_verified=True)\n"
    sites = _scan_source(ast.parse(planted), "leibniz/sneaky2.py")
    assert ("leibniz/sneaky2.py", "sneaky2", "ctor_kwarg") in sites


def test_the_two_sanctioned_sites_are_present_and_correct():
    # Positive check: the real discharge + replay sites are exactly what the whitelist names.
    found = _scan_leibniz()
    assert ("leibniz/verifiers.py", "LeanVerifier::discharge", "attr_assign") in found
    assert ("leibniz/runtime.py", "_row_to_prop", "ctor_kwarg") in found
