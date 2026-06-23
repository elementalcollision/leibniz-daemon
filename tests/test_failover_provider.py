"""Failover frontier reasoner (ADR 0029): try the primary, fall back through backups.

A single reasoner is a single point of failure — a live measurement stalled during an
Anthropic outage. FailoverProvider returns the first non-empty success across an ordered
chain, so an outage of the primary transparently fails over to OpenRouter backups. It only
changes WHICH model proposes; the Lean kernel still decides. CI-safe (no network).
"""
from __future__ import annotations

import json
import urllib.request

import pytest

from leibniz.providers import ProviderUnavailable
from leibniz.providers.failover_provider import FailoverProvider
from leibniz.types import Role


class _FakeProv:
    def __init__(self, model, *, propose=None, repair=None, raises=False, avail=True):
        self.model = model
        self._p, self._r, self._raises, self._avail = propose, repair, raises, avail
        self.calls: list = []

    def available(self):
        return self._avail

    def propose(self, role, ctx):
        self.calls.append(("propose", role, ctx))
        if self._raises:
            raise RuntimeError("boom")
        return self._p

    def repair_proof(self, ts, fp, err):
        self.calls.append(("repair", ts, fp, err))
        if self._raises:
            raise RuntimeError("boom")
        return self._r


def test_primary_success_skips_backups():
    p1 = _FakeProv("primary", propose="by simp")
    p2 = _FakeProv("backup", propose="by ring")
    fo = FailoverProvider([p1, p2])
    assert fo.propose(Role.PROOF_DRAFT, "t") == "by simp"
    assert fo.last_used == "primary"
    assert p2.calls == []  # backup never consulted when primary succeeds


def test_fails_over_on_exception():
    p1 = _FakeProv("primary", raises=True)
    p2 = _FakeProv("backup", propose="by ring")
    fo = FailoverProvider([p1, p2])
    assert fo.propose(Role.PROOF_DRAFT, "t") == "by ring"
    assert fo.last_used == "backup"
    assert p1.calls and p2.calls  # primary was attempted, then the backup


def test_fails_over_on_empty_output():
    p1 = _FakeProv("primary", propose="   ")  # whitespace == no usable proof
    p2 = _FakeProv("backup", propose="by ring")
    fo = FailoverProvider([p1, p2])
    assert fo.propose(Role.PROOF_DRAFT, "t") == "by ring"
    assert fo.last_used == "backup"


def test_all_fail_raises_provider_unavailable():
    fo = FailoverProvider([_FakeProv("a", raises=True), _FakeProv("b", raises=True)])
    with pytest.raises(ProviderUnavailable):
        fo.propose(Role.PROOF_DRAFT, "t")


def test_unavailable_provider_is_skipped_not_called():
    p1 = _FakeProv("primary", propose="by simp", avail=False)
    p2 = _FakeProv("backup", propose="by ring")
    fo = FailoverProvider([p1, p2])
    assert fo.propose(Role.PROOF_DRAFT, "t") == "by ring"
    assert p1.calls == []  # availability checked before calling


def test_repair_proof_also_fails_over():
    p1 = _FakeProv("primary", raises=True)
    p2 = _FakeProv("backup", repair="by exact rfl")
    fo = FailoverProvider([p1, p2])
    assert fo.repair_proof("theorem t : P", "by sorry", "err") == "by exact rfl"
    assert fo.last_used == "backup"


def test_available_reflects_any_backend():
    assert FailoverProvider([_FakeProv("a", avail=False), _FakeProv("b", avail=True)]).available()
    assert not FailoverProvider([_FakeProv("a", avail=False), _FakeProv("b", avail=False)]).available()


# --- OpenRouterProvider.repair_proof (the backup's repair path) --------------

class _Resp:
    def __init__(self, content):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": self._content}}]}).encode()


def test_openrouter_repair_proof_uses_proof_system_and_returns_bare_script(monkeypatch):
    from leibniz.providers.openrouter_provider import _PROOF_SYSTEM, OpenRouterProvider

    captured: dict = {}

    def fake_urlopen(req, *a, **k):
        captured["body"] = json.loads(req.data.decode())
        return _Resp("by exact rfl")

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = OpenRouterProvider(model="z-ai/glm-5.2").repair_proof(
        "theorem t : n + 0 = n", "by sorry", "error: unsolved goals")
    assert out == "by exact rfl"
    msgs = captured["body"]["messages"]
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == _PROOF_SYSTEM  # bare-script, not JSON
    assert "theorem t : n + 0 = n" in msgs[1]["content"]
    assert "error: unsolved goals" in msgs[1]["content"]
