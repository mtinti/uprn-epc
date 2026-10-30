# Latest notebook and probe changes review — 2026-10-30

Scope: loading notebook and generator, notebook probe runner/harness/fixture, related tests, inspection-date linkage changes and saved probe evidence.

Verdict: the prior notebook query defect is fixed and the pyodbc validation gap has substantial recorded coverage. One P2 issue remains in how the new probe signals failure.

## [P2] Make failed probe scenarios and container failures return a nonzero status

Locations: loader/notebook_probe/harness.py:219–230; loader/notebook_probe.sh:30–33.

There are two layers of failure masking:

1. The harness records ok=false for a failed scenario, continues, prints its summary and returns normally. It does not raise or exit nonzero when one or more scenarios fail.
2. The shell runner pipes docker run through grep under /bin/sh with set -eu. The pipeline returns grep's status. A failing container that prints any non-filtered error line therefore makes the shell command succeed.

This makes the documented validation command report success to a caller or CI even when notebook validation fails. Correcting only the Python exit status is insufficient because the shell pipeline can still mask it.

Reproductions, without running Docker or touching database tables:

- Executed the harness's actual main function with its database/scenario helpers stubbed, recording ok=false for each scenario. It printed SUMMARY 0 of 11 tests as expected and returned None normally.
- Executed the same shell pipeline pattern with a producer that prints an error and exits 7. The complete command exited 0.

After all scenarios and cleanup, raise or exit nonzero unless every expected scenario completed and passed. Preserve the Docker exit code in the shell wrapper, for example by capturing output before filtering it, or using an explicitly selected shell with pipefail and suitable handling of grep's own exit status.

Add tests that make one scenario fail and one container process exit nonzero, and assert that the public probe command fails in both cases. Keep expected-failure scenarios passing only when they fail at the intended step with the intended evidence.

## Prior review findings and improvements verified

- Step 6 now selects one qualifying UPRN with TOP (1) and ORDER BY. Tests exercise several qualifying dwellings, no qualifying dwelling and the rejected old scalar-subquery form.
- Notebook connection handling now disables pooling before connection creation, uses autocommit for read operations, closes the loading connection before creating indexes, and bounds lock waits in DDL/index/digest operations.
- Replacement behavior is explicitly documented: the notebook commits chunks and requires a new target table for a safe refresh of an accepted table.
- Inspection-date selection is an explicit new decision in epc_ingest/decisions.yaml and the plan. Updated join tests exercise inspection before cohort date with lodgement afterward, longitudinal records, tie handling and the lodged-before-inspection flag.

## Validation and evidence

- Full Python suite: **44 passed in 11.00 seconds**.
- Command: /opt/homebrew/Caskroom/miniforge/base/bin/python3 -m pytest -q -p no:cacheprovider.
- Read results/.notebook_probe/out/results.json: **11 scenarios, all ok=true**. The saved full-run notebook contains the current inspection-date ranking.
- Read docs/sql/NOTEBOOK_PROBE_2026-10-30.md and inspected the fixture and harness. The fixture covers Unicode, empty versus NULL, wide rows, dates, flags, large UPRNs and decimals; scenarios exercise tampering and partial-batch failure.
- The probe record reports a full 3,787,069-row notebook upload and digest verification. Those timing/full-run claims were reviewed as recorded evidence, not independently rerun during this review.
- Reproduced both exit-status defects with isolated in-memory helper stubs and a harmless shell pipeline.
- No implementation, source data, notebook or database table was modified. Prior reviews are preserved.

## Remaining limits

The passing probe evidence is for a Linux container client and local SQL Server. It does not establish behavior or performance on the HIC Windows client/network. The notebook's full production upload was not executed by this review. The failure-signaling defect does not invalidate the inspected all-passing JSON results; it makes future failures easy to overlook.
