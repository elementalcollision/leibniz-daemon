"""ADR 0033 Slice 3: per-instance kernel + corpus pinning.

PROD runs the audited, code-pinned Lean image + checked-in corpus and refuses an
experimental override (fail-safe); UAT/dev honour overrides so they can soak experimental
artifacts. The resolved images + corpus content version are recorded per instance for audit.

CI-safe (pure Python, no Lean/Docker) — and deliberately NOT in test_invariants.py, which
stays byte-identical (this selects audited artifacts and records them; it is not a trust-edge
change — LeanVerifier.discharge is still the sole kernel_verified writer).
"""
from __future__ import annotations

import json

from leibniz.backends.lean_cli import DEFAULT_IMAGE
from leibniz.backends.lean_repl import REPL_IMAGE
from leibniz.instance_config import (
    InstanceConfig,
    resolve_instance_config,
    write_provenance,
)


def test_defaults_to_dev_and_audited_pins(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_INSTANCE", raising=False)
    monkeypatch.delenv("LEIBNIZ_LEAN_IMAGE", raising=False)
    monkeypatch.delenv("LEIBNIZ_CORPUS_PATH", raising=False)
    cfg = resolve_instance_config()
    assert cfg.instance == "dev"
    assert cfg.lean_image == DEFAULT_IMAGE
    assert cfg.lean_repl_image == REPL_IMAGE
    assert cfg.corpus_version.startswith("sha256:")  # the real corpus hashed


def test_prod_refuses_experimental_overrides(monkeypatch):
    # A misconfigured deploy must NOT be able to swap PROD's kernel/corpus via env.
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    monkeypatch.setenv("LEIBNIZ_LEAN_IMAGE", "leibniz-lean:experimental")
    monkeypatch.setenv("LEIBNIZ_LEAN_REPL_IMAGE", "leibniz-lean-repl:experimental")
    monkeypatch.setenv("LEIBNIZ_CORPUS_PATH", "/tmp/rogue_corpus.json")
    cfg = resolve_instance_config()
    assert cfg.instance == "prod"
    assert cfg.lean_image == DEFAULT_IMAGE          # audited pin, override ignored
    assert cfg.lean_repl_image == REPL_IMAGE
    assert cfg.corpus_path.endswith("known_results.json")  # the checked-in corpus, not the rogue one


def test_uat_honours_overrides(monkeypatch, tmp_path):
    corpus = tmp_path / "experimental_corpus.json"
    corpus.write_text("[]")
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "UAT")   # case-insensitive
    monkeypatch.setenv("LEIBNIZ_LEAN_IMAGE", "leibniz-lean:v4.32.0-rc")
    monkeypatch.setenv("LEIBNIZ_CORPUS_PATH", str(corpus))
    cfg = resolve_instance_config()
    assert cfg.instance == "uat"
    assert cfg.lean_image == "leibniz-lean:v4.32.0-rc"
    assert cfg.corpus_path == str(corpus)
    assert cfg.corpus_version.startswith("sha256:")  # the experimental corpus hashed


def test_explicit_instance_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "uat")
    assert resolve_instance_config("prod").instance == "prod"


def test_corpus_version_tracks_content(monkeypatch, tmp_path):
    c = tmp_path / "c.json"
    c.write_text("[]")
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "dev")
    monkeypatch.setenv("LEIBNIZ_CORPUS_PATH", str(c))
    v1 = resolve_instance_config().corpus_version
    c.write_text('[{"name": "x"}]')               # mutate the corpus
    v2 = resolve_instance_config().corpus_version
    assert v1 != v2 and v1.startswith("sha256:")   # version is a content hash


def test_missing_corpus_is_unknown_not_fatal(monkeypatch, tmp_path):
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "dev")
    monkeypatch.setenv("LEIBNIZ_CORPUS_PATH", str(tmp_path / "nope.json"))
    assert resolve_instance_config().corpus_version == "unknown"


def test_write_provenance_appends_per_instance(tmp_path):
    cfg = InstanceConfig("uat", "img:a", "repl:a", "/c.json", "sha256:abc")
    ticks = iter([100.0, 200.0])
    p1 = write_provenance(cfg, dir=tmp_path, clock=lambda: next(ticks))
    p2 = write_provenance(cfg, dir=tmp_path, clock=lambda: next(ticks))
    assert p1 == p2 == tmp_path / "provenance-uat.jsonl"
    lines = p1.read_text().splitlines()
    assert len(lines) == 2                          # append-only history
    rec = json.loads(lines[0])
    assert rec["instance"] == "uat" and rec["lean_image"] == "img:a"
    assert rec["corpus_version"] == "sha256:abc" and rec["ts"] == 100.0


def test_write_provenance_separates_instances(tmp_path):
    write_provenance(InstanceConfig("prod", "i", "r", "/c", "v"), dir=tmp_path, clock=lambda: 1.0)
    write_provenance(InstanceConfig("uat", "i", "r", "/c", "v"), dir=tmp_path, clock=lambda: 1.0)
    assert (tmp_path / "provenance-prod.jsonl").exists()
    assert (tmp_path / "provenance-uat.jsonl").exists()  # never interleaved
