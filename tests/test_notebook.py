"""The upload notebook: it is generated from the manifest, every code cell parses, and the
table-definition parsing of step 3 reproduces the CSV header from the shipped import script."""

import ast
import gzip
import json
import re
from pathlib import Path

import duckdb
import nbformat
import pytest

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "loader" / "upload_epc.ipynb"
MANIFEST = ROOT / "results" / "manifest.json"
IMPORT_SQL = ROOT / "docs" / "sql" / "import_csv.sql"

needs_build = pytest.mark.skipif(not (NOTEBOOK.is_file() and MANIFEST.is_file()), reason="no build or notebook present")


@needs_build
def test_notebook_cells_parse_and_carry_the_manifest_numbers():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    m = json.loads(MANIFEST.read_text())["csv"]
    code = [c.source for c in nb.cells if c.cell_type == "code"]
    assert len(code) == 7
    for source in code:
        ast.parse(source.replace("display(", "print("))
    step2 = code[1]
    assert m["uncompressed_sha256"] in step2 and str(m["uncompressed_bytes"]) in step2
    assert str(m["rows"]) in step2 and m["digest"]["total"] in step2
    text = "\n".join(c.source for c in nb.cells)
    assert "TEST STREET" not in text and "ADDRESS1" not in text


@needs_build
def test_notebook_connections_cannot_inherit_an_open_transaction():
    """Found by the notebook probe of 30 October 2026: pyodbc pools connections, the SQL Server
    ODBC driver opens an implicit transaction on any statement under autocommit=False, and a pooled
    connection comes back with that transaction still open. Step 4's autocommit connection was given
    step 1's session and its CREATE INDEX statements never committed, so step 5 waited forever on the
    schema locks. Pooling must be off before the first connection, every connection that only reads must
    autocommit, and the two that write must end with no transaction open."""
    nb = nbformat.read(NOTEBOOK, as_version=4)
    code = {c.source.split(" ")[2]: c.source for c in nb.cells if c.cell_type == "code"}
    step1 = code["1"]
    assert step1.index("pyodbc.pooling = False") < step1.index("pyodbc.connect(")
    connects = re.findall(r"pyodbc\.connect\((.*?)\)", "\n".join(code.values()))
    assert len(connects) == 7
    without_autocommit = [c for c in connects if "autocommit=True" not in c]
    assert without_autocommit == ["CONN, timeout=120"], without_autocommit    # step 4's loading connection, which commits per chunk
    step3, step4 = code["3"], code["4"]
    assert "cn.autocommit = False" in step3 and step3.count("cn.autocommit = True") == 2 and step3.index("cn.commit()") < step3.rindex("cn.autocommit = True") < step3.index("display(")
    assert "cn.close()" in step4 and step4.index("cn.close()") < step4.index("for statement in INDEXES")
    assert "SET LOCK_TIMEOUT" in step3 and "SET LOCK_TIMEOUT" in step4 and "SET LOCK_TIMEOUT" in code["5"]


def test_step_3_parsing_reproduces_the_csv_header():
    recipe = IMPORT_SQL.read_text(encoding="utf-8")
    block = re.search(r"CREATE TABLE epc_domestic \((.*?)\n\);", recipe, re.S)
    assert block
    line = re.compile(r"\[([^\]]+)\] (nvarchar\(\d+\)|bigint|smallint|int|bit|datetime2\(0\)|date|decimal\(\d+,\d+\))( NOT NULL)?")
    spec = line.findall(block.group(1))
    columns = [name for name, _, _ in spec]
    not_null = {name for name, _, nn in spec if nn}
    assert len(columns) == 127 and len(columns) - len(not_null) == 5
    assert {n for n in columns if n not in not_null} == {"rrn", "uprn_osg", "pc_norm", "datazone_2001", "datazone_2011"}
    csv_path = ROOT / "results" / "epc_domestic.csv.gz"
    if csv_path.is_file():
        with gzip.open(csv_path, "rt", encoding="utf-8", newline="") as fh:
            header = fh.readline().rstrip("\n").split(",")
        assert header == columns
    indexes = [l for l in recipe.splitlines() if l.startswith("CREATE INDEX IX_epc_domestic_")]
    assert len(indexes) == 2


def _step_6_queries():
    """The two queries of step 6, with T-SQL spelling changed for DuckDB: TOP (1) to LIMIT 1,
    COUNT_BIG to COUNT, CONVERT(decimal(5,1), x) to CAST(x AS DECIMAL(5,1))."""
    nb = nbformat.read(NOTEBOOK, as_version=4)
    step6 = next(c.source for c in nb.cells if c.cell_type == "code" and c.source.startswith("# Step 6 "))
    queries = re.findall(r'pd\.read_sql\(f"""(.*?)""", cn\)', step6, re.S)
    assert len(queries) == 2
    out = []
    for q in queries:
        q = q.replace("{TABLE}", "epc_domestic").replace("COUNT_BIG(*)", "COUNT(*)")
        q = re.sub(r"CONVERT\(decimal\(5,1\), (.*?)\) AS", r"CAST(\1 AS DECIMAL(5,1)) AS", q)
        q = re.sub(r"SELECT TOP \(1\) (.*?) ORDER BY uprn_osg\)", r"SELECT \1 ORDER BY uprn_osg LIMIT 1)", q, flags=re.S)
        assert "TOP" not in q, q
        out.append(q)
    return out


def _table(con, pairs):
    con.execute("CREATE TABLE epc_domestic (source_year SMALLINT, source_row INTEGER, uprn_osg BIGINT, pc_norm VARCHAR, "
                "lodgement_date_parsed DATE, historic_flag BOOLEAN, CURRENT_ENERGY_RATING VARCHAR, current_energy_efficiency_int INTEGER, "
                "total_floor_area_int INTEGER, PROPERTY_TYPE VARCHAR, BUILT_FORM VARCHAR, CONSTRUCTION_AGE_BAND VARCHAR)")
    rows = [(2024, 1, 35000009, "FK101AA", "2024-01-05", False, "C", 70, 90, "House", "Detached", "1950-1964")]
    for uprn, n in pairs:
        for i in range(n):
            rows.append((2010 + i, 100 + len(rows), uprn, "FK101AA", f"{2010 + i}-06-01", i < n - 1, "D", 60, 80, "Flat", "Mid-terrace", "1900-1929"))
    con.executemany("INSERT INTO epc_domestic VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)


@needs_build
def test_step_6_picks_one_twice_assessed_dwelling():
    """Two dwellings each with two certificates, plus one with three and one with one: the sample
    must return the 2024 row and the two certificates of the lowest qualifying UPRN, four rows."""
    per_year, sample = _step_6_queries()
    con = duckdb.connect()
    _table(con, [(35000002, 2), (35000001, 2), (35000003, 3), (35000004, 1)])
    assert con.execute(per_year).fetchall()[0][0] == 2010
    rows = con.execute(sample).fetchall()
    assert [(r[0], r[2]) for r in rows] == [(2010, 35000001), (2011, 35000001), (2024, 35000009)]


@needs_build
def test_step_6_with_no_twice_assessed_dwelling_shows_the_2024_row_only():
    _, sample = _step_6_queries()
    con = duckdb.connect()
    _table(con, [(35000003, 3), (35000004, 1)])
    rows = con.execute(sample).fetchall()
    assert len(rows) == 1 and rows[0][0] == 2024


def test_the_old_grouped_min_selector_fails_with_two_qualifying_dwellings():
    """The form the notebook carried before 30 October 2026: GROUP BY returns one MIN per group,
    so the equality receives several rows. DuckDB rejects it as SQL Server does."""
    con = duckdb.connect()
    _table(con, [(35000002, 2), (35000001, 2)])
    with pytest.raises(duckdb.Error, match="More than one row"):
        con.execute("SELECT * FROM epc_domestic WHERE uprn_osg = (SELECT MIN(uprn_osg) FROM epc_domestic "
                    "WHERE uprn_osg IS NOT NULL GROUP BY uprn_osg HAVING COUNT(*) = 2)").fetchall()
