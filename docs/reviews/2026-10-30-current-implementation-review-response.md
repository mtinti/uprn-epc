# Response to the implementation review of 30 October 2026

Review: `2026-10-30-current-implementation-review.md`. All three findings reproduce as
described and are fixed the same day. Each fix carries a test that fails on the code before it.

| # | Finding | Holds | Change |
| --- | --- | --- | --- |
| 1 | The dated joins partition by `pseudo_id`, so a person with several cohort rows has the rows pooled and every row gets the same certificate | yes | The cohort table now carries a unique `cohort_row_id` beside `pseudo_id`. Every partition, grouping and final join in the three queries is by `cohort_row_id`; `pseudo_id` is returned as the person identifier. Each query starts with a guard that throws if `cohort_row_id` repeats, so uniqueness is enforced, not assumed. The probe's cohort table and the onward sketch follow. Test added (`test_one_person_many_rows_each_row_gets_its_own_certificate`): one person at 2015 and 2024 gets the 2015 and the 2020 certificate respectively; a duplicate observation matches on its own; the same person at another address gets that address's certificate; a real same-day tie stays `ambiguous_as_of`. The DuckDB shim asserts the guard is present before removing it. |
| 2 | The width check raises `TypeError` when a nullable text column is missing in every row of a file | yes | `reader.py`: an all-missing length maximum counts as zero. Test added: a file with every RRN, postcode and 2011 data zone empty builds, and the derived columns are all NULL with status `empty`. |
| 3 | The CSV and the Parquet are written to their final paths before the read-back and whole-table checks, so a failed rebuild destroys the accepted build and leaves a stale manifest beside it | yes | The build writes into `results/.staging_<time>_<pid>/`, and only after every check has passed are the four outputs moved into `results/`. On any failure the staging folder is removed and both writers close and delete their part files. Test added: a good build, then a build that fails the whole-table unknown-zone check, then one that fails in the reader on the second file; after each failure the four accepted files are byte for byte what they were and the manifest's Parquet hash still matches. |

Validation limits the review names and this response does not remove: the join SQL is tested
in DuckDB through a dialect shim and against SQL Server by the container probe, which on Linux
imports a UTF-16 copy rather than the Windows UTF-8 path; the reader holds one annual file in
memory at a time (the largest, 2014, took 64 seconds in the full build; memory was not
measured). The full build was rerun after the fixes and gave the same CSV hash and digest as
before, which is expected: none of the three fixes changes a value.
