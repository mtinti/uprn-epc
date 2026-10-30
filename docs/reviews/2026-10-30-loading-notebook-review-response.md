# Response to the loading notebook review, 30 October 2026

Review: `2026-10-30-loading-notebook-review.md`. One defect reported, fixed. The validation
the review asked for was run and found a second, worse defect, also fixed. Probe record:
`docs/sql/NOTEBOOK_PROBE_2026-10-30.md`.

## 1. The twice-assessed dwelling selector (P2)

Confirmed. `MIN(uprn_osg) ... GROUP BY uprn_osg` returns one row per qualifying UPRN, and the
real table has hundreds of thousands of them, so the step 6 example would have failed on the
first real run. The generator now uses `SELECT TOP (1) uprn_osg ... GROUP BY uprn_osg HAVING
COUNT(*) = 2 ORDER BY uprn_osg`; with no qualifying dwelling the subquery is NULL and only the
2024 row shows, which the step's text now says.

Regression tests in `tests/test_notebook.py` take the two queries out of the generated notebook
and run them in DuckDB: two dwellings with two certificates each, beside one with three and one
with one, return the 2024 row and the two certificates of the lowest qualifying UPRN; with no
qualifying dwelling, the 2024 row alone. A third test keeps the old form and asserts that DuckDB
rejects it with two qualifying dwellings, as SQL Server does.

## 2. The pyodbc path, run for real

The review's validation gap was real, and running the notebook's cells against SQL Server found
a defect the parsing tests could not: the first full run never finished. pyodbc pools
connections, the SQL Server ODBC driver opens an implicit transaction on any statement under
`autocommit=False`, and a pooled connection comes back with that transaction open. Step 4's
`autocommit=True` connection was given step 1's session, its two `CREATE INDEX` statements ran
inside step 1's transaction and never committed, and step 5 waited on the schema locks without
a timeout. The probe record gives the lock evidence and the reproduction.

Fixes, each asserted by a new test on the generated notebook: pooling off before the first
connection; every read-only connection in autocommit; step 3's DDL in an explicit transaction
closed before its display queries; step 4's loading connection closed before the indexes;
`SET LOCK_TIMEOUT` in steps 3, 4 and 5.

`loader/notebook_probe.sh` is now part of the repository: a Dockerfile for the client side, a
15-row fixture with every case the review listed (empty published strings beside NULL derived
values; accents, a no-break space, curly quotes and a euro sign; an embedded newline and a
double quote; every wide column one short of its width and a 7,998-character pair; decimals at
the 4-decimal edge; a 2108 date, a midnight timestamp, both flag values; a padded and a 12-digit
UPRN), and a harness that runs the notebook's cells under eleven scenarios, including a batch
the server rejects and four kinds of tampering with the loaded table. Every scenario behaves as
expected; 375 cells read back through pyodbc equal the CSV text.

## 3. Load behaviour

Kept explicit: the notebook's opening text now says that steps 3 to 5 are not all-or-nothing,
that a failure leaves an incomplete or unverified table to be reloaded from step 3, and that a
refresh of a table in use should load under a new `TABLE` name and rename after step 5 passes.
Scenario 08 of the probe records the behaviour: a rejected batch leaves the chunks committed
before it.

## 4. Runtime and memory

Measured, by running the real notebook on the full table against the throwaway server from the
client container: 399 seconds for the rows at about 9,500 rows a second, 37 seconds for the two
indexes, 25 seconds for the digest, every check passing, 20.6 GB of table. The notebook's opening
text now gives these numbers instead of "an hour or more", keeping the hour as the upper bound
for a load over the HIC network. Peak memory of step 4's code path on real rows was 785 MB.

## Standing limits

The probe runs on Linux containers on one machine; the HIC server's network and the Windows
ODBC driver are untested. The datazone-ahah notebook has the same pooled-connection pattern
and has not been changed. My findings are closed.
