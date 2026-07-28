# ADR 0080 — The frontier controller escapes a bound it is saturated against

- Status: accepted
- Date: 2026-07-28
- Depends on: ADR 0018/0019 (the difficulty band and its persistence)

## Context

Three consecutive nightly beats reported `band_target: 0.15` — the controller's **floor** — while
promulgating steadily. All three of the newest held laws are two-variable residue laws of the same
shape: the daemon was producing, but producing one genre, at its easiest setting.

The persisted state explains it exactly:

```json
{"target": 0.15, "recent": [false,false,false,true,false,false,true,false], "jumps": 1}
```

Success rate **0.25** against `aim` **0.35**. So `err = +0.10`, the homing rule reads *"too hard,
go easier"*, computes `0.15 - 0.30 × 0.10 = 0.12`, and `max(floor, …)` clamps it back to `0.15`.
Every night. The controller is not converged — it is **saturated**: it wants a band below its own
floor, so homing is a permanent no-op.

The existing re-exploration escape cannot help, because it fires only on `rate == 0.0` *exactly* —
a condition that stops being true the moment the daemon proves anything at all. A productive
daemon can therefore pin itself at the floor forever, which is precisely the failure the escape was
written to prevent, one notch away from the case it checks.

## Decision

Generalize the escape from *"nothing is proving at a bound"* to *"the correction still points past
a bound"*:

```python
saturated = (at_floor and err > 0) or (at_ceil and err < 0)
```

A single saturated update is not a pin — a bound can be touched legitimately in passing — so a
counter (`pin_limit`, default 3 updates) must run out first. The `rate == 0.0` escape keeps its
immediate trigger. On escape the controller jumps to the opposite half with the existing
per-jump jitter, clears the window, and resets the counter.

Crucially, a bound touched while the correction points **inward** is *not* saturation: at the
floor while succeeding too often, homing legitimately pulls the target up, and that is the
controller working. Pinned above, not counted.

`_pinned` is persisted; state files written before this ADR simply read back as `0`.

## Consequences

Replayed against the live pinned state: the target escapes on the third update, `0.15 → 0.57`,
instead of holding 0.15 indefinitely.

Proposal-side only — the band is context for the conjecturer's prompt and decides nothing. No gate,
no kernel, no trust surface.

Expect the funnel to look *worse* for a night or two after an escape: a harder band means more
`unproven`, and the controller will home back down. That is the intended cost of not mining one
genre forever, and the journal's `band_target` makes each excursion visible.
