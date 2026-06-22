"""R4 proposal providers — real LLMs in the proposal-only roles (ADR 0001/0005).

These never decide: every draft re-enters the mechanical gates and the kernel. All
providers are lazy + env-gated, so the package imports without the `propose` extra
and makes no network call until credentials are configured.
"""


class ProviderUnavailable(RuntimeError):
    """Raised when a provider is asked to propose but is not configured (no SDK or
    no credentials). Callers/tests check ``available()`` first."""


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
