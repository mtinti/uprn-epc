# Notebook probe, 30 October 2026

`loader/notebook_probe.sh`: the upload notebook's own cells, run in a Jupyter kernel from a
container that stands in for an analyst's machine (Python 3.12, pandas 2.2.3, pyodbc 5.1.0,
Microsoft ODBC Driver 18), against a throwaway SQL Server 2022 container. The notebook was
generated from a 15-row fixture release so that its embedded hash, row count and digest belong to
the fixture. The fixture carries the awkward cells every test uses (a trailing newline inside a
quoted cell, a double quote, an empty UPRN, an empty RRN, a superseded certificate, junk and
empty data zones, a code value in a count column) and the cases the notebook review asked for:
accented letters, a no-break space, curly quotes, a euro sign and an em dash across four columns;
every wide column one character short of its width, a row of 7,998 characters in the widest two
alone; decimals at the 4-decimal edge, positive, negative and zero; a 2108 lodgement date and a
2002 inspection date; a midnight timestamp; a 12-digit UPRN at the top of the range.

## First run: step 5 waited forever

The first full run never finished. Step 4 printed its 15 rows loaded, and step 5 then waited on
a schema lock. `sys.dm_tran_locks` showed the lock held by a sleeping session with one open
transaction whose last statement was step 4's own `sys.indexes` query. That session had connected
before step 4's loading connection: it was step 1's.

The mechanism, reproduced with a small script against the same server:

1. pyodbc pools connections by default (`pyodbc.pooling` is `True`), so a second
   `pyodbc.connect` with the same string can be handed the first connection back.
2. With the SQL Server ODBC driver, `autocommit=False` means `SET IMPLICIT_TRANSACTIONS ON`:
   every statement, a SELECT included, opens a transaction that stays open until a commit.
3. A pooled connection comes back with that transaction still open, and `autocommit=True` on
   the new connection object does not close it. Step 4's two `CREATE INDEX` statements ran inside
   step 1's transaction, were never committed, and held `Sch-M` locks on the table. Step 5, on a
   fresh session, waited for them without a timeout.

Fixes in `loader/make_notebook.py`: `pyodbc.pooling = False` before the first connection; every
connection that only reads opens with `autocommit=True`; step 3 runs its DROP and CREATE in an
explicit transaction and sets the connection back to autocommit before its two display queries;
step 4's loading connection is closed before the indexes are built; `SET LOCK_TIMEOUT` in steps
3, 4 and 5 so an unexpected lock becomes an error rather than a silent wait. A test asserts each
of these in the generated notebook.

The datazone-ahah notebook has the same mix of pooled connections with and without autocommit
and has not been changed.

## Second full run: eleven scenarios, every one as expected

| Scenario | Expected | Result |
| --- | --- | --- |
| 01 full run, steps 1 to 7 | every step passes | passed; 375 cells of 25 columns read back equal to the CSV; the wide row holds 3,999 and 999 characters (7,998 bytes in `IMPROVEMENTS`); `uprn_osg` NULL in 2 rows, `rrn` NULL in 2, `ADDENDUM_TEXT` empty in 15 and NULL in 0, 2 embedded newlines; the no-break space and the euro sign survived |
| 02 rerun, same folder | the same | the same |
| 03 one byte changed in the CSV | stops at step 2, table untouched | stopped: `the file is not the one this build produced`; table unchanged |
| 04 a rating changed after loading | step 5 fails | `FAIL` on the digest, `the loaded table does not match the build` |
| 05 a NULL `rrn` made the empty string | step 5 fails | the same |
| 06 the trailing newline removed from a `BUILDING_REFERENCE_NUMBER` | step 5 fails | the same |
| 06b a trailing space added to a `TENURE` | step 5 fails | the same (SQL Server's `=` ignores trailing spaces; the digest does not) |
| 07 restored | steps 1, 2, 5 pass | passed |
| 08 a batch the server rejects (chunks of 4, `'x'` in a smallint of the second) | step 4 fails; the first chunk stays | failed with message 245; 4 rows in the table |
| 09 a decimal not in 4-decimal form | step 4 fails before any insert | `is not a 4-decimal value`; 0 rows |
| 10 full run after the failures | every step passes | passed, read-back equal |

Each scenario took about one second. Results: `results/.notebook_probe/out/results.json` and one
executed notebook per scenario (not committed).

## The full table through pyodbc

Step 4's exact code path on the first 200,000 rows of the real CSV, from the same container to
the same kind of server:

| Measure | Value |
| --- | --- |
| Rows per second, steady | 10,300 |
| Time to send one chunk of 20,000 rows | 1.6 s |
| Peak resident memory of the Python process | 785 MB |
| Projected time for 3,787,069 rows | 6 min |

## The real notebook on the full table

`loader/upload_epc.ipynb` as generated for release 2026Q2, every cell, from the client container
to the throwaway server, the delivery folder holding `epc_domestic.csv.gz`, the two SQL scripts
and the notebook. Every step passed; the executed notebook is not committed because it shows
postcodes.

| Step | Time | Outcome |
| --- | --- | --- |
| 1 settings, unpack the 7.8 GB CSV, connect | 14 s | three files found, `can_create_table = 1` |
| 2 hash, row count, header | 65 s | match on all |
| 3 create the table | under 1 s | 127 columns, 5 nullable, three-column key |
| 4 load 3,787,069 rows, then two indexes | 399 s for the rows (9,497 rows/s, steady from 9,900 at the start to 9,400 after a million), 37 s for the indexes | `uprn_osg` NULL in 178,537, `rrn` NULL in 340,010, `ADDENDUM_TEXT` empty in 3,787,069 and NULL in 0, as the manifest says |
| 5 digest inside SQL Server | 25 s | five checks pass, digest total equal to the manifest's `-35655847973013680818794` |
| 6 rows per year, three certificates | under 1 s | 19 years; UPRN 35000002 with its 2013 and 2024 certificates beside the first row of 2024 |
| 7 join by UPRN | under 1 s | seven rows in, seven out, the expected statuses |

The table with its primary key and two indexes takes 20.6 GB in the database. The Python
process of the throughput measurement peaked at 785 MB; the kernel of the full run was not
measured separately, and `fast_executemany` holds one chunk of 20,000 rows at a time.


## Rerun after the switch to the inspection date

Step 7 of the notebook follows `join_by_uprn.sql` and now dates the cohort rows by the
dwelling's inspection date. The eleven scenarios were rerun with the regenerated notebook: every
one as expected.

## Rerun with the address lines in the table

Decision `address-lines-loaded`: the CSV and the table now carry `ADDRESS1`, `ADDRESS2` and
`ADDRESS3`, so the table has 130 columns. The first rerun stopped at step 3 of every scenario with
`the file's header does not match the shipped table definition`, because `docs/sql/import_csv.sql`
had not yet been regenerated: the notebook's header check caught the stale table definition, which
is what it is for. After `python -m epc_ingest.sql_check`, the eleven scenarios ran as expected.
The read-back now includes the three address columns (the fixture's quoted `FLAT 1/2 "THE OLD
MILL"` and accented post town among them): 420 cells of 28 columns equal to the CSV.

## The mechanism, probed again (31 October 2026)

A check of the datazone-ahah note argued that the hang cannot arise where every connection is a
`with` block, because pyodbc commits on exit, so no transaction is left open for the pool to hand
on. The EPC notebook that hung used `with` blocks too (step 1 was `with pyodbc.connect(CONN,
timeout=10) as cn:`), so the point was probed with `loader/notebook_probe/pooling_diag.py` in the
client container against the throwaway server:

| | A: `with`, autocommit False, one SELECT, exit, closed | C: new connect, autocommit=True |
| --- | --- | --- |
| pooling on | spid 55, `@@TRANCOUNT` 1 after the SELECT | spid 55 again; `@@TRANCOUNT` 1 after a SELECT and after CREATE TABLE; `c.autocommit` reads True; another session sees one open transaction on spid 55 |
| pooling off | spid 55, `@@TRANCOUNT` 1 | spid 55 (the number reused by the server); `@@TRANCOUNT` 0; no open transaction |

So the description above, "a pooled connection comes back with that transaction still open", was
not quite the mechanism. A's with-block did commit and A's close did roll back. What the pool
hands on is the physical connection in manual-commit mode at the server: pyodbc's new handle
records `autocommit=True` without the driver changing the session, so every statement on C opens
a transaction that pyodbc, believing itself in autocommit, never commits. The fixes stand:
pooling off is what makes C start clean; autocommit on the read-only connections and the lock
timeouts are belt and braces.

## Rerun with the tie rule (31 October 2026)

Step 7 of the notebook follows `join_by_uprn.sql` and now ranks a same-day pair by the current
flag and then `created_at_parsed`, returning `epc_tie_candidates`. The eleven scenarios were
rerun with the regenerated notebook: every one as expected, 420 cells read back equal.
