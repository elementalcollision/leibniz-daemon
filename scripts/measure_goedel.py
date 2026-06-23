"""Harness A (ADR 0028, lever 3): run a calibration with Goedel-Prover-V2 as the prover.

Points Leibniz's OpenAI-compatible prover client at a gateway serving Goedel-Prover-V2
(default: Featherless) so a STRONGER open model than the current HF ensemble drives
proving — config only, no model code. Goedel-V2-8B already beats DeepSeek-Prover-V2-671B
on miniF2F; this measures whether raw-model strength alone lifts the non-trivial close
rate before we invest in the agentic loop (ADR 0029, option C).

Put the gateway key in .env under the name in LEIBNIZ_PROVER_KEY_ENV (default
FEATHERLESS_API_KEY). Override model/endpoint via env. BILLABLE.

    # Featherless (hosted, OpenAI-compatible)
    python scripts/measure_goedel.py [cycles] [seeds] [cap_usd]
    # self-hosted vLLM:
    LEIBNIZ_PROVER_BASE_URL=http://localhost:8000/v1/chat/completions \
    LEIBNIZ_PROVER_KEY_ENV=DUMMY python scripts/measure_goedel.py 3 2 0
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # import sibling calibrate_discovery


def main() -> int:
    os.environ.pop("LEIBNIZ_HF_PROVER_MODELS", None)  # force the OpenAI-compatible path
    os.environ.setdefault("LEIBNIZ_PROVER_MODELS", "Goedel-LM/Goedel-Prover-V2-32B")
    os.environ.setdefault("LEIBNIZ_PROVER_BASE_URL", "https://api.featherless.ai/v1/chat/completions")
    os.environ.setdefault("LEIBNIZ_PROVER_KEY_ENV", "FEATHERLESS_API_KEY")
    os.environ.setdefault("LEIBNIZ_DECOMPOSE", "0")  # isolate raw-model strength first
    print(f"[measure_goedel] prover {os.environ['LEIBNIZ_PROVER_MODELS']} via "
          f"{os.environ['LEIBNIZ_PROVER_BASE_URL']} (key env {os.environ['LEIBNIZ_PROVER_KEY_ENV']})")
    import calibrate_discovery
    return calibrate_discovery.main()


if __name__ == "__main__":
    raise SystemExit(main())
