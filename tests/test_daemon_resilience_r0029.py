"""ADR 0029 resilience: a transient provider/infra failure on ONE seed must not crash a run.

A sustained Anthropic 529 in the CONJECTURE role crashed an organic run mid-cycle (the
exception propagated out of `_run_seeds` and killed `main`). The autoformalizer now fails over
to backups first; if every reasoner is still unavailable for a seed, `_run_seeds` records the
seed as `errored` and continues — losing only that seed, never the whole multi-cycle run.

These exercise the resilience boundary directly with stub stages; no network, no Lean.
"""
from __future__ import annotations

from types import SimpleNamespace

from leibniz.daemon import CycleReport, Leibniz


class _Boom:
    """A conjecture stage whose .run always raises (mimics a sustained provider outage)."""
    def run(self, _seed):
        raise RuntimeError("anthropic overloaded (529)")


class _StageReturning:
    def __init__(self, value):
        self._value = value
        self.calls = 0

    def run(self, *_a):
        self.calls += 1
        return self._value


def _bare_daemon() -> Leibniz:
    """A Leibniz instance with only the attributes _run_seeds touches (bypasses build_daemon)."""
    d = Leibniz.__new__(Leibniz)
    d.notebook = None
    d.frontier = None
    return d


def test_errored_seed_does_not_crash_the_run():
    d = _bare_daemon()
    d.conjecture = _Boom()
    report = CycleReport()
    d._run_seeds(["s1", "s2", "s3"], report)          # must NOT raise
    assert report.by_reason.get("errored") == 3        # each seed recorded as errored
    assert report.conjectured == 0                      # raised before the counter increment


def test_loop_continues_past_an_errored_seed():
    # seed 1 errors; seed 2 must still be processed (conjecture -> formalize rejects -> settle).
    class _ConjectureOnceBoom:
        def __init__(self):
            self.n = 0

        def run(self, _seed):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("transient 529")
            return SimpleNamespace()                     # an attribute-settable 'prop' for seed 2
            # (a real conjecture returns a Propositio; _run_seeds tags .seed_origin on it, ADR 0034)

    d = _bare_daemon()
    d.conjecture = _ConjectureOnceBoom()
    d.formalize = _StageReturning(None)                  # seed 2 formalizes to None -> _settle
    settled: list = []
    d._settle = lambda prop, rep: settled.append(prop)   # stub _settle (avoids KFM/runtime wiring)

    report = CycleReport()
    d._run_seeds(["s1", "s2"], report)
    assert report.by_reason.get("errored") == 1          # only seed 1 errored
    assert report.conjectured == 1                        # seed 2 advanced past conjecture
    assert d.formalize.calls == 1 and len(settled) == 1   # seed 2 reached formalize + settle


def test_ctrl_c_is_not_swallowed():
    # KeyboardInterrupt is not an Exception subclass, so an operator Ctrl-C still stops the run.
    class _Interrupt:
        def run(self, _seed):
            raise KeyboardInterrupt

    d = _bare_daemon()
    d.conjecture = _Interrupt()
    try:
        d._run_seeds(["s1"], CycleReport())
    except KeyboardInterrupt:
        return  # expected — propagated, not swallowed
    raise AssertionError("KeyboardInterrupt should propagate, not be caught as an errored seed")
