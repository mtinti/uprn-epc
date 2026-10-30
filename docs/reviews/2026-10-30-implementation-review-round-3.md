# Implementation review, round 3 — 2026-10-30

Scope: the two findings in 2026-10-30-implementation-follow-up-review.md, their fixes and regression tests.

Verdict: both prior findings are addressed. No new blocking defect found in this focused follow-up.

## Findings closed

### Promotion failure preserves or retains recoverable accepted outputs

pipeline.promote now moves accepted files into a .previous directory before replacing them. An exception triggers rollback; if rollback fails, the backup is retained and identified by the raised error.

The new regression covers a transient destination-CSV failure, a persistent failure during rollback, and a subsequent successful promotion. Together with the earlier reader/validation-failure tests, this addresses the previous reproduction where Parquet was replaced and the old manifest left without recovery material.

This is recoverable publication, not an atomic generation switch. A hard interruption between renames can still leave partial results requiring manual recovery, as the implementation docstring acknowledges. Do not treat results as concurrently readable during promotion.

Small documentation correction: the response and test comment say the .previous folder remains “whole” when rollback fails. Earlier files may already have been restored into results before a later restore fails. In that case the accepted generation is recoverable across results and .previous, not necessarily contained wholly in .previous. Recovery instructions should preserve both locations.

### NULL cohort keys are rejected

All three join queries now explicitly reject NULL cohort_row_id before the duplicate-key guard. Their input contracts declare cohort_row_id int NOT NULL PRIMARY KEY. This prevents the prior case in which a single NULL key silently returned no_certificate_by_date despite an eligible certificate.

The regression checks the guard and input contract in every query. The SQL Server probe now includes invalid-cohort cases for the UPRN query; the DuckDB tests still remove the T-SQL guards and therefore do not execute them.

## Validation

- Reran the suite using /opt/homebrew/Caskroom/miniforge/base/bin/python3 -m pytest -q -p no:cacheprovider.
- **38 tests passed in 9.51 seconds**, including promotion rollback and cohort-key contract regressions.
- Inspected pipeline.promote, query guards, test changes, probe changes and the review response.
- Read docs/sql/SQLSERVER_PROBE_2026-10-30.md. It records the full-data load/digest and earlier join results, but does not yet record the newly added NULL/duplicate cohort-key probe outcomes claimed by the response. Add those outcomes for a complete audit trail; this review does not independently confirm that rerun.
- No full source build, full SQL import or container probe was rerun in this follow-up. Windows UTF-8 import validation and full-build memory measurement remain outside the checks performed here.
- No implementation or source data was changed; earlier reviews are preserved.
