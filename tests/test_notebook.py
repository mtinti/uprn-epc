"""The upload notebook: it is generated from the manifest, every code cell parses, and the
table-definition parsing of step 3 reproduces the CSV header from the shipped import script."""

import ast
import gzip
import json
import re
from pathlib import Path

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
