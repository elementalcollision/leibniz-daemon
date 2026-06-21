"""Leonardo SURVEY adapter (D6 / ADR 0007) — a real LeonardoAdapter implementation.

Leonardo is NOT the survey/analogy oracle the original spec inferred. It is a live
da-Vinci-voice autonomous journaling agent (claude-daemon lineage; a Forge journal
of Studio + Codex folios, plus mind-search). Its genuine contribution to Leibniz is
**cross-domain analogy** — the "da Vinci move": its Codex folios are reflective
stepping stones from other domains. Frontier survey of analysis-of-algorithms is
*not* Leonardo's job, so it comes from a curated source here. Both sit behind this
one adapter (the spec's isolation intent), so the seam stays a one-file change.

Coupling is loose: it reads Leonardo's **Forge artifact** (a git checkout; path via
`LEONARDO_FORGE_PATH`) — no dependency on Leonardo's running daemon. A mind-search
HTTP path (`LEONARDO_SEARCH_URL`) is a possible future enhancement, not required.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_FORGE = _REPO.parent / "leonardo-forge"
_DEFAULT_FRONTIER = _REPO / "corpus" / "frontier.json"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML-frontmatter split (stdlib only): scalars between leading
    `---` fences -> dict; the rest -> body."""
    fm: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    key, _, val = line.partition(":")
                    fm[key.strip()] = val.strip().strip('"').strip("'")
            body = text[end + 4:]
    return fm, body


def _forge_path() -> Path:
    return Path(os.environ.get("LEONARDO_FORGE_PATH", str(_DEFAULT_FORGE)))


def _frontier_path() -> Path:
    return Path(os.environ.get("LEIBNIZ_FRONTIER_PATH", str(_DEFAULT_FRONTIER)))


@dataclass
class LeonardoForgeAdapter:
    forge_path: Path = field(default_factory=_forge_path)
    frontier_path: Path = field(default_factory=_frontier_path)
    max_analogies: int = 3
    max_seeds: int = 8

    def survey_frontier(self, domain: str) -> list[str]:
        """Curated open-edge seeds for the domain (Leonardo does not survey these)."""
        try:
            data = json.loads(self.frontier_path.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        seeds = data.get(domain, []) if isinstance(data, dict) else (data or [])
        return [str(s) for s in seeds][: self.max_seeds]

    def cross_domain_analogies(self, seed: str) -> list[str]:
        """Stepping stones drawn from Leonardo's Codex folios (the da Vinci move)."""
        codex = self.forge_path / "Codex"
        if not codex.is_dir():
            return []
        folios = sorted(codex.glob("*.en.md")) or sorted(codex.glob("*.md"))
        if not folios:
            return []
        # Deterministic per-seed rotation (stable across runs; no RNG).
        start = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(folios)
        chosen = [folios[(start + i) % len(folios)] for i in range(min(self.max_analogies, len(folios)))]
        out: list[str] = []
        for f in chosen:
            try:
                fm, body = _parse_frontmatter(f.read_text())
            except OSError:
                continue
            gist = next((ln.strip() for ln in body.splitlines() if ln.strip()), f.stem)
            out.append(f"analogy[{fm.get('domain', 'meta')}]: {gist[:160]}")
        return out
