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
    def __init__(self, model, *, propose=None, repair=None, raises=False, avail=True, af=None):
        self.model = model
        self._p, self._r, self._raises, self._avail = propose, repair, raises, avail
        self._af = af  # value returned by the autoformalize-stage methods
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

    def repair_formalization(self, statement, prior_src, error):
        self.calls.append(("repair_formalization", statement))
        if self._raises:
            raise RuntimeError("boom")
        return self._af

    def repair_contract(self, statement, cd, cp, ed, problems):
        self.calls.append(("repair_contract", statement))
        if self._raises:
            raise RuntimeError("boom")
        return self._af

    def decompose(self, theorem_src):
        self.calls.append(("decompose", theorem_src))
        if self._raises:
            raise RuntimeError("boom")
        return self._af


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


def test_autoformalize_stage_methods_fail_over():
    # ADR 0029: the failover wrapper must expose the FULL autoformalizer surface, else wrapping
    # the autoformalizer would silently DISABLE the contract/import-repair + decomposition loops
    # (the pipeline looks them up via getattr). Each must fall over to a backup.
    p1 = _FakeProv("primary", raises=True)
    p2 = _FakeProv("backup", af='{"ok": true}')
    fo = FailoverProvider([p1, p2])
    assert fo.repair_formalization("claim", "src", "err") == '{"ok": true}'
    assert fo.repair_contract("claim", "n>=0", "p", "n>=0", ["bad"]) == '{"ok": true}'
    assert fo.decompose("theorem t : P") == '{"ok": true}'
    # the primary was attempted for each before falling over
    assert {c[0] for c in p1.calls} == {"repair_formalization", "repair_contract", "decompose"}


def test_failover_exposes_autoformalizer_surface_for_getattr():
    # the pipeline does getattr(provider, "repair_contract", None); a wrapped autoformalizer
    # must still expose these or those loops silently vanish.
    fo = FailoverProvider([_FakeProv("p", af="x")])
    for name in ("propose", "repair_proof", "repair_formalization", "repair_contract", "decompose"):
        assert callable(getattr(fo, name, None)), name


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


# --- OpenRouter as a CONJECTURE/FORMALIZE backup (ADR 0029 proposal-side failover) ----------

def _capture_openrouter(monkeypatch, content="{}"):
    """Point OpenRouterProvider at a fake gateway; return a dict that captures the last body."""
    captured: dict = {}

    def fake_urlopen(req, *a, **k):
        captured["body"] = json.loads(req.data.decode())
        return _Resp(content)

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def test_openrouter_conjecture_applies_the_shared_template(monkeypatch):
    # The crux of proposal-side failover: a backup must build the FULL conjecture prompt, not
    # send the bare seed. It must match the Anthropic primary's prompt byte-for-byte (no drift).
    from leibniz.providers import AUTOFORMALIZE_PROMPTS, AUTOFORMALIZE_SYSTEM
    from leibniz.providers.openrouter_provider import OpenRouterProvider

    cap = _capture_openrouter(monkeypatch, '{"statement": "x"}')
    OpenRouterProvider(model="z-ai/glm-5.2").propose(Role.CONJECTURE, "ctx-123")
    msgs = cap["body"]["messages"]
    assert msgs[0]["content"] == AUTOFORMALIZE_SYSTEM           # JSON system, not the proof/generic one
    assert msgs[1]["content"] == AUTOFORMALIZE_PROMPTS[Role.CONJECTURE].format(context="ctx-123")
    assert "FAITHFULNESS DSL" in msgs[1]["content"] and "ctx-123" in msgs[1]["content"]


def test_openrouter_formalize_applies_the_shared_template(monkeypatch):
    from leibniz.providers import AUTOFORMALIZE_PROMPTS
    from leibniz.providers.openrouter_provider import OpenRouterProvider

    cap = _capture_openrouter(monkeypatch, '{"theorem_src": "theorem t : True"}')
    OpenRouterProvider(model="z-ai/glm-5.2").propose(Role.FORMALIZE, "the claim")
    assert cap["body"]["messages"][1]["content"] == \
        AUTOFORMALIZE_PROMPTS[Role.FORMALIZE].format(context="the claim")


def test_openrouter_proof_draft_sends_raw_context(monkeypatch):
    # PROOF_DRAFT context is already the full proof prompt (built by the caller) — must NOT be
    # re-wrapped in the conjecture template.
    from leibniz.providers.openrouter_provider import _PROOF_SYSTEM, OpenRouterProvider

    cap = _capture_openrouter(monkeypatch, "by simp")
    OpenRouterProvider(model="z-ai/glm-5.2").propose(Role.PROOF_DRAFT, "theorem t : True := by ?")
    msgs = cap["body"]["messages"]
    assert msgs[0]["content"] == _PROOF_SYSTEM
    assert msgs[1]["content"] == "theorem t : True := by ?"     # raw, not templated


def test_openrouter_autoformalize_repairs_match_shared_prompts(monkeypatch):
    from leibniz.providers import (
        AUTOFORMALIZE_SYSTEM,
        decompose_prompt,
        repair_contract_prompt,
        repair_formalization_prompt,
    )
    from leibniz.providers.openrouter_provider import OpenRouterProvider

    p = OpenRouterProvider(model="z-ai/glm-5.2")
    cap = _capture_openrouter(monkeypatch, "{}")
    p.repair_formalization("claim", "prior", "lean err")
    assert cap["body"]["messages"][0]["content"] == AUTOFORMALIZE_SYSTEM
    assert cap["body"]["messages"][1]["content"] == repair_formalization_prompt("claim", "prior", "lean err")

    p.repair_contract("claim", "n>=0", "p", "n>=0", ["bad"])
    assert cap["body"]["messages"][1]["content"] == \
        repair_contract_prompt("claim", "n>=0", "p", "n>=0", ["bad"])

    p.decompose("theorem t : P")
    assert cap["body"]["messages"][1]["content"] == decompose_prompt("theorem t : P")


def test_anthropic_and_openrouter_build_identical_conjecture_prompt():
    # No-drift guarantee: both providers source the SAME template, so a failover conjecture is
    # the same prompt the primary would have sent.
    from leibniz.providers import AUTOFORMALIZE_PROMPTS
    from leibniz.providers.anthropic_provider import _PROMPTS as ANTHROPIC_PROMPTS

    assert ANTHROPIC_PROMPTS is AUTOFORMALIZE_PROMPTS
    assert ANTHROPIC_PROMPTS[Role.CONJECTURE] == AUTOFORMALIZE_PROMPTS[Role.CONJECTURE]
