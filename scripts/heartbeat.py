"""ADR 0068 Phase α — the heartbeat: one autonomous, capped, journaled beat of the daemon.

One invocation = one beat: PREFLIGHT (Docker/OrbStack up — restarting it if down, the failure observed
twice in live operation — Lean image present, Z3 importable) → N capped cycles through the FULL
steering loop (ADR 0069 Phase β: ``run_cycles`` — domain rotation, KFM recombination, near-miss
weakening, frontier-band retune, notebook persistence — not the bare fresh-survey
``circadian_cycle``) → a JSONL RUN JOURNAL entry (funnel, dispositions, ADR 0067 CROSS_STATS delta,
steering state, duration, anomalies) → a regenerated REVIEW QUEUE of promulgated-but-held laws →
an optional arXiv AMPLIFICATION-TARGET sweep (``LEIBNIZ_ARXIV_FEED=1``; failure is a journal note,
never an abort) → ANOMALY alarms (cross-solver disagreement, errored cycles, leaked containers,
preflight degradation) to a log + a best-effort macOS notification.

Autonomy posture (the whole point of Phase α): the daemon may explore and promulgate on its own —
**nothing publishes itself**. Promulgations land in the Codex and the review queue; publication stays
the operator's ADR 0033 act. Spend is capped (``LEIBNIZ_DAILY_USD_CAP``, default 5 here), activation
follows the operator's standing ``.env`` (plus ``LEIBNIZ_LEAN_DECIDED`` defaulted ON for beats), and
every anomaly is loud. The launchd bootstrap (``deploy/heartbeat/``) runs each beat from a worktree
synced to **origin/main** — the daemon always executes the latest operator-merged code, never a
working tree.

State lives under ``LEIBNIZ_HEARTBEAT_HOME`` (the canonical repo's ``.leibniz/``):
``journal.jsonl`` · ``review_queue.md`` · ``alarms.log``.

Usage:  PYTHONPATH=. python scripts/heartbeat.py            # one beat (LEIBNIZ_HEARTBEAT_CYCLES, default 2)
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def _home() -> Path:
    return Path(os.environ.get("LEIBNIZ_HEARTBEAT_HOME") or (_REPO / ".leibniz"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- preflight -------------------------------------------------------------------------------------

def docker_up(start_wait_s: int = 120) -> bool:
    """True iff the Docker daemon answers — starting OrbStack and waiting if it is down."""
    def _ok() -> bool:
        try:
            return subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    if _ok():
        return True
    try:
        subprocess.run(["open", "-a", "OrbStack"], capture_output=True, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    deadline = time.monotonic() + start_wait_s
    while time.monotonic() < deadline:
        if _ok():
            return True
        time.sleep(5)
    return False


def preflight() -> tuple[list[str], list[str]]:
    """(hard_problems, notes). Any hard problem aborts the beat (alarmed, journaled, exit 2)."""
    hard: list[str] = []
    notes: list[str] = []
    if not docker_up():
        hard.append("docker daemon unreachable (OrbStack restart failed)")
    else:
        from leibniz.backends import lean_repl
        if not lean_repl.available():
            hard.append(f"Lean REPL image absent: {lean_repl.REPL_IMAGE}")
    try:
        from leibniz.backends.smt_z3 import available as z3_available
        if not z3_available():
            hard.append("z3-solver (verify extra) not importable")
    except Exception as e:  # pragma: no cover
        hard.append(f"smt_z3 import failed: {e}")
    try:
        from leibniz.backends.smt_cvc5 import available as cvc5_available
        if not cvc5_available():
            notes.append("cvc5 extra absent — ADR 0067 cross-check will not attest this beat")
    except Exception:  # pragma: no cover
        notes.append("smt_cvc5 import failed — cross-check unavailable")
    if not (_REPO / ".env").exists():
        hard.append(".env missing (credentials/config)")
    return hard, notes


# --- the beat --------------------------------------------------------------------------------------

def lean_containers() -> int:
    try:
        out = subprocess.run(["docker", "ps", "--format", "{{.Image}}"],
                             capture_output=True, text=True, timeout=20).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1
    return sum(1 for line in out.splitlines() if any(k in line.lower() for k in ("lean", "leibniz", "repl", "mathlib")))


def wait_containers_drained(timeout_s: int = 240, poll_s: int = 10) -> int:
    """Final image-filtered container count, giving ``--rm`` REPL containers time to self-drain.
    The grace must EXCEED lean_repl's per-call timeout (180s): a container abandoned mid-proof
    legitimately lives until its own teardown horizon (two validation beats 2026-07-21 false-
    alarmed at 0s and 60s grace; the container was gone shortly after each time)."""
    n = lean_containers()
    deadline = time.monotonic() + timeout_s
    while n > 0 and time.monotonic() < deadline:
        time.sleep(poll_s)
        n = lean_containers()
    return n


def beat(cycles: int, frontier_limit: int = 2, analogy_limit: int = 1) -> dict:
    """Turn ``cycles`` capped cycles through the FULL steering loop and return the journal
    entry (pure data). ADR 0069: this calls ``run_cycles`` — which recombines from the KFM
    archive, weakens recent near-misses, rotates domains, retunes + persists the frontier
    band, and persists the notebook — where Phase α's bare ``circadian_cycle`` loop took a
    fresh survey every time and threw the steering state away."""
    os.environ.setdefault("LEIBNIZ_LEAN_DECIDED", "1")          # beats run the activated pipeline
    os.environ.setdefault("LEIBNIZ_DAILY_USD_CAP", "5")         # never uncapped on a schedule
    from leibniz.assembly import build_daemon
    from leibniz.backends.smt_z3 import CROSS_STATS
    from leibniz.env import load_env

    load_env(_REPO / ".env")
    cross_before = dict(CROSS_STATS)
    entry: dict = {"ts": _now(), "cycles_requested": cycles, "cycles": [], "anomalies": [],
                   "usd_cap": os.environ.get("LEIBNIZ_DAILY_USD_CAP")}
    t0 = time.monotonic()
    daemon = build_daemon(frontier_limit=frontier_limit, analogy_limit=analogy_limit)
    try:
        # run_cycles enforces the cost cap before each cycle and may return fewer reports
        # than requested; the journal records cycles_requested vs what actually turned.
        for r in daemon.run_cycles(cycles):
            entry["cycles"].append({"seeds": r.seeds, "conjectured": r.conjectured,
                                    "reached_proof": r.reached_proof, "promulgated": r.promulgated,
                                    "by_reason": dict(r.by_reason)})
    except Exception as e:                                       # a broken run is an anomaly, not a crash
        entry["cycles"].append({"error": f"{type(e).__name__}: {e}"})
        entry["anomalies"].append(f"beat errored mid-run: {type(e).__name__}: {str(e)[:200]}")
    try:
        # Tear down the daemon's REPL backends NOW: their containers hold this process's stdin
        # pipes and cannot exit while we wait — the 1→2→3 "leak" of the 2026-07-23 soak was the
        # per-procedure backends (six since ADR 0070) draining only at process exit, AFTER the
        # count. With this, a nonzero post-beat count is a genuine anomaly again.
        from leibniz.backends import lean_repl
        entry["backends_closed"] = lean_repl.close_all()
    except Exception:  # pragma: no cover
        pass
    entry["duration_s"] = round(time.monotonic() - t0, 1)
    entry["cross_stats_delta"] = {k: CROSS_STATS[k] - cross_before[k] for k in CROSS_STATS}
    # ADR 0069 observability: the morning journal shows WHERE the frontier moved to.
    nb, fr = getattr(daemon, "notebook", None), getattr(daemon, "frontier", None)
    entry["steering"] = {
        "genre_kill": list(nb.genre_kill) if nb else [],
        "dry_kill": list(nb.dry_kill) if nb else [],
        "too_hard": len(nb.too_hard) if nb else 0,
        "band_target": fr.target if fr else None,
    }
    return entry


def detect_anomalies(entry: dict, containers_after: int) -> list[str]:
    """Kill-only anomaly scan of a journal entry — anything here is loud, nothing is fatal upstream."""
    out = list(entry.get("anomalies", []))
    if entry.get("cross_stats_delta", {}).get("disagree", 0) > 0:
        out.append(f"ADR 0067 CROSS-SOLVER DISAGREEMENT this beat: {entry['cross_stats_delta']}")
    errored = sum(c.get("by_reason", {}).get("errored", 0) for c in entry.get("cycles", []) if isinstance(c, dict))
    if errored:
        out.append(f"{errored} candidate(s) errored inside cycles")
    if containers_after > 0:
        out.append(f"{containers_after} Lean container(s) still running after the beat")
    if all(c.get("seeds", 0) == 0 for c in entry.get("cycles", []) if "seeds" in c) and entry.get("cycles"):
        out.append("0 seeds in every cycle — frontier misconfiguration? (see the 2026-07-09 finding)")
    return out


# --- journal + review queue + alarms ---------------------------------------------------------------

def write_journal(entry: dict, home: Path | None = None) -> Path:
    home = home or _home()
    home.mkdir(parents=True, exist_ok=True)
    p = home / "journal.jsonl"
    with p.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return p


def write_review_queue(db_path: str | Path, home: Path | None = None) -> Path:
    """Regenerate the operator review queue: every promulgated (kernel-verified) law in the runtime
    DB, newest first. Promulgated ≠ published — everything here awaits the ADR 0033 operator act."""
    home = home or _home()
    home.mkdir(parents=True, exist_ok=True)
    rows: list = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT pid, born, theorem_src FROM memory "
            "WHERE lower(finish_reason) = 'promulgated' AND kernel_verified = 1 "
            "ORDER BY rowid DESC").fetchall()
        con.close()
    except Exception:
        rows = []
    lines = ["# Review queue — promulgated, held for the operator (ADR 0033)", "",
             f"_Regenerated {_now()} by the heartbeat. Publication is YOUR act; nothing here_",
             "_publishes itself. Newest first._", ""]
    if not rows:
        lines.append("(no held promulgations)")
    for pid, born, thm in rows:
        try:
            when = datetime.fromtimestamp(float(born), tz=timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            when = "?"
        head = " ".join(str(thm or "").split())[:100]
        lines.append(f"- `{pid[:8]}` · {when} · `{head}`")
    p = home / "review_queue.md"
    p.write_text("\n".join(lines) + "\n")
    return p


def alarm(messages: list[str], home: Path | None = None) -> None:
    if not messages:
        return
    home = home or _home()
    home.mkdir(parents=True, exist_ok=True)
    with (home / "alarms.log").open("a") as f:
        for m in messages:
            f.write(f"{_now()}  {m}\n")
    try:  # best-effort desktop ping; never load-bearing
        subprocess.run(["osascript", "-e",
                        f'display notification "{messages[0][:120]}" with title "Leibniz heartbeat"'],
                       capture_output=True, timeout=10)
    except Exception:  # pragma: no cover
        pass


# --- entrypoint ------------------------------------------------------------------------------------

def main() -> int:
    cycles = int(os.environ.get("LEIBNIZ_HEARTBEAT_CYCLES", "2"))
    home = _home()
    hard, notes = preflight()
    if hard:
        entry = {"ts": _now(), "aborted": True, "preflight": hard, "notes": notes}
        write_journal(entry, home)
        alarm([f"beat ABORTED at preflight: {'; '.join(hard)}"], home)
        print(f"[heartbeat] ABORT — {hard}")
        return 2
    entry = beat(cycles)
    entry["preflight_notes"] = notes
    containers = wait_containers_drained()
    anomalies = detect_anomalies(entry, containers)
    entry["anomalies"] = anomalies
    if os.environ.get("LEIBNIZ_ARXIV_FEED") == "1":              # ADR 0069: amplification-target sweep
        try:
            from leibniz.arxiv_feed import run_feed
            entry["arxiv_feed"] = run_feed(home)
        except Exception as e:                                   # arXiv down at 02:30 is a note, not a page
            entry["arxiv_feed"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    write_journal(entry, home)
    write_review_queue(os.environ.get("LEIBNIZ_RUNTIME_DB") or (_REPO / ".leibniz" / "memory.db"), home)
    if anomalies:
        alarm(anomalies, home)
    promulgated = sum(c.get("promulgated", 0) for c in entry["cycles"] if isinstance(c, dict))
    feed = entry.get("arxiv_feed")
    feed_note = (f", feed={feed.get('queued', '?')} queued of {feed.get('fetched', '?')}"
                 if isinstance(feed, dict) and "error" not in feed
                 else ", feed=ERROR" if feed else "")
    print(f"[heartbeat] beat complete: {len(entry['cycles'])} cycle(s), {promulgated} promulgated (held), "
          f"cross={entry['cross_stats_delta']}, steering={entry.get('steering')}{feed_note}, "
          f"anomalies={len(anomalies)}, {entry['duration_s']}s")
    return 3 if anomalies else 0


if __name__ == "__main__":
    sys.exit(main())
