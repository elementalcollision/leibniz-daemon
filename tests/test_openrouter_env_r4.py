"""R4.1: OpenRouter provider gating + the .env loader (CI-safe, no network)."""
from __future__ import annotations

import os

import pytest

from leibniz.env import load_env
from leibniz.providers import ProviderUnavailable
from leibniz.providers.openrouter_provider import OpenRouterProvider
from leibniz.types import Role


def test_openrouter_unavailable_and_raises_without_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    p = OpenRouterProvider(model="deepseek/deepseek-prover-v2")
    assert p.available() is False
    with pytest.raises(ProviderUnavailable):
        p.propose(Role.PROOF_DRAFT, "theorem t : P")


def test_openrouter_available_with_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    assert OpenRouterProvider(model="x/y").available() is True


def test_load_env_sets_missing_vars(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('FOO_TEST=bar\n# a comment\nQUOTED_TEST="baz"\n\n')
    monkeypatch.delenv("FOO_TEST", raising=False)
    monkeypatch.delenv("QUOTED_TEST", raising=False)
    n = load_env(f)
    assert n == 2
    assert os.environ.get("FOO_TEST") == "bar"
    assert os.environ.get("QUOTED_TEST") == "baz"


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("X_TEST=fromfile\n")
    monkeypatch.setenv("X_TEST", "fromenv")
    load_env(f)
    assert os.environ.get("X_TEST") == "fromenv"


def test_load_env_missing_file_is_noop():
    assert load_env("/nonexistent/path/.env") == 0
