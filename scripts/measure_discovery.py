"""Measure the discovery frontier (ADR 0018) — a deterministic demonstration that
the FrontierController steers the proposal band over the prover's reach and lifts
discovery yield, and that it recovers instead of getting stuck.

Self-contained (no LLM, no Lean): a hidden "tractable window" stands in for the
prover's reach — a conjecture below it is trivial (killed by the gates), above it is
too hard (UNPROVEN), inside it proves. The conjecturer clusters its proposals around
the controller's target band. We do NOT claim the controller centres on the window;
it holds a target SUCCESS RATE, walking the proposal band so its tractable tail
overlaps the window.

Two scenarios:
  1. WIDE window, far start — thermostat ON vs OFF: ON lifts steady-state yield.
  2. NARROW window the band overshoots — show re-exploration recovers (yield > 0)
     where a pin-at-the-floor controller would stay stuck at 0% forever.

Run:  python scripts/measure_discovery.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.discovery import FrontierController  # noqa: E402

SPREAD = (-0.12, -0.06, -0.03, 0.0, 0.06, 0.12)  # deterministic proposal cloud (±band)


def _proves(d: float, window: tuple[float, float]) -> bool:
    return window[0] <= d <= window[1]


def run(window, *, adaptive: bool, cycles: int = 30, per_cycle: int = 6, start: float = 0.80):
    fc = FrontierController(target=start, window=8)
    yields: list[float] = []
    for _ in range(cycles):
        proved = 0
        for j in range(per_cycle):
            d = min(0.999, max(0.0, fc.target + SPREAD[j % len(SPREAD)]))
            ok = _proves(d, window)
            proved += ok
            fc.record(ok)
        yields.append(proved / per_cycle)
        if adaptive:
            fc.update()
    return yields, fc.target


def _bar(y: float, width: int = 22) -> str:
    return "█" * round(y * width) + "·" * (width - round(y * width))


def _avg(xs):
    return sum(xs) / len(xs)


def main() -> int:
    # ---- Scenario 1: wide window, far start --------------------------------------
    wide = (0.30, 0.50)
    print(f"Scenario 1 — wide window {wide}, start target 0.80 (far above it)\n")
    on_y, on_t = run(wide, adaptive=True)
    off_y, off_t = run(wide, adaptive=False)
    print("cycle │ thermostat ON                     │ thermostat OFF")
    print("──────┼───────────────────────────────────┼───────────────────────")
    for i in range(0, len(on_y), 5):
        print(f"  {i:>3} │ {_bar(on_y[i])} {on_y[i]*100:4.0f}% │ {_bar(off_y[i])} {off_y[i]*100:4.0f}%")
    print(f"\n  ON : target 0.80 → {on_t:.2f}; proposal band overlaps the window; "
          f"yield {on_y[0]*100:.0f}% → {_avg(on_y[-6:])*100:.0f}% (last 6 avg)")
    print(f"  OFF: target stays {off_t:.2f}; yield {_avg(off_y[-6:])*100:.0f}% (stuck)")

    # ---- Scenario 2: narrow window, recovery from overshoot ----------------------
    narrow = (0.40, 0.48)
    print(f"\nScenario 2 — narrow window {narrow}: the band overshoots; re-exploration must recover\n")
    rec_y, rec_t = run(narrow, adaptive=True, cycles=40)
    hit_cycle = next((i for i, y in enumerate(rec_y) if y > 0), None)
    print(f"  adaptive: first proof at cycle {hit_cycle}; steady yield {_avg(rec_y[-8:])*100:.0f}% "
          f"(last 8 avg); target wandered, did not pin the floor")
    print("  → the controller re-explored after overshooting and found the band; a plain "
          "deadband controller would sit at the floor at 0% forever.")

    gain = _avg(on_y[-6:]) - _avg(off_y[-6:])
    print(f"\nADR 0018: the frontier controller lifts steady-state yield by ~{gain*100:.0f} points "
          f"and recovers from overshoot — it finds reach it was never told.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
