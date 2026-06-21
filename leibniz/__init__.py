"""Leibniz · Calculemus — agentic theorem daemon.

Public entrypoints (HANDOFF §5). LLMs propose; only mechanical checkers decide.
These re-exports pull in only stdlib-backed modules; the real Lean/Z3/provider
backends are optional extras and are never imported by importing this package.
"""

from leibniz.daemon import Leibniz
from leibniz.propositio import Propositio
from leibniz.trust import TrustPolicy

__all__ = ["Leibniz", "Propositio", "TrustPolicy"]
