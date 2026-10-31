"""Pooling diagnostic: does a connection declared autocommit=True inherit manual-commit mode from
a pooled session, even after the earlier with-block committed and the connection was closed?

    docker run --rm --network epc_probe -e SA_PW=... -e SERVER=epc_mssql \
      -v $PWD/loader/notebook_probe:/work:ro epc-notebook-test:1 python /work/pooling_diag.py pooling
    ... python /work/pooling_diag.py nopooling

Run 31 October 2026 (docs/sql/NOTEBOOK_PROBE_2026-10-30.md, "The mechanism, probed again"):
with pooling, C got A's session and @@TRANCOUNT was 1 after every statement while pyodbc reported
C.autocommit True, and another session saw the open transaction; without pooling, 0.
"""
import os, sys, pyodbc
pyodbc.pooling = sys.argv[1] == "pooling"       # must be set before the first connect in the process
CONN = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.environ['SERVER']};DATABASE=master;UID=sa;PWD={os.environ['SA_PW']};Encrypt=yes;TrustServerCertificate=yes"
def state(cn, tag):
    r = cn.cursor().execute("SELECT @@SPID, @@TRANCOUNT").fetchone()
    print(f"{tag}: spid={r[0]} trancount_after_select={r[1]}", flush=True)
print(f"--- pyodbc.pooling = {pyodbc.pooling}")
with pyodbc.connect(CONN, timeout=10) as a:
    state(a, "A in with, autocommit=False")
del a                                            # closed: pyodbc rolls back; the physical connection may go to the pool
with pyodbc.connect(CONN, timeout=10, autocommit=True) as c:
    state(c, "C new connect, autocommit=True")
    print("C.autocommit as pyodbc sees it:", c.autocommit)
    c.cursor().execute("CREATE TABLE #t (x int)")
    state(c, "C after CREATE TABLE")
    # Does the server see the transaction? Another session looks at sys.dm_tran_session_transactions.
    spid = c.cursor().execute("SELECT @@SPID").fetchone()[0]
with pyodbc.connect(CONN, timeout=10, autocommit=True) as d:
    n = d.cursor().execute("SELECT COUNT(*) FROM sys.dm_tran_session_transactions WHERE session_id = ?", spid).fetchone()[0]
    print(f"open transactions on C's session seen from another session: {n}")
