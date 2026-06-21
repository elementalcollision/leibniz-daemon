"""Calculemus (R6) — the public reading-room + the operator publish tier.

The daemon *promulgates* kernel-checked laws to the Codex. **Promotion is not
publication**: a law only reaches the public *Calculemus* ledger after an explicit
operator action. This module renders promulgated Propositiones (triad + kernel
certificate + falsifiable claim) and enforces that publish gate.

Trust posture: read-only over the ledger. A law enters the Codex only if it carries
a real kernel-checked `Q.E.D.` (invariant 7) — this never hand-sets the certificate,
it reads `Demonstratio.qed`/`kernel_verified` set by `discharge`/`seal`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from leibniz.propositio import Propositio


def render_propositio(prop: Propositio) -> str:
    """Render one promulgated Propositio as a Calculemus folio (Markdown)."""
    en = prop.enuntiatio
    ex = prop.expressio
    demo = prop.demonstratio
    verified = bool(demo and demo.kernel_verified)
    return "\n".join([
        f"## {en.statement}",
        "",
        f"- **Claim type:** {en.claim_type.value}",
        f"- **Falsifiable claim:** {en.falsifiable_claim}",
        "",
        "### Expressio — formal statement",
        "```lean",
        (ex.theorem_src if ex else "(none)"),
        "```",
        "### Demonstratio — kernel-checked proof",
        "```lean",
        ((demo.proof_src or "(none)") if demo else "(none)"),
        "```",
        f"**{demo.qed if demo else 'Q.E.I.'}** · kernel_verified: {verified}"
        + (f" · obligation: `{demo.proof_obligation}`" if demo else ""),
    ])


@dataclass
class Calculemus:
    """The Codex (promulgated) + the published set (operator-promoted to public)."""

    codex: dict[str, Propositio] = field(default_factory=dict)
    published: set[str] = field(default_factory=set)

    def promulgate(self, prop: Propositio) -> bool:
        """Admit a law to the Codex — only if it carries a real kernel `Q.E.D.`."""
        demo = prop.demonstratio
        if not (prop.promulgated and demo and demo.kernel_verified and demo.qed == "Q.E.D."):
            return False
        self.codex[prop.pid] = prop
        return True

    def publish(self, pid: str, *, operator_approved: bool = False) -> bool:
        """Promote a Codex law to the public ledger. Promotion != publication: a
        human operator must explicitly approve (the daemon never calls this with
        approval). Returns False unless approved and the law is in the Codex."""
        if not operator_approved or pid not in self.codex:
            return False
        self.published.add(pid)
        return True

    def render_public(self) -> str:
        """The public Calculemus — only operator-published laws, proofs open."""
        header = "# Calculemus\n\n*The ledger of theorems settled by calculation.*\n"
        entries = [render_propositio(self.codex[pid]) for pid in self.codex if pid in self.published]
        if not entries:
            return header + "\n*(nothing published yet)*\n"
        return header + "\n" + "\n\n---\n\n".join(entries) + "\n"

    def colophon(self) -> str:
        """What is held back and why: promulgated laws awaiting operator publication."""
        held = [self.codex[pid] for pid in self.codex if pid not in self.published]
        lines = [
            "# Colophon — held back",
            "",
            f"{len(held)} promulgated law(s) await operator publication "
            "(promotion is not publication):",
        ]
        for p in held:
            d = p.demonstratio
            lines.append(f"- {p.enuntiatio.statement}  [{d.qed if d else 'Q.E.I.'}]  — awaiting operator publish")
        return "\n".join(lines)
