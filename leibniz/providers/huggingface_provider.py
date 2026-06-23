"""HuggingFace proposal provider (HF Inference router, OpenAI-compatible) — for the
PROOF_DRAFT prover ensemble.

The specialized provers (DeepSeek-Prover-V2 / Goedel-Prover class) live on HuggingFace,
not OpenRouter. This calls HF's router (`router.huggingface.co/v1/chat/completions`,
OpenAI-compatible) with `HUGGINGFACE_API_KEY`. Proposal-only (ADR 0001): it returns a
tactic-script draft the kernel checks; it never decides. stdlib `urllib` + a certifi
SSL context (the macOS trust-store fix); model id is per-instance so the same class
serves every member of the ensemble.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Optional

from leibniz.providers import USER_AGENT, ProviderUnavailable, ssl_context
from leibniz.types import Role

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

_PROOF_SYSTEM = (
    "You draft Lean 4 tactic scripts for a theorem daemon. Output ONLY the proof "
    "term/script (e.g. starting with `by`), no prose, no backticks. You PROPOSE; "
    "a Lean kernel DECIDES — never claim the proof is correct."
)
_GENERIC_SYSTEM = (
    "You propose for an automated theorem daemon; mechanical checkers decide. "
    "Respond with ONLY the requested content."
)


@dataclass
class HuggingFaceProvider:
    model: str
    api_key_env: str = "HUGGINGFACE_API_KEY"
    url: str = HF_ROUTER_URL
    max_tokens: int = 2048
    timeout_s: int = 180
    meter: Optional[object] = None  # ADR 0014: has .record_usage(model, in, out)

    def available(self) -> bool:
        return bool(os.environ.get(self.api_key_env))

    def propose(self, role: Role, context: str) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderUnavailable(f"{self.api_key_env} not set")
        system = _PROOF_SYSTEM if role is Role.PROOF_DRAFT else _GENERIC_SYSTEM
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": context},
            ],
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                     "User-Agent": USER_AGENT},  # avoid urllib's default UA being bot-blocked
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_s, context=ssl_context()) as resp:  # noqa: S310 (fixed gateway)
            data = json.loads(resp.read().decode())
        self._meter(data)
        return data["choices"][0]["message"]["content"].strip()

    def _meter(self, data: dict) -> None:
        """ADR 0014: report real token usage to the cost meter (best-effort)."""
        if self.meter is None:
            return
        usage = data.get("usage") or {}
        try:
            self.meter.record_usage(
                self.model,
                int(usage.get("prompt_tokens", 0) or 0),
                int(usage.get("completion_tokens", 0) or 0),
            )
        except Exception:  # metering must never break a proposal
            pass
