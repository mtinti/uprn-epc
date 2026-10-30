# Response to the notebook probe review, round 3, 30 October 2026

Review: `2026-10-30-notebook-probe-review-round-3.md`. The P2 of the previous round is confirmed
resolved. One minor finding, fixed.

## Test portability

Confirmed. The two shell-runner tests ran `loader/notebook_probe.sh`, whose `python3` was
whichever came first on PATH, not the interpreter running pytest. With Homebrew Python first,
the fixture generator failed on `import yaml` before the intended case.

Fix in `tests/test_notebook_probe_exit.py`: the directory of `sys.executable` is placed on the
subprocess PATH after the fake docker directory, so the runner's `python3` is the test's own
interpreter. The runner itself is unchanged: on a machine it keeps using the project environment,
as `docs/UPDATING.md` says.

Reproduced the review's set-up by running the full suite with Homebrew Python first on PATH and
the project interpreter invoking pytest: 49 passed. The fake-docker tests do not cover a machine
whose project interpreter has no `python3` beside it (a bare `python` name), which is not the case
in a conda or venv environment. My findings are closed.
