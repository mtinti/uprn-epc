# SQL Server probe, 30 October 2026

`loader/sqlserver_probe.sh` against a throwaway SQL Server 2022 container (Developer edition,
linux/amd64 under emulation on an Apple Silicon Mac, 6 GB memory limit), with the full build of
release 2026Q2: 3,787,069 rows by 127 columns.

## Three runs

1. **First run: structure and digest failed.** The structure check reported one difference:
   the generator declared `datetime2(0)` with precision 0, and `sys.columns` reports 19. The
   digest differed in every year. Hashing each column's rendering for three rows found one
   column, `IMPROVEMENTS`, and the bytes showed why: the file's non-breaking spaces (UTF-8
   `C2 A0`) had been read in the OEM code page as two characters (`┬á`). A UTF-8 collation on
   the staging columns governs how bytes are stored, not how `BULK INSERT` reads the file.
   Every text cell with a non-ASCII character was wrong. Fixes: `CODEPAGE = '65001'` in the
   generated import; precision 19 in the declared structure.
2. **Second run: `CODEPAGE` is not supported on Linux.** The import stopped at once with
   message 16202. A small experiment showed that a UTF-8 byte order mark does not help, and
   that a UTF-16LE file with a byte order mark imported as `DATAFILETYPE = 'widechar'` with
   `ROWTERMINATOR = '\n'` keeps a non-breaking space and an embedded newline intact. The probe
   now converts the CSV with `iconv` and adapts those two options; the generated script for
   Windows keeps `CODEPAGE = '65001'`.
3. **Third run: every check passed.**

## Timings, third run

| Step | Time |
| --- | --- |
| Import: staging `BULK INSERT` of the UTF-16 file (15 GB), typed insert with the restore expressions, two indexes | 413 s |
| `check_loaded_digest.sql`: structure, key, reserved characters, row count, digest over 3,787,069 rows by 127 columns | 26 s |

The digest over the whole table runs well inside a minute, so it does not need to run per year.

## What passed

- Structure: 127 columns in order with the declared types, widths (`max_length`) and
  nullability. Key unique. No reserved framing character. Row count. Digest total equal to the
  manifest's `-35655847973013680818794`.
- Rendering: SQL Server's text for 44 chosen cells (bigint, date, datetime2, bit, decimal(19,4),
  int, nullable text, empty published text) equals the CSV text byte for byte.
- Empty against NULL, counted against the manifest: `ADDENDUM_TEXT` is the empty string in
  all 3,787,069 rows and NULL in none; `OSG_REFERENCE_NUMBER` is empty and `uprn_osg` NULL in
  the same 178,537 rows; `REPORT_REFERENCE_NUMBER` is empty and `rrn` NULL in the same 340,010;
  the six `BUILDING_REFERENCE_NUMBER` cells with an embedded newline survived; `historic_flag`
  agrees with `HISTORIC` and `total_floor_area_int` with `TOTAL_FLOOR_AREA` in every row.
- The join by UPRN: seven cohort rows (a real UPRN on its lodgement date, the same UPRN padded
  to 12 digits, the same UPRN before any certificate, a UPRN with no certificate, an empty
  UPRN, a NULL and a non-integer) returned once each with `matched`, `matched`,
  `no_certificate_by_date`, `uprn_not_in_epc`, `no_uprn`, `no_uprn`, `no_uprn`.

The one query the third run did not reach as written, the empty-against-NULL count, had a
T-SQL syntax error in the mismatch expression; it was corrected and that step and the join
step were rerun against the loaded table.

## Fourth run, after the implementation reviews

Rerun from a fresh container with the queries revised for the implementation reviews
(`cohort_row_id` per cohort row; NULL and repeated keys rejected). Every step passed in one run:

| Step | Result |
| --- | --- |
| Import (UTF-16 copy, Linux) | 340 s |
| `check_loaded_digest.sql`: structure, key, reserved characters, row count, digest | 25 s, all pass |
| Rendering of 44 chosen cells | equal to the CSV text |
| Empty against NULL counts | every count equals the manifest |
| Join by UPRN, seven cohort rows | one row each, expected statuses |
| Cohort key guards | a cohort with a NULL `cohort_row_id` and one with a repeated `cohort_row_id` each stopped the T-SQL with the guard's own message |

## Fifth run, after the switch to the inspection date

The dated joins choose the certificate by `inspection_date_parsed` rather than
`lodgement_date_parsed` (decision `join-by-inspection-date`), and the two join indexes key on it.
Rerun on the existing container with the regenerated import script: import completed (its time was not captured, the run kept only the tail of the output), digest
26 s, every check passed, 44 cells rendered equal, every empty-against-NULL count equal to the
manifest, the seven cohort rows with the expected statuses, both key guards stopped the query.

## Sixth run: the table with the address lines

After decision `address-lines-loaded` the CSV carries all 130 columns (1,215,960,553 bytes
gzipped, digest total `-17782796129345549661789`). The regenerated import and check scripts
were run on the full file: 3,787,069 rows, every check passing, the digest equal to the
manifest's, the check in 26 s; 44 chosen cells rendered equal to the CSV text; every empty and
NULL count equal to the manifest (`uprn_osg` NULL 178,537, `rrn` NULL 340,010, six
`BUILDING_REFERENCE_NUMBER` cells with a newline); the seven join statuses and both key guards
as expected.

## Seventh run: the tie rule in `join_by_uprn.sql`

After decision `tie-prefers-current-then-latest-lodged` (31 October 2026) the dated joins rank a
same-day pair by the current flag and then the register timestamp, with three window functions.
The full table was loaded and checked again (digest equal, 26 s; 44 cells rendered equal; every
empty and NULL count equal to the manifest) and the join step ran the revised T-SQL from
`docs/sql/join_by_uprn.sql` against it: seven cohort rows returned once each with the expected
status, both key guards stopped the query. The probe's cohort has no tie, so the rule's choices
are shown by the DuckDB tests in `tests/test_joins.py` (one current of two; both superseded with
different timestamps; identical timestamps left ambiguous) and the T-SQL by this run.
