# Implementation follow-up review — 2026-10-30

Scope: fixes responding to 2026-10-30-current-implementation-review.md, related tests and current build manifest.

Verdict: the three original reproduction cases now pass. Two remaining edge cases in the fixes need correction.

## 1. [P2] Promotion can still leave mixed generations of outputs

Location: epc_ingest/pipeline.py:51–58.

Staging protects the accepted build from reader and validation failures, but promotion replaces four files individually. If a later replacement fails after Parquet has been replaced, the exception handler deletes the remaining staging directory and leaves new Parquet beside the previous CSV, manifest and report. This can occur with a destination permission/file-lock error, and interruption between replacements has the same consistency problem.

Reproduced in a temporary directory: build an accepted release, build a valid changed release, and inject PermissionError only when os.replace targets the final CSV. Parquet promotion succeeds first. Results:

    simulated locked destination CSV
    old_manifest_remains True
    parquet_matches_manifest False
    staging_remaining 0

Use immutable build directories and publish a single atomic pointer to the accepted generation, with consumers resolving that generation consistently. Alternatively implement recoverable promotion with retained backups and rollback for file-operation failures, documenting any remaining interruption window. Do not discard recovery material after partial promotion.

Add a regression that fails the second or third promotion operation and verifies the accepted generation remains consistent or recoverable. The current early/late validation-failure tests are useful but do not exercise publication failure.

## 2. [P2] Reject NULL cohort record keys before dated linkage

Locations: docs/sql/join_by_uprn.sql:20–21; equivalent guard and record-key joins in docs/sql/join_by_postcode.sql.

The new uniqueness guard rejects duplicates but permits one NULL cohort_row_id. The documented cohort columns are not declared NOT NULL. That record enters the ranking/aggregation, but its result cannot join back through equality on NULL, so a valid match silently becomes no_certificate_by_date.

Reproduced with the existing join fixture and DuckDB dialect adapter:

    input: (cohort_row_id=NULL, pseudo_id=7, uprn='35000001', cohort_date=2024-01-01)
    output: (NULL, 'no_certificate_by_date', NULL)

The fixture has an eligible 2020 certificate. The duplicate-count guard would not reject this one-row cohort. The postcode route has the same equality-join problem.

Require a non-null unique cohort_row_id, preferably via a NOT NULL primary key in the input contract and an explicit NULL guard in the query. Update the example/probe DDL. Test a single NULL key and duplicate keys against the actual T-SQL guard; the DuckDB shim currently removes that guard after checking its presence.

## Fixes verified

- Repeated person IDs at different dates/addresses are isolated by cohort_row_id; the new longitudinal regression passes. Postcode tests also repeat a person across observations.
- Entirely missing nullable text columns no longer crash the width reduction; RRN, postcode and 2011 data-zone coverage is included in the passing test.
- Failed source/reader/whole-table validation leaves the previous accepted files unchanged, and writer abort methods were added. The remaining limitation is specifically the promotion stage above.

## Validation

- Existing suite rerun with /opt/homebrew/Caskroom/miniforge/base/bin/python3 -m pytest -q -p no:cacheprovider: **36 passed in 7.47 seconds**.
- Focused NULL-key reproduction used the existing DuckDB fixture.
- Promotion-failure reproduction used temporary synthetic sources/outputs and unittest.mock fault injection; production outputs were untouched.
- Read results/manifest.json: it reports release 2026Q2, 3,787,069 rows, build time 2026-10-30T08:56:31.688866+00:00, and 297 blocking checks passed with zero failed. This is recorded build evidence, not an independently rerun full build or rehash.
- No full SQL Server import/probe was rerun in this follow-up. Prior Windows UTF-8-path and memory-measurement limitations remain.
- No implementation or source data was changed. Earlier reviews are preserved.
