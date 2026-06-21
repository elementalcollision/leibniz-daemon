"""Hosted prover client for PROOF_DRAFT (R4) — Goedel-Prover-V2 / DeepSeek-Prover class.

Proposal-only: returns a tactic-script draft for the kernel to check; it never
decides. stdlib `urllib` (no new dependency); env-gated. Point ``LEIBNIZ_PROVER_URL``
at a hosted endpoint now and at a rented A100 later — config, not code (D5).
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from leibniz.providers import ProviderUnavailable
from leibniz.types import Role


@dataclass
class ProverClient:
    url_env: str = "LEIBNIZ_PROVER_URL"
    key_env: str = "LEIBNIZ_PROVER_KEY"
    timeout_s: int = 120

    def available(self) -> bool:
        return bool(os.environ.get(self.url_env))

    def propose(self, role: Role, context: str) -> str:
        url = os.environ.get(self.url_env)
        if not url:
            raise ProviderUnavailable(f"{self.url_env} not set")
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self.key_env)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = json.dumps({"statement": context}).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310 (configured endpoint)
            data = json.loads(resp.read().decode())
        # Accept a few common field names; the result is a tactic script the kernel checks.
        return data.get("proof_src") or data.get("proof") or data.get("text") or ""
