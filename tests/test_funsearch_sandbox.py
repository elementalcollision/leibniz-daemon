"""Guard the untrusted-code sandbox + LLM-free evaluator (the FunSearch security boundary).

Two layers: (1) docker-independent unit tests pin the isolation argv, the output parsing, and the
evaluator's re-check contract; (2) docker-gated integration tests prove the container ACTUALLY isolates
(no network, killed on timeout) and that benign programs round-trip. The sandbox output is untrusted —
the evaluator must re-validate it with verify_cwc and must never trust a self-reported beat.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m            # register before exec so @dataclass introspection resolves
    spec.loader.exec_module(m)
    return m


sb = _load("funsearch_sandbox", "scripts/funsearch_sandbox.py")

FANO_PROG = ("def construct(n, d, w):\n"
             "    return [[0,1,2],[0,3,4],[0,5,6],[1,3,5],[1,4,6],[2,3,6],[2,4,5]]\n")


# --- isolation argv (pure) ----------------------------------------------------------------------
def test_docker_argv_is_locked_down():
    argv = sb._docker_argv("nm", sb.DEFAULT_IMAGE, "512m", "1.0", 128)
    s = " ".join(argv)
    assert "--network none" in s                      # no network
    assert "--read-only" in s                         # read-only root
    assert "--rm" in argv and "-i" in argv
    assert "--cap-drop" in argv and "ALL" in argv
    assert "no-new-privileges" in s
    assert "--pids-limit" in argv                      # fork-bomb guard
    assert "--memory" in argv and "--cpus" in argv
    assert "--user" in argv and "65534:65534" in argv  # runs as nobody
    assert "-v" not in argv                            # CRITICAL: no host filesystem mount


def test_memory_swap_equals_memory_so_no_swap():
    argv = sb._docker_argv("nm", sb.DEFAULT_IMAGE, "256m", "1.0", 64)
    i = argv.index("--memory-swap")
    assert argv[i + 1] == "256m"


# --- output parsing (pure) ----------------------------------------------------------------------
def test_parse_valid_result():
    r = sb._parse_output("noise\n" + sb.RESULT_SENTINEL + "[[0,1,2],[3,4,5]]\n")
    assert r.ok is True and r.code == [[0, 1, 2], [3, 4, 5]]


def test_parse_takes_last_sentinel_not_a_spoof():
    # a program that prints a fake result line cannot displace the harness's real (last) line
    out = sb.RESULT_SENTINEL + "[[9,9,9]]\n" + sb.RESULT_SENTINEL + "[[0,1,2]]\n"
    assert sb._parse_output(out).code == [[0, 1, 2]]


def test_parse_error_sentinel():
    r = sb._parse_output(sb.ERROR_SENTINEL + '"boom"\n')
    assert r.ok is False and "boom" in r.error


def test_parse_no_sentinel_is_a_clean_failure():
    r = sb._parse_output("segfault\n")
    assert r.ok is False and "no result" in r.error


# --- evaluator re-check contract (pure; run_program monkeypatched) -------------------------------
def test_evaluator_validates_and_scores_a_good_code(monkeypatch):
    monkeypatch.setattr(sb, "run_program",
                        lambda *a, **k: sb.SandboxResult(True, [[0, 1, 2], [0, 3, 4], [0, 5, 6],
                                                                [1, 3, 5], [1, 4, 6], [2, 3, 6],
                                                                [2, 4, 5]], ""))
    r = sb.evaluate_program(FANO_PROG, 7, 4, 3)
    assert r["valid"] is True and r["fitness"] == 7 and r["size"] == 7
    assert r["best_known"] == 7 and r["beats_record"] is False


def test_evaluator_gives_invalid_output_zero_fitness(monkeypatch):
    # sandbox returns a distance-2 (invalid) code -> verify_cwc rejects -> fitness 0, not trusted
    monkeypatch.setattr(sb, "run_program",
                        lambda *a, **k: sb.SandboxResult(True, [[0, 1, 2], [0, 1, 3]], ""))
    r = sb.evaluate_program("x", 7, 4, 3)
    assert r["valid"] is False and r["fitness"] == 0 and r["beats_record"] is False


def test_evaluator_handles_sandbox_failure(monkeypatch):
    monkeypatch.setattr(sb, "run_program",
                        lambda *a, **k: sb.SandboxResult(False, None, "timeout after 20s"))
    r = sb.evaluate_program("x", 7, 4, 3)
    assert r["sandbox_ok"] is False and r["fitness"] == 0 and "timeout" in r["sandbox_error"]


def test_run_program_clean_error_when_docker_missing(monkeypatch):
    def _boom(*a, **k):
        raise FileNotFoundError("no docker")
    monkeypatch.setattr(sb.subprocess, "Popen", _boom)   # run_program now uses Popen
    r = sb.run_program("def construct(n,d,w): return []", 7, 4, 3)
    assert r.ok is False and "docker unavailable" in r.error


# --- docker-gated integration: the container ACTUALLY isolates -----------------------------------
def _skip_if_no_docker():
    import pytest
    if not sb.available():
        pytest.skip("docker / python:3.12-slim sandbox image not available")


def test_sandbox_runs_a_benign_program():
    _skip_if_no_docker()
    r = sb.run_program(FANO_PROG, 7, 4, 3, timeout_s=30)
    assert r.ok is True
    assert {frozenset(c) for c in r.code} == {frozenset(c) for c in
            [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]]}


def test_sandbox_blocks_network():
    _skip_if_no_docker()
    prog = ("def construct(n, d, w):\n"
            "    import urllib.request\n"
            "    urllib.request.urlopen('http://example.com', timeout=3)\n"
            "    return []\n")
    r = sb.run_program(prog, 7, 4, 3, timeout_s=30)
    assert r.ok is False                                # network is --network none => construct raises


def test_sandbox_kills_infinite_loop():
    _skip_if_no_docker()
    prog = "def construct(n, d, w):\n    while True:\n        pass\n"
    r = sb.run_program(prog, 7, 4, 3, timeout_s=8)
    assert r.ok is False                                # SIGALRM in-container and/or host timeout


def test_sandbox_bounds_stdout_flood():
    # the headline DoS fix: a program printing in an infinite loop must NOT OOM the host
    _skip_if_no_docker()
    prog = ("def construct(n, d, w):\n"
            "    import sys\n"
            "    while True:\n"
            "        sys.stdout.write('x' * 1000000)\n")
    r = sb.run_program(prog, 7, 4, 3, timeout_s=20)
    assert r.ok is False
    assert ("output exceeded" in r.error) or ("timeout" in r.error)   # bounded, never a host crash


def test_sandbox_read_only_root_blocks_writes():
    _skip_if_no_docker()
    prog = ("def construct(n, d, w):\n"
            "    open('/evil', 'w').write('x')\n"        # root FS is --read-only => OSError
            "    return []\n")
    r = sb.run_program(prog, 7, 4, 3, timeout_s=30)
    assert r.ok is False


def test_sandbox_container_reaped_after_host_timeout():
    # program disarms the in-container alarm and busy-loops => the HOST deadline must fire AND the
    # named container must be force-removed (not orphaned).
    _skip_if_no_docker()
    import subprocess as _sp
    prog = ("def construct(n, d, w):\n"
            "    import signal\n"
            "    signal.signal(signal.SIGALRM, signal.SIG_IGN)\n"
            "    while True:\n"
            "        pass\n")
    r = sb.run_program(prog, 7, 4, 3, timeout_s=6)
    assert r.ok is False and "timeout" in r.error
    ps = _sp.run(["docker", "ps", "-aq", "--filter", "name=leibniz-fs-"],
                 capture_output=True, text=True, timeout=15)
    assert ps.stdout.strip() == "", f"orphaned sandbox containers: {ps.stdout!r}"


def test_sandbox_non_iterable_return_is_clean_error():
    _skip_if_no_docker()
    r = sb.run_program("def construct(n, d, w):\n    return 5\n", 7, 4, 3, timeout_s=20)
    assert r.ok is False                                # harness catches the TypeError, never raises
