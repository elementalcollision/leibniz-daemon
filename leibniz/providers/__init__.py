"""R4 proposal providers — real LLMs in the proposal-only roles (ADR 0001/0005).

These never decide: every draft re-enters the mechanical gates and the kernel. All
providers are lazy + env-gated, so the package imports without the `propose` extra
and makes no network call until credentials are configured.
"""


class ProviderUnavailable(RuntimeError):
    """Raised when a provider is asked to propose but is not configured (no SDK or
    no credentials). Callers/tests check ``available()`` first."""
