# Current implementation review — 2026-10-30

Scope: reader, pipeline, checks, source verification, Parquet/CSV output, SQL generation, loader/probe, example joins and existing tests. Reviewed while source download and other implementation edits were ongoing. Final spot-checks distinguish open issues from changes made during the review.

Verdict: changes requested before using the linkage queries or relying on repeat builds. Three reproduced issues remain. The existing synthetic suite passes.

## 1. [P1] Partition dated joins by cohort record, not person ID

Locations: docs/sql/join_by_uprn.sql:23–37 and the final join on pseudo_id; docs/sql/join_by_postcode.sql:28 and its aggregation/final join.

The dated queries partition and aggregate solely by pseudo_id (plus dwelling for postcode linkage). The documented cohort shape does not require pseudo_id to be unique. A longitudinal cohort can have multiple records per person, at different dates or addresses. Eligible certificates from those records are pooled, and the selected result is then attached to every record for that person. This can assign a future certificate to an earlier observation or report false ambiguity from repeated eligible rows.

Reproduced using the existing tests/test_joins.py fixture and its DuckDB adaptation of join_by_uprn.sql:

- Input: pseudo_id 1, UPRN 35000001, dates 2015-06-01 and 2024-01-01.
- Actual: both records are matched to the certificate lodged 2020-06-01.
- Expected: the first record matches 2015-06-01; the second matches 2020-06-01.

Carry a unique cohort_row_id through every partition, grouping and join, retaining pseudo_id as a person identifier. Alternatively explicitly require and enforce a unique record key before execution; silently assuming uniqueness is unsafe.

Regression tests: repeated person ID at different dates; repeated person ID with different UPRNs/postcodes; duplicate observations. Each record must retain its own eligible certificate set. Apply the fix to both dated routes.

## 2. [P2] Allow an entirely NULL optional string column in an annual file

Location: epc_ingest/reader.py:173–179.

The width check evaluates int(series.str.len().max()). When every value of a nullable string column is missing, max() is pd.NA, and int(pd.NA) raises TypeError. Missing RRN, postcode and data-zone codes are supported by the schema; a file containing only missing values for one such derived column should not crash.

Reproduced with default_rows(2008), setting REPORT_REFERENCE_NUMBER to the empty string in all five rows, and building an otherwise valid synthetic release. The exception occurs at reader.py:177:

    TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NAType'

Treat an all-null length reduction as zero (or skip width comparison when no non-null values exist), while retaining the separate required-value checks.

Regression tests: entire annual rrn column missing, entire pc_norm missing, and an entire data-zone code column missing or malformed under its documented non-blocking policy. A separate all-missing numeric uprn_osg synthetic build passed during this review.

## 3. [P2] Publish outputs only after the whole build validates

Locations: epc_ingest/pipeline.py:65–90 and the later read-back/table checks; epc_ingest/core/text_output.py CsvWriter.__init__; epc_ingest/core/output.py ParquetWriter.close.

The CSV opens its final path in write mode before validation. Parquet replaces its final path when the writer closes, before read-back and whole-table checks. The old manifest and BUILD_REPORT remain until the new build succeeds. A failed rerun therefore destroys a previously accepted output and leaves old success metadata beside rejected or incomplete data.

Reproduced entirely in a temporary directory:

1. Build a valid synthetic release.
2. Build a second pinned synthetic release to the same results directory, containing S01999999 (Nowhere), which fails the whole-table unknown-zone check.
3. The old manifest remains unchanged, but the Parquet SHA256 no longer matches it.

Observed output:

    old_manifest_remains True
    parquet_still_matches_manifest False

Write each build into a separate staging directory, close writers reliably on failure, and promote the complete set only after read-back and blocking checks pass. Preserve the last accepted build on failure and ensure incomplete output cannot look like an accepted release.

Regression test: successful build followed by a late failing build; every accepted artifact and its manifest must remain consistent. Also exercise a reader failure after one annual part has already been written.

## Issues resolved concurrently during review

These are not open findings against the latest inspected files:

- SQL datetime2 metadata initially expected precision 0 and scale 0. A read-only SQL Server query confirmed precision 19 and scale 0 for datetime2(0). The generator, generated check and test expectation were updated to 19/0 during review.
- The probe initially compared predicates with <>. A minimal read-only query reproduced SQL Server error 102 near '<'. The current probe replaces the invalid comparison with CASE-based scalar comparison.

The SQL Server checks were limited to SELECT statements against an existing local container; no EPC tables were loaded or modified. Supporting references: [Microsoft datetime2 metadata documentation](https://learn.microsoft.com/en-us/sql/t-sql/data-types/datetime2-transact-sql) and [Microsoft comparison/Boolean expression documentation](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/comparison-operators-transact-sql).

## Validation performed

- Existing suite: 33 passed in 5.16 seconds on the final rerun.
- Interpreter: /opt/homebrew/Caskroom/miniforge/base/bin/python3, Python 3.12; pytest 9.1.1, pandas 3.0.3, pyarrow 24.0.0 and DuckDB 1.5.5.
- Command: python -m pytest -q -p no:cacheprovider, using that interpreter.
- Focused reproductions: longitudinal join, all-missing RRN, failed rebuild preserving stale manifest; all described above.
- Read-only SQL metadata and syntax checks; reviewed revised SQL files after concurrent edits.
- No source download files or download processes were altered. No implementation fixes were made by this review.

## Remaining validation limits

No full-data build, source reprofiling, full generated SQL import/check run or full container probe was performed in this review. Annual-file memory use and SQL runtime remain unmeasured. The reader materializes a whole annual CSV with list(reader), and CSV writing creates whole-year text/bytes, so a successful tiny fixture does not establish the full build's memory requirements.

The join tests execute adapted SQL in DuckDB, and SQL-generation tests chiefly inspect strings. Their passing result is useful but does not establish SQL Server end-to-end correctness. The updated Linux probe also transcodes to UTF-16LE, so it does not validate the Windows UTF-8 BULK INSERT path. These are validation limits, not additional reproduced defects.

Earlier reviews and responses are preserved.
