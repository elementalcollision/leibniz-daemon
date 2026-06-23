"""The urllib providers must send a non-default User-Agent.

Python-urllib's default UA is bot-blocked by some Cloudflare-fronted gateways (Featherless
returns 403 "error code: 1010"). A live pre-flight surfaced this; here we lock it in:
the OpenAI-compatible client sends our descriptive UA. CI-safe (urlopen is mocked)."""
from __future__ import annotations

import json
import urllib.request

from leibniz.providers import USER_AGENT
from leibniz.providers.openrouter_provider import OpenRouterProvider
from leibniz.types import Role


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "by simp"}}]}).encode()


def test_openai_compatible_client_sends_user_agent(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, *a, **k):
        captured["headers"] = {kk.lower(): vv for kk, vv in req.header_items()}
        return _Resp()

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = OpenRouterProvider(model="m").propose(Role.PROOF_DRAFT, "theorem t : True")
    assert out == "by simp"
    assert captured["headers"].get("user-agent") == USER_AGENT
    assert "python-urllib" not in captured["headers"].get("user-agent", "").lower()
