# Response to the implementation follow-up review of 30 October 2026

Review: `2026-10-30-implementation-follow-up-review.md`. Both findings reproduce as described
and are fixed the same day, each with a test that fails on the code before it.

| # | Finding | Holds | Change |
| --- | --- | --- | --- |
| 1 | Promotion replaces the four outputs one by one, so a failure after the first leaves mixed generations and deletes the staging folder | yes | `pipeline.promote` now moves the accepted files aside into a `.previous_<stamp>` folder, then moves the new files in. If any move fails, every move is undone and `results/` holds the accepted build again. If the rollback itself fails, the `.previous` folder is kept whole and the error names it, so nothing accepted is ever lost. Each step is a rename on one filesystem. Test added: a lock on the final CSV that clears (rollback leaves the four files byte for byte as before, nothing left over), a lock that persists (`RuntimeError` names the folder, which holds the accepted CSV and manifest intact), then the same build promoting cleanly as one generation. The remaining window is an interruption between renames, which leaves `.previous` beside a partial `results/` and never a deleted file; the docstring says so. |
| 2 | The uniqueness guard admits one NULL `cohort_row_id`, whose match then cannot join back and reads as `no_certificate_by_date` | yes | Each query now has two guards: NULL key, then repeated key, each a `THROW`. The cohort contract in every query header is `cohort_row_id int NOT NULL PRIMARY KEY`. The DuckDB test asserts both guards and the contract are present in all three files before stripping the guards. The container probe exercises the T-SQL guards themselves: a cohort with a NULL key and one with a repeated key must each stop with the guard's message. |

Validation: 38 tests pass. The container probe was rerun after the change to exercise the
guards in SQL Server; its result is in `docs/sql/SQLSERVER_PROBE_2026-10-30.md`.
