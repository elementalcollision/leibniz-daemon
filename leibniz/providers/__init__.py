"""R4 proposal providers — real LLMs in the proposal-only roles (ADR 0001/0005).

These never decide: every draft re-enters the mechanical gates and the kernel. All
providers are lazy + env-gated, so the package imports without the `propose` extra
and makes no network call until credentials are configured.
"""


# A descriptive User-Agent for the urllib-based providers. Python-urllib's default UA is
# blocked by some Cloudflare-fronted gateways (e.g. Featherless returns 403 "error code:
# 1010" — banned-by-signature); an honest non-default UA passes the bot check. Not
# deceptive — we are a real client with a valid key.
USER_AGENT = "leibniz-daemon/0.1 (+https://github.com/elementalcollision/leibniz-daemon)"


class ProviderUnavailable(RuntimeError):
    """Raised when a provider is asked to propose but is not configured (no SDK or
    no credentials). Callers/tests check ``available()`` first."""


def repair_proof_prompt(theorem_src: str, failed_proof: str, error: str) -> str:
    """The ADR 0029 proof-repair user prompt, shared by every repair-capable provider
    (AnthropicProvider, OpenRouterProvider) so the two cannot drift. Requests a BARE ``by …``
    script; the statement is fixed (changing it would 'prove' a different, weaker claim) and
    the kernel re-checks whatever comes back — this only proposes."""
    return (
        "Your Lean 4 proof FAILED to verify. Repair it using the kernel's error. Output ONLY "
        "the corrected proof — a tactic script starting with `by` — no prose, no backticks. Do "
        "NOT change, restate, or weaken the theorem; fix only the proof. Toolchain is Lean 4.31 "
        "+ current Mathlib (prefer `import Mathlib.Tactic` lemmas/tactics). You PROPOSE; the "
        "Lean kernel DECIDES — do not claim the repair is correct.\n"
        f"Theorem (do NOT change):\n{theorem_src}\n"
        f"Failed proof:\n{failed_proof}\n"
        f"Lean error:\n{error[:1500]}"
    )


# --- Autoformalize prompts (CONJECTURE / FORMALIZE + their repairs) -----------------------
# Single source of truth, shared by every autoformalize-capable provider (AnthropicProvider
# primary + OpenRouterProvider failover backups), so the two cannot drift — exactly as
# repair_proof_prompt is shared for the proof role. Routing conjecture/formalize through a
# backup model during an Anthropic outage stays proposal-only (ADR 0001): the faithfulness /
# novelty gates and the Lean kernel still decide every candidate.
from leibniz.types import Role  # noqa: E402  (kept next to the prompts that use it)

AUTOFORMALIZE_SYSTEM = (
    "You are a proposal engine for an automated theorem daemon working in analysis "
    "of algorithms. You PROPOSE; a Lean kernel and mechanical gates DECIDE. Never "
    "claim something is proven. Respond with ONLY the requested JSON, no prose."
)

# ADR 0022: the faithfulness checker can only certify a contract whose predicates
# live in this sound, Z3-decidable arithmetic DSL (ADR 0021). A contract outside it
# DEFERs before any proof compute — so it can never be promulgated. Steer proposals
# INTO the grammar; this is the single source of truth quoted to both roles.
AUTOFORMALIZE_DSL = (
    "FAITHFULNESS DSL — the contract predicates must use ONLY these constructs, or "
    "the claim is rejected (DEFERred) before it can ever be proven:\n"
    "  • non-negative integer variables — name them freely (n, a, b, k, ...)\n"
    "  • non-negative integer literals\n"
    "  • + - *  (add, subtract, multiply)\n"
    "  • ^ with a CONSTANT exponent 0..8 (n^2, (a+b)^3) — NOT a variable exponent\n"
    "  • / and % by a CONSTANT positive divisor (n/2, n%3)\n"
    "  • min(a, b) and max(a, b) — two or more integer arguments (ADR 0030)\n"
    "  • comparisons < <= > >= == != ; and / or / not ; parentheses\n"
    "FORBIDDEN (these make the claim un-checkable): named functions (log, sqrt, gcd, "
    "factorial, Nat.log, floor, sums/products), VARIABLE exponents (2^n, "
    "k^n), division/modulo by a variable, real/rational numbers, quantifiers inside "
    "a predicate. If the natural claim needs any of these, RESTATE it as an "
    "elementary-arithmetic statement that does fit (e.g. a concrete polynomial bound, "
    "a divisibility/mod identity) — that is the novel-yet-tractable band."
)

AUTOFORMALIZE_PROMPTS = {
    Role.CONJECTURE: (
        "Propose ONE conjecture that is (a) NOVEL — not a textbook/Mathlib result, "
        "(b) genuinely NON-TRIVIAL, and (c) PLAUSIBLY PROVABLE with standard Mathlib "
        "tactics, possibly needing a short helper lemma or induction. The aim is the "
        "band of the novel-yet-tractable. Honour any lessons and target difficulty band "
        "in the context (emulate what proved, AVOID what was trivial/known, weaken what "
        "was too hard).\n"
        "NON-TRIVIALITY IS ENFORCED MECHANICALLY: a statement that a SINGLE decision "
        "procedure closes on its own — `decide`, `simp`, `omega`, `trivial`, `aesop`, "
        "`ring`, or `nlinarith` — is quarantined as TRIVIAL and can NEVER be promulgated. "
        "So DO NOT propose a pure polynomial identity or a polynomial (in)equality: "
        "`ring`/`nlinarith` close those instantly. Aim instead for claims needing "
        "INDUCTION, CASE ANALYSIS, or a HELPER LEMMA — e.g. a divisibility or modular "
        "fact about a NON-LINEAR expression, or a property that holds by parity / "
        "recursion.\n"
        "KNOWN FAMILIES ARE ALSO QUARANTINED (as KNOWN, ADR 0031): the corpus now holds the "
        "classic results and a RESTATEMENT is caught by decision-procedure equivalence, so do "
        "NOT propose these or any restatement of them — (1) Fermat's little theorem "
        "(n^p mod p == n mod p for prime p), (2) power-residue facts (n^k mod m == n mod m, or "
        "n^k - n divisible by m), and (3) consecutive-product divisibilities (k! divides any k "
        "consecutive integers, e.g. 6 | n*(n+1)*(n+2)). These are non-trivial yet TEXTBOOK; "
        "proposing them wastes the cycle. Seek a GENUINELY NOVEL pattern — a non-standard "
        "modulus/coefficient combination, or a property that is not a named theorem.\n"
        "VARY THE STRUCTURE across cycles (ADR 0034): if the context lists EXHAUSTED FAMILIES "
        "or FLAVOUR exemplars, do NOT propose another member of a shape you have already proved "
        "— reach for a DIFFERENT structure (e.g. characterize a residue SET like n^2 mod 4 in "
        "{{0,1}}, or relate two quantities), not yet another divisibility of a fresh polynomial.\n"
        "If the seed is a COMPUTED PATTERN (ADR 0034 Stage 2): it is empirical data already "
        "verified true by enumeration — formalize and explain THAT EXACT fact faithfully (it is "
        "the claim_property), do not free-associate to a different or weaker claim.\n"
        "The claim must come with a machine-checkable CONTRACT (claim_domain, "
        "claim_property): for all integer inputs satisfying claim_domain, claim_property "
        "holds. BOTH predicates MUST be inside the DSL below.\n"
        f"{AUTOFORMALIZE_DSL}\n"
        "Example (illustrating the FORMAT — a non-trivial, encodable modular fact NOT in the "
        "known families above) — statement \"n^2 + 3 is never congruent to 2 modulo 4\"; "
        "claim_domain \"n >= 0\"; claim_property \"(n^2 + 3) % 4 != 2\" — needs case analysis on "
        "parity (n^2 mod 4 is 0 or 1), so no single decision procedure closes it, yet the "
        "contract is plain DSL. Treat this as the SHAPE, not a claim to resubmit.\n"
        "Context: {context}\n"
        'Return JSON: {{"statement": <human claim>, "claim_type": '
        '"complexity_bound|correctness|optimality|invariant|existence|structural|open_form", '
        '"falsifiable_claim": <what would refute it>, '
        '"claim_domain": <DSL predicate bounding the inputs>, '
        '"claim_property": <DSL predicate the claim asserts on that domain>}}'
    ),
    Role.FORMALIZE: (
        "Formalize this claim as a Lean 4 theorem statement (header only, no proof): {context}\n"
        "Also give established_domain: the DSL predicate over the same integer "
        "variables that the formal statement ACTUALLY establishes the property on. It "
        "must COVER claim_domain (be at least as broad) and stay inside the DSL.\n"
        f"{AUTOFORMALIZE_DSL}\n"
        'Return JSON: {{"theorem_src": "theorem name : ...", '
        '"imports": ["Mathlib.Tactic"], '
        '"established_domain": <DSL predicate the statement covers>}}'
    ),
    Role.PROOF_DRAFT: (
        "Draft a Lean 4 tactic script proving this statement. Return ONLY the script "
        "starting with `by`:\n{context}"
    ),
}


def repair_formalization_prompt(statement: str, prior_src: str, error: str) -> str:
    """R4.2: hand a failed Lean compile back to the autoformalizer to fix the
    imports/statement, given the kernel's actual error. Shared so the failover backup
    repairs identically. Returns the user prompt; the caller requests corrected JSON."""
    return (
        "Your Lean 4 formalization failed to compile. Fix it. Toolchain is Lean "
        "4.31 + current Mathlib — module paths may have moved since older Mathlib. "
        "If an import 'does not exist', replace it with the correct current module "
        "or drop it and rely on `import Mathlib.Tactic`. Keep the statement "
        "faithful to the claim; do not weaken it to make it compile.\n"
        f"Claim: {statement}\n"
        f"Previous attempt:\n{prior_src}\n"
        f"Lean error:\n{error[:1500]}\n"
        'Return corrected JSON only: {"theorem_src": "theorem name : ...", '
        '"imports": ["Mathlib.Tactic", ...], "established_domain": "<predicate over n>"}'
    )


def repair_contract_prompt(
    statement: str, claim_domain: str, claim_property: str,
    established_domain: str, problems: list,
) -> str:
    """ADR 0022 contract-repair user prompt, shared by primary + failover backup."""
    return (
        "The machine-checkable CONTRACT for your claim cannot be verified: these "
        f"fields use constructs outside the decidable DSL: {', '.join(problems)}. "
        "Restate ALL THREE predicates so each is inside the DSL, WITHOUT changing "
        "what the claim means.\n"
        f"{AUTOFORMALIZE_DSL}\n"
        f"Claim (do NOT change): {statement}\n"
        "Current contract:\n"
        f"  claim_domain: {claim_domain}\n"
        f"  claim_property: {claim_property}\n"
        f"  established_domain: {established_domain}\n"
        "Rules: keep claim_domain NON-EMPTY and just as broad (adding constraints "
        "to shrink it is cheating and will be rejected); keep claim_property at "
        "least as STRONG (a weaker/hollowed property is rejected — the new one must "
        "imply the old); established_domain must COVER claim_domain; preserve the "
        "mathematical meaning. If the claim genuinely cannot be expressed in this "
        "DSL, return the fields unchanged.\n"
        'Return JSON only: {"claim_domain": "...", "claim_property": "...", '
        '"established_domain": "..."}'
    )


def decompose_prompt(theorem_src: str) -> str:
    """ADR 0027 decomposition user prompt, shared by primary + failover backup."""
    return (
        "This Lean 4 theorem is hard to prove in one shot. DECOMPOSE it: propose 1-4 "
        "helper LEMMAS that, once proven, make the main proof short, plus the main "
        "proof that uses them BY NAME. Each lemma must be a self-contained Lean 4 "
        "statement provable on its own (induction / case analysis welcome), and "
        "genuinely useful for the main goal. Name them aux1, aux2, ... Use ONLY "
        "`lemma`/tactic proofs — never `axiom`, `sorry`, `admit`, or `opaque`.\n"
        f"Theorem:\n{theorem_src}\n"
        'Return JSON only: {"lemmas": [{"name": "aux1", "statement": "<binders> : '
        '<prop>"}], "main_proof": "by <tactic script citing aux1, aux2, ...>"}. '
        'The lemma "statement" is everything AFTER the lemma name, e.g. '
        '"(n : Nat) : 2 ∣ n * (n + 1)". One line per statement, no `:=`.'
    )


def ssl_context():
    """An SSL context for the urllib-based providers (OpenRouter, HuggingFace).

    Prefer certifi's CA bundle — on some platforms (notably macOS framework Python)
    the system trust store is empty for OpenSSL, so a bare `urlopen` fails with
    CERTIFICATE_VERIFY_FAILED. Falls back to the default context if certifi is absent.
    Returns None when no context can be built (let urllib use its default)."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        try:
            return ssl.create_default_context()
        except Exception:
            return None
