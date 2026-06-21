"""Minimal .env loader (stdlib only).

Leibniz reads provider credentials from the environment. For local/dev runs you can
drop them in a gitignored ``.env`` at the repo root; call ``load_env()`` at an
entrypoint to populate ``os.environ`` for any keys not already set. Secrets are
never logged here and ``.env`` is gitignored.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_DEFAULT = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Optional[Path] = None, *, override: bool = False) -> int:
    """Load KEY=VALUE lines from ``.env`` into os.environ. Returns the number of
    variables set. Existing env vars win unless ``override=True``. No-op if absent."""
    p = Path(path or _DEFAULT)
    if not p.exists():
        return 0
    n = 0
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value
            n += 1
    return n
