# Notebook probe review, round 3 — 2026-10-30

Scope: the failure-signaling fix from 2026-10-30-loading-notebook-follow-up-review.md and its new regression tests.

Verdict: the previous P2 finding is resolved. No new blocking issue found in this focused review.

## Verified fix

- The Python harness now exits 1 if any scenario fails or if the recorded count differs from SCENARIOS.
- The shell runner captures the container's exit status before filtering its output and returns that status on failure.
- After a successful container exit, the runner independently checks results.json for eleven passing scenarios.
- Regression tests cover a failing scenario, missing scenario, all-passing harness, container exit 7, and container exit 0 with a failing results record.

These tests exercise the public shell runner with a fake Docker executable and the real harness control flow with database/notebook helpers stubbed. They address both failure-masking layers identified in the previous review.

## Minor test portability issue

Locations: tests/test_notebook_probe_exit.py, PATH construction in the two shell-runner tests; loader/notebook_probe.sh, python3 invocations.

Running pytest through an explicit interpreter path does not ensure that shell subprocesses use the same interpreter. The initial run used Miniforge Python for pytest but Homebrew Python for the runner's fixture generation, which failed importing yaml before reaching the intended test cases.

Consider putting Path(sys.executable).parent on the test subprocess PATH after the fake Docker directory, or passing an explicit Python executable into the runner. The documented requirement to use the project Python environment is sufficient operationally; this is test portability, not an unresolved failure-signaling defect.

## Validation

- Initial full suite: **47 passed, 2 failed in 11.74 seconds**. Both failures were the new shell-runner tests, stopped by ModuleNotFoundError: No module named 'yaml' in the other Python environment.
- Reran tests/test_notebook_probe_exit.py with /opt/homebrew/Caskroom/miniforge/base/bin first on PATH: **5 passed in 3.65 seconds**, including both previously failing tests.
- Together these runs cover all 49 tests; a fresh full-suite run under the adjusted PATH was not repeated.
- Inspected saved results/.notebook_probe/out/results.json: eleven scenarios, all passing; harness.log exists.
- No live Docker probe or database load was rerun. Previously recorded Linux probe results remain evidence from the earlier run; Windows/HIC validation remains outside this review.
- No code, source data or database contents were modified. Earlier reviews are preserved.
