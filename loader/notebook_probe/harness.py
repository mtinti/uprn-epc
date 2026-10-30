"""Run the fixture's upload_epc.ipynb against SQL Server in Docker through pyodbc, as it is and
under hostile conditions: the notebook's own code, cell by cell, in a Jupyter kernel.

Runs inside the image of loader/notebook_probe/Dockerfile, started by loader/notebook_probe.sh:
/data/delivery is the fixture's delivery folder (CSV, two SQL scripts, notebook), read-only;
/out receives the executed notebooks and results.json. SA_PW and SERVER come from the environment.

Scenarios: the full notebook twice; a changed byte in the CSV stopping at step 2; a changed
value, a NULL made empty, a trailing newline removed and a trailing space added, each failing
the digest of step 5 and passing again once restored; a batch SQL Server rejects, which keeps
the chunks committed before it; a decimal not in 4-decimal form, which stops before any insert;
then the full notebook once more. After each full run every cell of a chosen set of columns is
read back through pyodbc and compared with the CSV text."""
import csv, gzip, json, os, secrets, shutil, sys, time, traceback
from pathlib import Path

import nbformat, pyodbc
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

SA_PW = os.environ.pop("SA_PW")
SERVER = os.environ.get("SERVER", "epc_mssql")
DELIVERY, RUNS, OUT = Path("/data/delivery"), Path("/tmp/runs"), Path("/out")
USER, USER_PW = "epc_nbtest_user", secrets.token_urlsafe(24) + "aA1!"
DB, TABLE = "epc_nbtest", "dbo.epc_domestic"
SCENARIOS = 11   # main() must record exactly this many, every one ok, or exit nonzero
RESULTS = []


def sa(db="master"):
    return pyodbc.connect(f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={db};UID=sa;PWD={SA_PW};"
                          "Encrypt=yes;TrustServerCertificate=yes;", autocommit=True, timeout=30)


def q(sql, db=DB):
    with sa(db) as cn:
        cur = cn.cursor().execute(sql)
        return cur.fetchall() if cur.description else None


def setup():
    with sa() as cn:
        cur = cn.cursor()
        cur.execute(f"IF DB_ID(N'{DB}') IS NOT NULL BEGIN ALTER DATABASE [{DB}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{DB}]; END")
        cur.execute(f"IF SUSER_ID(N'{USER}') IS NOT NULL DROP LOGIN [{USER}]")
        cur.execute(f"CREATE LOGIN [{USER}] WITH PASSWORD = N'{USER_PW}', CHECK_POLICY = OFF")
        cur.execute(f"CREATE DATABASE [{DB}]")
    with sa(DB) as cn:
        cur = cn.cursor()
        cur.execute(f"CREATE USER [{USER}] FOR LOGIN [{USER}]")
        cur.execute(f"GRANT CREATE TABLE TO [{USER}]")
        cur.execute(f"GRANT ALTER, SELECT, INSERT, UPDATE, DELETE, REFERENCES ON SCHEMA::dbo TO [{USER}]")


def teardown():
    with sa() as cn:
        cur = cn.cursor()
        cur.execute(f"IF DB_ID(N'{DB}') IS NOT NULL BEGIN ALTER DATABASE [{DB}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{DB}]; END")
        cur.execute(f"IF SUSER_ID(N'{USER}') IS NOT NULL DROP LOGIN [{USER}]")


def folder(name, mutate=None):
    path = RUNS / name
    if path.exists():
        shutil.rmtree(path)
    shutil.copytree(DELIVERY, path)
    if mutate:
        mutate(path)
    return path


def step_index(nb, step):
    return next(i for i, c in enumerate(nb.cells) if c.cell_type == "code" and c.source.startswith(f"# Step {step} "))


def point_at(nb, path):
    cell = nb.cells[step_index(nb, 1)]
    src = cell.source
    for old, new in [('FOLDER   = Path(r"")', f'FOLDER   = Path(r"{path}")'), ('SERVER   = "sql-de-01"', f'SERVER   = "{SERVER}"'),
                     ('DATABASE = "IMD"', f'DATABASE = "{DB}"'),
                     ('"Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;")', f'"UID={USER};PWD={USER_PW};Encrypt=yes;TrustServerCertificate=yes;")')]:
        assert src.count(old) == 1, old
        src = src.replace(old, new)
    cell.source = src


def run(name, path, steps=None, edit=None, expect_fail=None, expect_error=None, expect_text=(), check=None):
    nb = nbformat.read(path / "upload_epc.ipynb", as_version=4)
    point_at(nb, path)
    if edit:
        edit(nb)
    chosen = [i for i, c in enumerate(nb.cells) if c.cell_type == "code"]
    if steps is not None:
        chosen = [step_index(nb, s) for s in steps]
    started, failed, error = time.time(), None, None
    # A cell that runs longer than ten minutes on a 15-row fixture is a hang, and fails the scenario.
    client = NotebookClient(nb, kernel_name="python3", timeout=600, resources={"metadata": {"path": str(path)}})
    with client.setup_kernel():
        for i in chosen:
            try:
                client.execute_cell(nb.cells[i], i)
            except Exception as e:
                first = nb.cells[i].source.splitlines()[0]
                failed = first[2:].split(" —")[0]
                error = ((e.ename + ": " + str(e.evalue)) if isinstance(e, CellExecutionError) else repr(e))[:400]
                break
    # Never write the test password into the saved notebook.
    nb.cells[step_index(nb, 1)].source = nb.cells[step_index(nb, 1)].source.replace(USER_PW, "<redacted>")
    nbformat.write(nb, OUT / f"{name}.ipynb")
    text = "\n".join(o.get("text", "") + o.get("data", {}).get("text/plain", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    found = {t: t in text for t in expect_text}
    ok = (failed == expect_fail) and all(found.values()) and (expect_error is None or (error or "").find(expect_error) >= 0)
    extra = None
    if check:
        try:
            extra = check()
            ok = ok and extra.get("ok", True)
        except Exception as e:
            extra, ok = {"check_error": repr(e)}, False
    result = {"test": name, "ok": ok, "failed_at": failed, "expected_failure": expect_fail, "expected_error": expect_error,
              "error": error, "texts_found": found, "extra": extra, "seconds": round(time.time() - started, 1)}
    RESULTS.append(result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    (OUT / "results.json").write_text(json.dumps(RESULTS, indent=1, ensure_ascii=False))
    return result


def csv_rows():
    csv.field_size_limit(1 << 24)
    with gzip.open(DELIVERY / "epc_domestic.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        return {(int(r["source_year"]), int(r["source_row"])): r for r in csv.DictReader(fh)}


def loaded_matches_csv():
    """Read back through pyodbc and compare, cell by cell, with the CSV text: the published text
    columns as they are, empty for empty; the derived ones rendered in SQL; NULL where the CSV is empty."""
    rows = csv_rows()
    cols = ["ADDRESS1", "ADDRESS2", "ADDRESS3", "POSTCODE", "IMPROVEMENTS", "LOCAL_AUTHORITY_LABEL", "MAINHEAT_DESCRIPTION", "PHOTO_SUPPLY", "BUILDING_REFERENCE_NUMBER", "TENURE",
            "REPORT_REFERENCE_NUMBER", "OSG_REFERENCE_NUMBER", "ADDENDUM_TEXT", "rrn", "pc_norm", "datazone_2001", "datazone_2011"]
    rendered = {"uprn_osg": "CONVERT(nvarchar(30), uprn_osg)", "uprn_sepcr": "CONVERT(nvarchar(30), uprn_sepcr)",
                "lodgement_date_parsed": "CONVERT(nvarchar(30), lodgement_date_parsed, 23)", "inspection_date_parsed": "CONVERT(nvarchar(30), inspection_date_parsed, 23)",
                "created_at_parsed": "REPLACE(CONVERT(nvarchar(30), created_at_parsed, 126), 'T', ' ')",
                "historic_flag": "CONVERT(nvarchar(1), historic_flag)", "energy_consumption_current_num": "CONVERT(nvarchar(40), energy_consumption_current_num)",
                "co2_emissions_current_num": "CONVERT(nvarchar(40), co2_emissions_current_num)", "co2_emiss_curr_per_floor_area_num": "CONVERT(nvarchar(40), co2_emiss_curr_per_floor_area_num)",
                "total_floor_area_int": "CONVERT(nvarchar(20), total_floor_area_int)", "current_energy_efficiency_int": "CONVERT(nvarchar(20), current_energy_efficiency_int)"}
    select = ", ".join([f"[{c}]" for c in cols] + list(rendered.values()))
    got = q(f"SELECT source_year, source_row, {select} FROM {TABLE}")
    assert len(got) == len(rows) == 15, (len(got), len(rows))
    diffs, checked = [], 0
    for r in got:
        key = (r[0], r[1]); expect = rows[key]
        for i, c in enumerate(cols + list(rendered)):
            e, g = expect[c], r[2 + i]
            if c in ("rrn", "pc_norm", "datazone_2001", "datazone_2011", "uprn_osg") and e == "":
                e = None
            checked += 1
            if e != g:
                diffs.append({"row": key, "column": c, "csv": (e or "")[:60], "sql": (g or "")[:60] if isinstance(g, str) else g})
    long = q(f"SELECT LEN(IMPROVEMENTS), LEN(PHOTO_SUPPLY), DATALENGTH(IMPROVEMENTS) FROM {TABLE} WHERE source_year = 2024 AND source_row = 7")[0]
    counts = q(f"SELECT COUNT(*), SUM(CASE WHEN uprn_osg IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN rrn IS NULL THEN 1 ELSE 0 END), "
               f"SUM(CASE WHEN ADDENDUM_TEXT = N'' THEN 1 ELSE 0 END), SUM(CASE WHEN ADDENDUM_TEXT IS NULL THEN 1 ELSE 0 END), "
               f"SUM(CASE WHEN BUILDING_REFERENCE_NUMBER LIKE N'%' + NCHAR(10) THEN 1 ELSE 0 END) FROM {TABLE}")[0]
    nbsp = q(f"SELECT COUNT(*) FROM {TABLE} WHERE IMPROVEMENTS LIKE N'%' + NCHAR(160) + N'%' AND IMPROVEMENTS LIKE N'%€%'")[0][0]
    ok = not diffs and list(long) == [3999, 999, 7998] and list(counts) == [15, 2, 2, 15, 0, 2] and nbsp == 1
    return {"ok": ok, "cells_checked": checked, "diffs": diffs, "wide_row": list(long), "counts": list(counts), "nbsp_euro_rows": nbsp}


def main():
    OUT.mkdir(exist_ok=True)
    setup()
    full_ok = ("the file is exactly what the build wrote", "every check passed", "seven rows in, seven out, every status as expected")
    run("01_full_run", folder("a"), expect_text=full_ok, check=loaded_matches_csv)
    run("02_rerun_same_folder", RUNS / "a", expect_text=full_ok, check=loaded_matches_csv)

    def flip(p):
        with gzip.open(p / "epc_domestic.csv.gz") as src, open(p / "epc_domestic.csv", "wb") as dst:
            shutil.copyfileobj(src, dst)
        data = bytearray((p / "epc_domestic.csv").read_bytes()); i = data.index(b"Owner-occupied"); data[i] = ord("o")
        (p / "epc_domestic.csv").write_bytes(data)
    before = q(f"SELECT COUNT_BIG(*), CHECKSUM_AGG(BINARY_CHECKSUM(*)) FROM {TABLE}")[0]
    unchanged = lambda: {"ok": q(f"SELECT COUNT_BIG(*), CHECKSUM_AGG(BINARY_CHECKSUM(*)) FROM {TABLE}")[0] == before}
    run("03_one_byte_changed_in_csv", folder("t03", flip), expect_fail="Step 2", expect_error="the file is not the one this build produced", check=unchanged)

    # A changed loaded value, and a NULL made the empty string: step 5 must fail on both, then pass once restored.
    def tampered(name, do, undo):
        q(do)
        try:
            return run(name, RUNS / "a", steps=[1, 2, 5], expect_fail="Step 5", expect_error="does not match the build", expect_text=("FAIL",))
        finally:
            q(undo)
    tampered("04_changed_value_caught_by_digest", f"UPDATE {TABLE} SET CURRENT_ENERGY_RATING = N'E' WHERE source_year = 2024 AND source_row = 1",
             f"UPDATE {TABLE} SET CURRENT_ENERGY_RATING = N'D' WHERE source_year = 2024 AND source_row = 1")
    tampered("05_null_made_empty_caught_by_digest", f"UPDATE {TABLE} SET rrn = N'' WHERE source_year = 2024 AND source_row = 2",
             f"UPDATE {TABLE} SET rrn = NULL WHERE source_year = 2024 AND source_row = 2")
    tampered("06_trailing_newline_removed_caught_by_digest", f"UPDATE {TABLE} SET BUILDING_REFERENCE_NUMBER = N'1000000002' WHERE source_year = 2024 AND source_row = 2",
             f"UPDATE {TABLE} SET BUILDING_REFERENCE_NUMBER = N'1000000002' + NCHAR(10) WHERE source_year = 2024 AND source_row = 2")
    tampered("06b_trailing_space_added_caught_by_digest", f"UPDATE {TABLE} SET TENURE = N'Owner-occupied ' WHERE source_year = 2024 AND source_row = 1",
             f"UPDATE {TABLE} SET TENURE = N'Owner-occupied' WHERE source_year = 2024 AND source_row = 1")
    run("07_restored_passes_again", RUNS / "a", steps=[1, 2, 5], expect_text=("every check passed",), check=unchanged)

    # A batch the server rejects: chunks of 4 rows, the second carrying a value SQL Server cannot convert.
    def break_batch(nb):
        cell = nb.cells[step_index(nb, 4)]
        cell.source = cell.source.replace("CHUNK = 20_000", "CHUNK = 4").replace(
            "        cur.executemany(insert, chunk[COLUMNS].values.tolist())",
            "        if loaded == 4: chunk.loc[chunk.index[0], 'source_year'] = 'x'\n        cur.executemany(insert, chunk[COLUMNS].values.tolist())")
        assert "loaded == 4" in cell.source
    def first_chunk_only():
        n = q(f"SELECT COUNT(*) FROM {TABLE}")[0][0]
        return {"ok": n == 4, "rows_left_in_table": n, "note": "step 4 commits per chunk: the rows before the failing chunk stay"}
    run("08_failed_batch_keeps_earlier_chunks", RUNS / "a", steps=[1, 2, 3, 4], edit=break_batch, expect_fail="Step 4", check=first_chunk_only)

    # The empty-string check of step 4 before anything is sent: a decimal not in 4-decimal form stops before the insert.
    def break_decimal(nb):
        cell = nb.cells[step_index(nb, 4)]
        cell.source = cell.source.replace("        chunk = chunk.astype(object)",
            "        chunk = chunk.astype(object)\n        chunk.loc[chunk.index[0], 'energy_consumption_current_num'] = '1.5'")
    run("09_bad_decimal_stops_before_insert", RUNS / "a", steps=[1, 2, 3, 4], edit=break_decimal, expect_fail="Step 4", expect_error="is not a 4-decimal value",
        check=lambda: {"ok": q(f"SELECT COUNT(*) FROM {TABLE}")[0][0] == 0})
    run("10_full_run_after_failures", RUNS / "a", expect_text=full_ok, check=loaded_matches_csv)
    teardown()
    failed = [r["test"] for r in RESULTS if not r["ok"]]
    print("SUMMARY", len(RESULTS) - len(failed), "of", len(RESULTS), "tests as expected", flush=True)
    # A caller or CI must see a failure as a nonzero status, never only as a word in the output.
    if failed or len(RESULTS) != SCENARIOS:
        print(f"FAILED: {failed or 'none'}; {len(RESULTS)} of {SCENARIOS} scenarios recorded", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        (OUT / "results.json").write_text(json.dumps(RESULTS, indent=1, ensure_ascii=False))
        raise
