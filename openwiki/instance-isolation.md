---
type: Reference
title: Instance Isolation and the Prod/UAT/Dev Split
description: ADR 0033 per-instance isolation — the prod/uat/dev instance split with a SQLite write-barrier, a deploy-profile guard, the publish tier that only the PROD instance may publish from, and per-instance pinned Lean image + corpus (env overrides honoured only for uat/dev, ignored for prod).
tags: [instance, isolation, prod, uat, dev, write-barrier, publish-guard, deploy, pinning, provenance, adr-0033]
---

# Instance Isolation and the Prod/UAT/Dev Split

ADR 0033 adds per-instance isolation so a misconfigured UAT run can never write or publish the PROD ledger. The instance is read at call time from `LEIBNIZ_INSTANCE` (default `dev`), lowercased, and must be one of `prod`, `uat`, `dev` (`leibniz/deploy.py::VALID_INSTANCES`).

## The write-barrier (Slice 1)

`PersistentRuntime` stamps the writing `instance` on every memory row and refuses a ledger already claimed by a **different** instance (a `RuntimeError`). Legacy untagged (NULL) rows predate tagging and are exempt; the first tagged write claims the DB for that instance. So a UAT run pointed at the PROD DB **fails closed** at the SQLite layer instead of interleaving.

## The publish guard (Slice 3)

`Calculemus.publish` (see [Calculemus](../components/calculemus.md)) raises a `RuntimeError` unless the running instance is `prod` **and** the caller confirms it (`confirm_instance="prod"`). The publish can never happen by default or from a UAT/dev process — additive over the operator-approval gate, never weaker.

## The deploy-profile guard (Slice 4)

`leibniz/deploy.py::validate_profile(env)` is a pure, early check that catches the same misconfiguration at launch with a clear message:

- `LEIBNIZ_INSTANCE` must be one of `prod`/`uat`/`dev`.
- A **non-prod** instance must explicitly set each state knob (`LEIBNIZ_RUNTIME_DB`, `LEIBNIZ_FRONTIER_PATH`, `LEIBNIZ_NOTEBOOK_PATH`) to a dir **other than** PROD's `.leibniz/` — so it can never inherit or collide with the production ledger.
- A **UAT** profile must not point its published-ledger export at the prod Codex.
- A **PROD** profile must not point any state knob at a UAT path.

## Per-instance pinned kernel + corpus (Slice 3)

`leibniz/instance_config.py::resolve_instance_config` pins the audited artifacts per instance. **PROD** runs the code-pinned, audited Lean image (`leibniz-lean:v4.31.0`) and the checked-in corpus; an experimental override (`LEIBNIZ_LEAN_IMAGE` / `LEIBNIZ_LEAN_REPL_IMAGE` / `LEIBNIZ_CORPUS_PATH`) is **honoured only for `uat`/`dev`** and **ignored for `prod`** (logged). To move PROD's pin you bump the code default — a reviewed, auditable change — not a mutable env var. The resolved image tags + a content hash of the corpus are recorded per instance (`write_provenance`), so a published PROD law is traceable to the exact kernel image and corpus version.

`InstanceConfig(instance, lean_image, lean_repl_image, corpus_path, corpus_version).provenance()` is the dict recorded; `.summary()` is the human-readable string. This only selects **which** audited artifacts to use — `LeanVerifier.discharge` is still the sole `kernel_verified` writer and the Lean kernel still decides every proof. The added property is **fail-safe pinning**: PROD's kernel image cannot be changed by environment alone, which *strengthens* the boundary.

## Why this matters

A system whose value is *proven* results has one existential risk: a kernel-valid proof of a mis-stated theorem. A public ledger makes that failure permanent. Instance isolation ensures the audited PROD path — the pinned kernel, the checked-in corpus, the operator-gated publish — is the only path that can produce a public law, and that an experimental UAT/dev run can never silently contaminate it.
