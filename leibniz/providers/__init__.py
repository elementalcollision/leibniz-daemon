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
import os  # noqa: E402  (env-gated DSL increment, ADR 0035 Stage A)

from leibniz.types import Role  # noqa: E402  (kept next to the prompts that use it)

AUTOFORMALIZE_SYSTEM = (
    "You are a proposal engine for an automated theorem daemon working in analysis "
    "of algorithms. You PROPOSE; a Lean kernel and mechanical gates DECIDE. Never "
    "claim something is proven. Respond with ONLY the requested JSON, no prose."
)

# ADR 0035 Stage A: the gate now soundly checks `base^n % m` (constant base, constant modulus,
# VARIABLE exponent) over the multiplicative-order period. Inviting that genre into the prompt is
# env-gated (default OFF) so main's conjecturer is unchanged until the live calibration proves it
# out — set LEIBNIZ_DSL_SYMBOLIC_EXP=1 for the Stage A experiment arm.
_SYMBOLIC_EXP = os.environ.get("LEIBNIZ_DSL_SYMBOLIC_EXP", "") not in ("", "0")
_POW_RULE = (
    "  • ^ with a CONSTANT exponent 0..8 (n^2, (a+b)^3); ALSO base^n % m with a CONSTANT base and "
    "CONSTANT modulus but a VARIABLE exponent n is allowed (ADR 0035: e.g. 2^n % 7 — checked over "
    "the multiplicative-order period). A variable exponent OUTSIDE a mod, a compound exponent "
    "(2^(n+1)), or a non-constant base is still forbidden.\n"
    if _SYMBOLIC_EXP else
    "  • ^ with a CONSTANT exponent 0..8 (n^2, (a+b)^3) — NOT a variable exponent\n"
)
_FORBIDDEN_EXP = ("VARIABLE exponents outside a mod (2^n alone, k^n, 2^(n+1))"
                  if _SYMBOLIC_EXP else "VARIABLE exponents (2^n, k^n)")

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
    f"{_POW_RULE}"
    "  • / and % by a CONSTANT positive divisor (n/2, n%3)\n"
    "  • min(a, b) and max(a, b) — two or more integer arguments (ADR 0030)\n"
    "  • factorial(n) and gcd(a, b) — BARE-VARIABLE or constant arguments ONLY "
    "(factorial(n+1) or gcd(a*b, c) are un-checkable) (ADR 0066)\n"
    "  • comparisons < <= > >= == != ; and / or / not ; parentheses\n"
    "FORBIDDEN (these make the claim un-checkable): named functions other than the four "
    "above (log, sqrt, Nat.log, floor, sums/products), compound arguments to "
    f"factorial/gcd, {_FORBIDDEN_EXP}, "
    "division/modulo by a variable, real/rational numbers, quantifiers inside "
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
        "RAISE THE AMBITION — the single-variable one-modulus reflex is a RUT. A long run of "
        "`P(n) % m` residue/divisibility facts about ONE variable has been mined out; the ledger "
        "now dedups restatements, so another such claim will likely be KNOWN or a near-duplicate. "
        "Prefer a structurally RICHER claim that still fits the DSL below:\n"
        "  • TWO or MORE variables with a genuine INTERACTION — a residue/divisibility/inequality "
        "about a*b, (a+b)^k, a^2+b^2, or a mixed form that must hold for ALL a,b (not reducible to "
        "a one-variable fact);\n"
        "  • min / max invariants (ADR 0030) — a non-obvious identity or bound combining min(a,b) "
        "and max(a,b) with +,*,% that needs case analysis on which is larger;\n"
        "  • a RESIDUE-SET or a RELATION between two constructed quantities (X < Y, X | Y-shaped as "
        "`Y % X-form`, or `Q1 % m == Q2 % m`), not just one expression's residue;\n"
        "  • an uncommon COMPOSITE modulus (e.g. mod 9, 12, 16, 24) whose residue structure needs "
        "CRT-style case analysis rather than parity.\n"
        "Pick the most SURPRISING such claim you are still confident is TRUE and provable — depth "
        "over another safe single-variable residue.\n"
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
    # ADR 0038: a claim for the Walnut-decided tier. This is NOT a Lean contract — it is a
    # first-order formula over a k-automatic sequence that Walnut decides over UNBOUNDED n.
    Role.WALNUT_CONJECTURE: (
        "Propose ONE genuinely NON-textbook conjecture about a k-AUTOMATIC SEQUENCE, "
        "expressible as a first-order formula with EXACTLY ONE free variable n over a "
        "numeration Walnut decides (msd_2, msd_fib, msd_trib). Good built-in sequences: "
        "Thue-Morse T, Rudin-Shapiro RS, paperfolding P, Fibonacci word F, Tribonacci TR. "
        "AVOID first-year facts; aim for properties proved with Walnut in the Shallit-group "
        "literature: power-/overlap-freeness, factor/subword structure, appearance, or "
        "additive properties. The formula must be TRUE for ALL n (the tier decides "
        "universality over unbounded n; a false one is REFUTED).\n"
        "WALNUT SYNTAX for walnut_predicate (n is the ONLY free variable): quantifiers "
        "`E i` / `A i` (and `E i,p` / `A i,p` to bind several); boolean `&` `|` `~` `=>`; "
        "comparisons `< <= = != >= >`; ADDITION ONLY between variables (NO `i*p`; write 3*p "
        "as p+p+p); index a sequence as `T[i+p]`; test a value as `T[i]=@0`. Do NOT put "
        "double-quotes, semicolons, or newlines inside walnut_predicate.\n"
        "Example (FORMAT only — Thue-Morse is overlap-free): walnut_numeration = \"msd_2\", "
        "walnut_predicate = \"A i,p (p>=1) => (E t (t<3*p) & T[i+t] != T[i+t+p])\". "
        "Treat this as the SHAPE, not a claim to resubmit; vary the sequence/property.\n"
        "FAITHFULNESS (REQUIRED): also return a property_descriptor — a HIGH-LEVEL, "
        "machine-checkable spec of EXACTLY the property your predicate is meant to encode. It "
        "must NOT contain any bound arithmetic (that lives only in walnut_predicate); a separate "
        "checker brute-forces it over a prefix and QUARANTINES your claim if the predicate "
        "disagrees with it. Choose ONE family and fill its parameters; word is one of "
        "T, RS, F, TR (paperfolding is not yet checkable):\n"
        '  power_free:     {{"family":"power_free","word":"RS","exponent":<e>=2>}}  '
        "(the word has NO e-th power; e.g. cube-free is exponent 3)\n"
        '  avoids_factor:  {{"family":"avoids_factor","word":"T","block":"00"}}  '
        "(the exact digit block never occurs)\n"
        '  avoids_pattern: {{"family":"avoids_pattern","word":"RS","pattern":"alternating","length":<L>}}  '
        "(no strictly alternating 0101…/1010… factor of length L)\n"
        "Pick the family that matches your statement; if none fits, pick a DIFFERENT property "
        "that does (do not invent a family — an unrecognised descriptor is quarantined). The "
        "descriptor's \"word\" MUST be the SAME sequence your walnut_predicate indexes (a "
        "mismatch is quarantined), and it must describe EXACTLY that property — not a different "
        "true fact about the sequence.\n"
        "Context: {context}\n"
        'Return JSON: {{"statement": <plain-English claim>, '
        '"walnut_predicate": <FO formula in n, per the syntax above>, '
        '"walnut_numeration": <e.g. msd_2>, '
        '"property_descriptor": <one family object from above>, '
        '"falsifiable_claim": <what would refute it>}}'
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
