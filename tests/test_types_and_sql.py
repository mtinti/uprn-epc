"""The renderings, the digest, the schema rules and the generated SQL."""

import datetime as dt
import gzip
import re
from decimal import Decimal

import pandas as pd
import pytest
import yaml

from epc_ingest import columns as col
from epc_ingest import sql_check
from epc_ingest.core import output
from epc_ingest.core import text_output as tx
from epc_ingest.core.checks import Report
from epc_ingest.pipeline import CONTRACT
from epc_ingest.reader import derive_datazone, norm_postcode

SCHEMA = output.load_schema(col.SCHEMA)
CONTRACT_SPEC = tx.load_contract(CONTRACT)
MARKER = CONTRACT_SPEC["digest"]["null_marker"]


def test_render_value_each_kind():
    assert tx.render_value(dt.date(2026, 3, 1), "date", MARKER) == "2026-03-01"
    assert tx.render_value(dt.datetime(2026, 3, 1, 9, 5, 7), "datetime", MARKER) == "2026-03-01 09:05:07"
    assert tx.render_value(True, "bool", MARKER) == "1" and tx.render_value(False, "bool", MARKER) == "0"
    assert tx.render_value(906700556768, "int64", MARKER) == "906700556768"
    assert tx.render_value(Decimal("250.00"), "decimal", MARKER) == "250.0000"
    assert tx.render_value(Decimal("-0.0"), "decimal", MARKER) == "0.0000"
    assert tx.render_value(None, "date", MARKER) == MARKER and tx.render_value(pd.NA, "int64", MARKER) == MARKER
    with pytest.raises(tx.DecimalDoesNotFit):
        tx.render_value(Decimal("1.00001"), "decimal", MARKER)


def test_dates_are_strict():
    assert tx.parse_date("2108-01-01") == dt.date(2108, 1, 1)
    for bad in ("2008-3-1", "01/03/2008", "2008-02-30", "2008-03-01 ", "2008-03-01T00:00:00"):
        with pytest.raises(ValueError):
            tx.parse_date(bad)
    assert tx.parse_datetime("08/12/2008 11:22:22", "%d/%m/%Y %H:%M:%S") == dt.datetime(2008, 12, 8, 11, 22, 22)
    with pytest.raises(ValueError):
        tx.parse_datetime("8/12/2008 11:22:22", "%d/%m/%Y %H:%M:%S")


def test_datazone_and_postcode_rules():
    zones = {"S01000416"}
    assert derive_datazone("S01000416 (Ythsie)", zones) == ("S01000416", "code")
    assert derive_datazone("S01000416", zones) == ("S01000416", "code")
    assert derive_datazone("S01000417 (Elsewhere)", zones) == ("S01000417", "unknown_code")
    assert derive_datazone("S01000416(Ythsie)", zones) == (None, "not_a_datazone")
    assert derive_datazone("00Q", zones) == (None, "not_a_datazone")
    assert derive_datazone("NA", zones) == (None, "not_a_datazone")
    assert derive_datazone("", zones) == (None, "empty")
    assert derive_datazone("   ", zones) == (None, "empty")
    assert norm_postcode("fk10 1aa") == "FK101AA" and norm_postcode("") is None and norm_postcode(" G12  8QQ ") == "G128QQ"


def _frame():
    return pd.DataFrame({
        "epc_release": pd.Series(["T", "T"], dtype="string"), "source_year": pd.Series([2008, 2008], dtype="Int64"),
        "source_row": pd.Series([1, 2], dtype="Int64"),
        "ADDENDUM_TEXT": pd.Series(["", ""], dtype="string"), "rrn": pd.Series([None, "2008-0001-0000-0000-0001"], dtype="string"),
        "uprn_osg": pd.Series([None, 35000001], dtype="Int64"), "historic_flag": pd.Series([True, False], dtype="boolean"),
        "lodgement_date_parsed": pd.Series([dt.date(2008, 3, 1), dt.date(2008, 3, 2)], dtype=object),
        "energy_consumption_current_num": pd.Series([Decimal("1.5"), Decimal("0")], dtype=object),
    })


def _schema(fields):
    return {"version": "t", "table": "t", "key": ["epc_release", "source_year", "source_row"], "fields": fields, "sha256": "x"}


SMALL = _schema([
    {"name": "epc_release", "type": "string", "width": 8, "nullable": False},
    {"name": "source_year", "type": "int16", "nullable": False},
    {"name": "source_row", "type": "int32", "nullable": False},
    {"name": "ADDENDUM_TEXT", "type": "string", "width": 128, "nullable": False},
    {"name": "rrn", "type": "string", "width": 24, "nullable": True},
    {"name": "uprn_osg", "type": "int64", "nullable": True},
    {"name": "historic_flag", "type": "bool", "nullable": False},
    {"name": "lodgement_date_parsed", "type": "date", "nullable": False},
    {"name": "energy_consumption_current_num", "type": "decimal", "nullable": False},
])


def test_empty_string_and_null_render_differently_and_survive_the_csv(tmp_path):
    columns = [f["name"] for f in SMALL["fields"]]
    rendered = tx.render(_frame(), SMALL, columns, CONTRACT_SPEC)
    assert rendered["ADDENDUM_TEXT"].tolist() == ["", ""] and rendered["rrn"].tolist()[0] == MARKER
    assert rendered["uprn_osg"].tolist() == [MARKER, "35000001"] and rendered["historic_flag"].tolist() == ["1", "0"]
    total = sum(tx.row_hashes(rendered, CONTRACT_SPEC))
    path = tmp_path / "t.csv.gz"
    tx.write_csv(rendered, CONTRACT_SPEC, path)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        text = fh.read()
    assert text.splitlines()[1].startswith("T,2008,1,,,,1,2008-03-01,1.5000")
    report = Report()
    tx.readback_csv_digest(path, columns, SMALL, CONTRACT_SPEC, report, "rb", 2, total)
    assert not report.blocking_failures
    # Had the empty ADDENDUM_TEXT been read back as NULL, the digest would differ.
    wrong = dict(SMALL, fields=[dict(f, nullable=True) if f["name"] == "ADDENDUM_TEXT" else f for f in SMALL["fields"]])
    report = Report()
    tx.readback_csv_digest(path, columns, wrong, CONTRACT_SPEC, report, "rb", 2, total)
    assert [c.name for c in report.blocking_failures] == ["rb.digest_total"]


def test_nullable_text_column_may_not_hold_an_empty_string():
    frame = _frame()
    frame.loc[0, "rrn"] = ""
    with pytest.raises(ValueError):
        tx.render(frame, SMALL, [f["name"] for f in SMALL["fields"]], CONTRACT_SPEC)


def test_reserved_characters_stop_the_render():
    frame = _frame()
    frame.loc[0, "ADDENDUM_TEXT"] = "a\x1fb"
    with pytest.raises(tx.ReservedCharacter):
        tx.render(frame, SMALL, [f["name"] for f in SMALL["fields"]], CONTRACT_SPEC)


def test_parquet_round_trip_keeps_every_kind(tmp_path):
    frame = _frame()
    path = tmp_path / "t.parquet"
    output.write_table(frame, SMALL, path, {"grain": "t"})
    saved = output.read_table(path)
    assert output.compare_frames(saved, frame, SMALL) == {}
    assert saved["lodgement_date_parsed"].iloc[0] == dt.date(2008, 3, 1) and saved["energy_consumption_current_num"].iloc[0] == Decimal("1.5")
    assert saved["ADDENDUM_TEXT"].iloc[0] == "" and pd.isna(saved["rrn"].iloc[0])


def test_schema_rejects_names_differing_only_by_case(tmp_path):
    raw = yaml.safe_load(col.SCHEMA.read_text())
    raw["fields"].append({"name": "inspection_date", "type": "date", "nullable": False})
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    with pytest.raises(ValueError) as e:
        output.load_schema(path)
    assert "INSPECTION_DATE" in str(e.value)
    bad = [dict(c) for c in col.load_published()]
    bad.append({"name": "Rrn", "label": "x", "max_len": 1})
    with pytest.raises(ValueError):
        col.fields(bad)


def test_width_buckets():
    assert [col.width(n) for n in (1, 5, 7, 8, 24, 31, 69, 75, 328, 570, 3330)] == [8, 8, 8, 32, 32, 32, 100, 100, 512, 1000, 4000]
    assert col.width(0) == 128
    with pytest.raises(ValueError):
        col.width(4000)


def test_no_derived_name_equals_a_published_name_in_any_case():
    published = {c["name"].lower() for c in col.load_published()}
    for f in col.DERIVED_FIELDS + col.KEY_FIELDS:
        assert f["name"].lower() not in published, f["name"]
        assert f["name"] == f["name"].lower()


def test_generated_import_sql_restores_empty_and_null_by_schema():
    sql = sql_check.render_import()
    assert "ISNULL([ADDENDUM_TEXT], N'')" in sql and "ISNULL([OSG_REFERENCE_NUMBER], N'')" in sql
    assert "NULLIF([rrn], N'')" in sql and "NULLIF([pc_norm], N'')" in sql and "NULLIF([datazone_2001], N'')" in sql
    assert "CONVERT(bigint, NULLIF([uprn_osg], ''))" in sql and "CONVERT(bit, NULLIF([historic_flag], ''))" in sql
    assert "CONVERT(date, NULLIF([lodgement_date_parsed], ''), 23)" in sql
    assert "CONVERT(datetime2(0), NULLIF([created_at_parsed], ''), 120)" in sql
    assert "[ADDRESS1]" not in sql and "[POSTCODE] nvarchar(32) NOT NULL" in sql
    # Nullability field for field.
    typed = sql.split("CREATE TABLE epc_domestic (")[1].split("CONSTRAINT")[0]
    for f in SCHEMA["fields"]:
        if f["name"] in ("ADDRESS1", "ADDRESS2", "ADDRESS3"):
            continue
        line = [l for l in typed.splitlines() if l.strip().startswith(f"[{f['name']}] ")][0]
        assert (" NOT NULL" in line) == (not f["nullable"]), f["name"]
        assert sql_check.declared_type(f) in line
    assert "[IMPROVEMENTS] varchar(max)" in sql and "[HISTORIC] varchar(8000)" in sql
    assert "IX_epc_domestic_uprn_osg" in sql and "IX_epc_domestic_pc_norm" in sql
    assert "CODEPAGE = '65001'" in sql


def test_generated_check_sql_keeps_max_in_the_digest_and_declares_widths():
    sql = sql_check.render()
    assert sql.count("CONVERT(nvarchar(max), ") == 1   # 127 columns, one chunk, first operand promoted
    assert "CONVERT(varchar(10), [lodgement_date_parsed], 23)" in sql
    assert "CONVERT(varchar(19), [created_at_parsed], 120)" in sql
    assert "CONVERT(varchar(1), [historic_flag])" in sql
    assert "(N'IMPROVEMENTS', 24, N'nvarchar', NULL, NULL, 8000, 0)" in sql
    assert "(N'uprn_osg', 110, N'bigint', NULL, NULL, NULL, 1)" in sql
    assert "(N'created_at_parsed', 118, N'datetime2', 19, 0, NULL, 0)" in sql
    assert "@ran <> 5" in sql
    assert "ADDRESS1" not in sql
