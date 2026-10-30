# Response to the loading notebook follow-up review, 30 October 2026

Review: `2026-10-30-loading-notebook-follow-up-review.md`. One finding, confirmed and fixed.

## P2: the probe could fail without saying so

Both layers were as described. The harness recorded `ok: false` and returned normally; the
runner piped `docker run` into `grep`, so under `set -e` the pipeline's status was grep's and a
crashing container exited the runner with 0.

Fixes:

- `loader/notebook_probe/harness.py`: after teardown, `main` exits 1 unless exactly eleven
  scenarios were recorded and every one is ok, printing which failed. The constant `SCENARIOS`
  names the count so a scenario that never ran is a failure too.
- `loader/notebook_probe.sh`: the container's output goes to `out/harness.log`, its exit status
  is kept and the runner exits with it; the warning filter runs on the log afterwards. The runner
  then reads `results.json` itself and fails unless it holds eleven scenarios, all ok, so a
  harness that exited 0 with a bad record is still caught.

Tests, `tests/test_notebook_probe_exit.py`, five cases, none needing a server or Docker:

- the harness with its database and notebook helpers stubbed exits 1 when one scenario fails,
  naming it; exits 1 when a scenario is missing; returns normally with eleven passing;
- the runner with a fake `docker` on the path exits 7 and shows the error when the harness
  container prints a traceback and exits 7 (the fake lets `docker run -d`, the server start,
  succeed, and fails only the harness run);
- the runner fails when the container exits 0 but `results.json` records a failed scenario.

The real probe was rerun with the fixed runner and reports every scenario as expected with exit
status 0; the record in `docs/sql/NOTEBOOK_PROBE_2026-10-30.md` is unchanged in substance.

## Not covered by the fixing tests

An expected-failure scenario that fails at the intended step for a different reason than the
one intended passes if its `expect_error` text still matches; the texts are specific enough that
no live case is known, but the harness does not compare tracebacks. The fake docker tests
exercise the runner's control flow, not Docker itself. My findings are closed.
