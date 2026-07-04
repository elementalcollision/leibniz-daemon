"""Guard the process-complexity certificate domain (scripts/process_complexity_domain.py) — a reusable
interface certifying a process's beyond-Markov complexity, each part naming its kernel-verified lemma. Fully
CI-safe (exact-rational Fractions; no z3/Lean). No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("process_complexity_domain",
                                                  _ROOT / "scripts" / "process_complexity_domain.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_registry_certifies_the_beyond_markov_witnesses():
    m = _load()
    reg = m.registry()
    names = {p["name"] for p in reg}
    assert any("even process" in n for n in names) and any("2-mode" in n for n in names)
    for p in reg:
        c = m.certify(p)
        assert c["validity"]["valid_hmm"] is True             # a genuine stochastic process (HMM)
        assert c["hankel"]["rank"] == 2 and c["hankel"]["rank_lower_ok"] is True   # rank 2, minor-certified
        assert c["markov_order"]["all_hold"] is True          # order > K
        assert c["kernel_lemmas"]                              # names the lemma(s) attesting it
        assert c["certified"] is True


def test_even_process_names_the_infinite_order_lemma():
    m = _load()
    ev = next(p for p in m.registry() if "even process" in p["name"])
    c = m.certify(ev)
    assert any("even_infinite_order" in name for name in c["kernel_lemmas"])
    assert any("hankel_block_rank_le" in name for name in c["kernel_lemmas"])


def test_necklace_positive_realization_certificate():
    m = _load()
    neck = m.necklace_positive_realization()
    assert neck["hankel_rank"] == 3 and neck["minimal_positive_realization"] == 4   # 4 > 3 = rank
    assert neck["fooling_size4_valid"] is True and neck["hankel_rank_stable_3"] is True
    assert "necklace_positive_realization_needs_4" in neck["kernel_lemmas"]
    assert neck["certified"] is True


def test_domain_is_honestly_labelled_amplification():
    # The domain report must carry the honest EV — this is not a discovery domain.
    m = _load()
    reg = m.registry()
    assert all(m.certify(p)["certified"] for p in reg) and m.necklace_positive_realization()["certified"]
    # the module docstring commits to the honest disposition
    assert "AMPLIFICATION" in m.__doc__ and "textbook" in m.__doc__
