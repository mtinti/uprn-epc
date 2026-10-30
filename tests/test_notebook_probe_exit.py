"""The notebook probe must fail loudly: the harness exits nonzero when a scenario fails or is
missing, and the shell runner keeps the container's exit status instead of grep's (review of
30 October 2026). The harness is imported with pyodbc and nbclient stubbed and its database and
notebook helpers replaced, so no server is needed; the runner is run with a fake docker."""

import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "loader" / "notebook_probe"


@pytest.fixture
def harness(monkeypatch, tmp_path):
    for name in ("pyodbc", "nbclient", "nbclient.exceptions"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules["nbclient"].NotebookClient = object
    sys.modules["nbclient.exceptions"].CellExecutionError = Exception
    monkeypatch.setenv("SA_PW", "stub")
    monkeypatch.syspath_prepend(str(PROBE))
    sys.modules.pop("harness", None)
    import harness
    monkeypatch.setattr(harness, "OUT", tmp_path)
    monkeypatch.setattr(harness, "RUNS", tmp_path / "runs")
    for fn in ("setup", "teardown"):
        monkeypatch.setattr(harness, fn, lambda: None)
    monkeypatch.setattr(harness, "q", lambda sql, db=None: [(0, 0)])
    monkeypatch.setattr(harness, "folder", lambda name, mutate=None: tmp_path / name)
    harness.RESULTS.clear()
    return harness


def _stub_run(harness, outcome):
    def run(name, path, **kwargs):
        result = {"test": name, "ok": outcome(name)}
        harness.RESULTS.append(result)
        return result
    harness.run = run


def test_harness_exits_nonzero_when_one_scenario_fails(harness, capsys):
    _stub_run(harness, lambda name: not name.startswith("05"))
    with pytest.raises(SystemExit) as stop:
        harness.main()
    assert stop.value.code == 1
    assert "FAILED: ['05_null_made_empty_caught_by_digest']" in capsys.readouterr().out


def test_harness_exits_nonzero_when_a_scenario_is_missing(harness):
    _stub_run(harness, lambda name: True)
    harness.SCENARIOS = 12
    with pytest.raises(SystemExit):
        harness.main()


def test_harness_returns_normally_when_every_scenario_passes(harness, capsys):
    _stub_run(harness, lambda name: True)
    assert harness.main() is None
    assert len(harness.RESULTS) == harness.SCENARIOS == 11
    assert "SUMMARY 11 of 11" in capsys.readouterr().out


def test_runner_fails_when_the_container_fails(tmp_path):
    """A fake docker: every subcommand succeeds silently except `run`, which prints an error
    and exits 7, as a crashing harness container would. The runner must exit nonzero and show
    the error."""
    fake = tmp_path / "bin"
    fake.mkdir()
    docker = fake / "docker"
    # `docker run -d` starts the server and must succeed; `docker run --rm` is the harness.
    docker.write_text('#!/bin/sh\ncase "$1 $2" in\n  "run --rm") echo "Traceback: the harness crashed"; exit 7;;\n  *) exit 0;;\nesac\n')
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}")
    done = subprocess.run(["sh", str(ROOT / "loader" / "notebook_probe.sh"), str(tmp_path / "scratch")],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert done.returncode == 7, done.stdout + done.stderr
    assert "the harness crashed" in done.stdout and "FAILED" in done.stdout
    assert not (tmp_path / "scratch" / "out" / "results.json").exists()


def test_runner_fails_when_results_say_a_scenario_failed(tmp_path):
    """The container exits 0 but results.json records a failure: the runner's own check fails."""
    fake = tmp_path / "bin"
    fake.mkdir()
    scratch = tmp_path / "scratch"
    results = json.dumps([{"test": f"{i:02d}", "ok": i != 4} for i in range(1, 12)])
    docker = fake / "docker"
    docker.write_text(f'#!/bin/sh\ncase "$1 $2" in\n  "run --rm") printf %s \'{results}\' > "{scratch}/out/results.json"; exit 0;;\n  *) exit 0;;\nesac\n')
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}")
    done = subprocess.run(["sh", str(ROOT / "loader" / "notebook_probe.sh"), str(scratch)],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert done.returncode != 0 and "failed: ['04']" in done.stderr
