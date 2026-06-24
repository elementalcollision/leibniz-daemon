"""ADR 0033 Slice 3 — per-instance kernel + corpus pinning.

PROD runs the audited, code-pinned Lean image and the checked-in corpus. An
experimental override (``LEIBNIZ_LEAN_IMAGE`` / ``LEIBNIZ_LEAN_REPL_IMAGE`` /
``LEIBNIZ_CORPUS_PATH``) is honoured only for ``uat``/``dev`` and **ignored for
``prod``** (logged), so a misconfigured deploy can never silently swap PROD's
kernel or corpus. To move PROD's pin you bump the code default — a reviewed,
auditable change — not a mutable env var.

The resolved image tags + a content hash of the corpus are recorded per instance
(``write_provenance``), so a published PROD law is traceable to the exact kernel
image and corpus version that produced it (ADR 0033 §2.4 "pinned kernel + corpus
per instance").

Trust note: this only selects WHICH audited artifacts to use and records them. It
never touches the trust floor — ``LeanVerifier.discharge`` is still the sole
``kernel_verified`` writer and the Lean kernel still decides every proof. The added
property is fail-safe pinning: PROD's kernel image cannot be changed by environment
alone, which *strengthens* the boundary.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from leibniz import corpus as _corpus
from leibniz.backends.lean_cli import DEFAULT_IMAGE
from leibniz.backends.lean_repl import REPL_IMAGE

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_PROVENANCE_DIR = _REPO / ".leibniz"


def _normalize_instance(instance: Optional[str]) -> str:
    """Same resolution as PersistentRuntime (Slice 1): explicit arg, else env, else 'dev'."""
    return (instance or os.environ.get("LEIBNIZ_INSTANCE") or "dev").strip().lower()


def _corpus_version(path: Path) -> str:
    """A content hash of the corpus file — the corpus *version* recorded per instance. A
    missing/unreadable corpus yields 'unknown' rather than aborting config resolution."""
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return "unknown"


@dataclass(frozen=True)
class InstanceConfig:
    """The audited artifacts pinned for one instance, plus the corpus content version."""

    instance: str
    lean_image: str
    lean_repl_image: str
    corpus_path: str
    corpus_version: str

    def provenance(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (f"instance={self.instance} lean={self.lean_image} "
                f"repl={self.lean_repl_image} "
                f"corpus={Path(self.corpus_path).name}@{self.corpus_version}")


def resolve_instance_config(instance: Optional[str] = None) -> InstanceConfig:
    """Resolve the pinned Lean image / corpus for ``instance`` (prod | uat | dev).

    PROD uses the code-pinned audited defaults and *refuses* an experimental env override
    (logged, fail-safe). UAT/dev honour overrides so they can soak experimental images/corpora.
    The corpus version is the content hash of the resolved corpus file.
    """
    inst = _normalize_instance(instance)
    is_prod = inst == "prod"

    def pick(env_name: str, audited_default: str, what: str) -> str:
        override = os.environ.get(env_name)
        if override and override.strip():
            if is_prod:
                # PROD pins the audited artifact; an env override is refused and logged so a
                # misconfigured deploy is visible rather than silently honoured (ADR 0033 §2.4).
                print(f"[instance_config] PROD ignores {env_name}={override!r}; using audited "
                      f"{what} {audited_default!r} (ADR 0033). Bump the code pin to change PROD.")
                return audited_default
            return override.strip()
        return audited_default

    lean_image = pick("LEIBNIZ_LEAN_IMAGE", DEFAULT_IMAGE, "Lean image")
    lean_repl_image = pick("LEIBNIZ_LEAN_REPL_IMAGE", REPL_IMAGE, "Lean REPL image")
    corpus_path = pick("LEIBNIZ_CORPUS_PATH", str(_corpus._DEFAULT_PATH), "corpus")
    return InstanceConfig(
        instance=inst,
        lean_image=lean_image,
        lean_repl_image=lean_repl_image,
        corpus_path=corpus_path,
        corpus_version=_corpus_version(Path(corpus_path)),
    )


def write_provenance(
    config: InstanceConfig,
    dir: Optional[Path] = None,
    clock: Callable[[], float] = time.time,
) -> Path:
    """Append one provenance record (a JSON line) for this instance.

    Durable + auditable: each run records the kernel image + corpus version it used, so a
    published PROD law is traceable to the artifacts that produced it. Append-only keeps the
    full history (e.g. UAT soaking v4.31 then v4.32). Called by the run entrypoint — NOT by
    ``build_daemon``, which stays construct-only (no filesystem writes)."""
    d = Path(dir or _DEFAULT_PROVENANCE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    rec = config.provenance()
    rec["ts"] = clock()
    out = d / f"provenance-{config.instance}.jsonl"
    with out.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return out
