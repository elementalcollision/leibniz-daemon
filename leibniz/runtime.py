"""Persistent runtime (ADR 0016) — a real RuntimeAdapter, not the in-memory stub.

`SimpleRuntime` kept memory in a list that vanished on exit and pinned the
circadian phase to "WAKE". `PersistentRuntime` makes the body's substrate real and
self-contained (no external dependency):

- **Memory** is SQLite-backed, so `remember`/`recall_recent` survive restarts — a
  sustained autonomous run accumulates its ledger of candidates across sessions.
- **Circadian phase** is computed from the clock (WAKE / NREM / REM), injectable
  for tests, instead of a constant.
- **Witness** (cross-model agreement) stays a documented seam returning [] until a
  provider ensemble is wired here; the gaming-witness uses Z3 (mechanical), not
  this path.

The DB connection is opened lazily on first `remember`/`recall`, so constructing a
`PersistentRuntime` (e.g. in `build_daemon`) touches no filesystem until the daemon
actually runs.

This is the body's clean-room implementation of `adapters.RuntimeAdapter`. Wiring
the *external* Chimera (its own scheduler/SQLite/witness) remains a drop-in behind
the same Protocol; nothing here assumes Chimera's internals. It writes no trust
edge and sets no kernel_verified — it only records and recalls.

Trust note: the runtime records a candidate's *disposition* via its `FinishReason`
(which includes PROMULGATED), and deliberately never sets the policy-gated
`Propositio.promulgated` flag — a recalled memory is a historical record, not a
live promotion. The promotion flag is written only on the two TrustPolicy-routed
paths (enforced by tests/test_boundary_guards.py).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Union

from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, FinishReason

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _REPO / ".leibniz" / "memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    pid TEXT PRIMARY KEY,
    born REAL, ts REAL,
    statement TEXT, claim_type TEXT, falsifiable_claim TEXT, domain TEXT,
    theorem_src TEXT, normalized_hash TEXT,
    kernel_verified INTEGER, qed TEXT, proof_src TEXT,
    finish_reason TEXT, parents TEXT, instance TEXT, claim_property TEXT
)
"""

# Columns the runtime reads/writes by NAME (so the INSERT is robust to a migrated
# DB where ALTER TABLE appended columns at the end, ADR 0025 / ADR 0033 / ADR 0034).
_COLUMNS = (
    "pid", "born", "ts", "statement", "claim_type", "falsifiable_claim", "domain",
    "theorem_src", "normalized_hash", "kernel_verified", "qed", "proof_src",
    "finish_reason", "parents", "instance", "claim_property",
)


def phase_for_hour(hour: int) -> str:
    """Map an hour-of-day to a circadian phase (the daemon's 'slow cycle')."""
    if 6 <= hour < 22:
        return "WAKE"
    if 2 <= hour < 6:
        return "REM"
    return "NREM"  # 22:00–02:00


class PersistentRuntime:
    """A real RuntimeAdapter: SQLite memory + clock-based circadian phase."""

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.db_path = str(db_path or os.environ.get("LEIBNIZ_RUNTIME_DB") or _DEFAULT_DB)
        # ADR 0033: the instance this runtime belongs to (prod | uat | dev). Stamped on every
        # row and enforced by the write-barrier so a UAT run can never write the PROD ledger.
        self.instance = (os.environ.get("LEIBNIZ_INSTANCE") or "dev").strip().lower()
        self._clock = clock
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    # --- lazy connection (build_daemon stays side-effect-free) ----------------
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute(_SCHEMA)
            # ADR 0025: idempotent migration — add proof_src to a pre-existing DB so a
            # promulgated law's kernel-checked proof is persisted (not just its verdict).
            have = {row[1] for row in self._conn.execute("PRAGMA table_info(memory)")}
            if "proof_src" not in have:
                self._conn.execute("ALTER TABLE memory ADD COLUMN proof_src TEXT")
            if "instance" not in have:  # ADR 0033: per-instance provenance on a pre-existing DB
                self._conn.execute("ALTER TABLE memory ADD COLUMN instance TEXT")
            if "claim_property" not in have:  # ADR 0034 Stage 0: persist the canonical DSL
                # predicate so promulgations are natively measurable by novelty_metrics
                # (pre-Stage-0 rows stay NULL — reported honestly as no-property-stored).
                self._conn.execute("ALTER TABLE memory ADD COLUMN claim_property TEXT")
            self._conn.commit()
            # ADR 0033 write-barrier: refuse a ledger already claimed by a DIFFERENT instance, so
            # a misconfigured UAT pointed at the PROD DB FAILS CLOSED instead of interleaving.
            # Legacy untagged (NULL) rows predate tagging and are exempt; the first tagged write
            # claims the DB for that instance.
            others = sorted(
                r[0] for r in self._conn.execute(
                    "SELECT DISTINCT instance FROM memory "
                    "WHERE instance IS NOT NULL AND instance != ?", (self.instance,)
                )
            )
            if others:
                self._conn.close()
                self._conn = None
                raise RuntimeError(
                    f"runtime DB {self.db_path!r} is owned by instance(s) {others}, not "
                    f"{self.instance!r} (ADR 0033 write-barrier). Point LEIBNIZ_RUNTIME_DB at a "
                    f"separate ledger for this instance."
                )
        return self._conn

    # --- RuntimeAdapter Protocol ----------------------------------------------
    def now_phase(self) -> str:
        return phase_for_hour(time.localtime(self._clock()).tm_hour)

    def remember(self, prop: Propositio) -> None:
        en, ex, de = prop.enuntiatio, prop.expressio, prop.demonstratio
        row = (
            prop.pid, prop.born, self._clock(),
            en.statement, en.claim_type.value, en.falsifiable_claim, en.domain,
            ex.theorem_src if ex else None, ex.normalized_hash if ex else None,
            int(de.kernel_verified) if de else 0, de.qed if de else "Q.E.I.",
            de.proof_src if de else None,  # ADR 0025: persist the kernel-checked proof
            prop.finish_reason.value if prop.finish_reason else None,
            json.dumps(list(prop.parents)),
            self.instance,  # ADR 0033: stamp the writing instance (provenance)
            en.claim_property,  # ADR 0034 Stage 0: the canonical DSL predicate (or None)
        )
        cols = ", ".join(_COLUMNS)
        marks = ", ".join("?" for _ in _COLUMNS)
        with self._lock:
            self._db().execute(
                f"INSERT OR REPLACE INTO memory ({cols}) VALUES ({marks})", row
            )
            self._db().commit()

    def recall_recent(self, n: int) -> list[Propositio]:
        with self._lock:
            rows = self._db().execute(
                "SELECT pid, born, statement, claim_type, falsifiable_claim, domain, "
                "theorem_src, normalized_hash, kernel_verified, qed, proof_src, "
                "finish_reason, parents, claim_property "
                "FROM memory ORDER BY ts DESC, rowid DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [_row_to_prop(r) for r in rows]

    def witness(self, prompt: str, n_models: int) -> list[str]:
        # Cross-model agreement is a seam: wiring a provider ensemble here is future
        # work. The gaming-witness (faithfulness) uses Z3, not this path.
        return []

    # --- lifecycle ------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> "PersistentRuntime":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _row_to_prop(r: tuple) -> Propositio:
    (pid, born, statement, claim_type, falsifiable_claim, domain, theorem_src,
     normalized_hash, kernel_verified, qed, proof_src, finish_reason, parents,
     claim_property) = r
    en = Enuntiatio(
        statement=statement, claim_type=ClaimType(claim_type),
        falsifiable_claim=falsifiable_claim or "",
        domain=domain or "analysis_of_algorithms",
        claim_property=claim_property,  # ADR 0034 Stage 0: round-trip the canonical predicate
    )
    ex = Expressio(theorem_src=theorem_src, normalized_hash=normalized_hash or "") if theorem_src else None
    # Reconstruct the certificate only for proven candidates (qed == Q.E.D. iff
    # kernel_verified), now WITH its kernel-checked proof script (ADR 0025) so a
    # promulgated law carries its proof for audit/publication.
    # kernel_verified is set via the Demonstratio constructor (not an attribute
    # assignment) — the single-writer guard binds discharge, and this only replays
    # a stored verdict, never mints one.
    de = Demonstratio(proof_obligation=pid, proof_src=proof_src,
                      kernel_verified=bool(kernel_verified), qed=qed) \
        if kernel_verified else None
    prop = Propositio(
        enuntiatio=en, expressio=ex, demonstratio=de, pid=pid, born=born,
        parents=tuple(json.loads(parents or "[]")),
    )
    # Disposition only — never the policy-gated `promulgated` flag (trust note above).
    prop.finish_reason = FinishReason(finish_reason) if finish_reason else None
    return prop
