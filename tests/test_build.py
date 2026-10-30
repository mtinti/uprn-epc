"""The build on a synthetic release: it passes on the publisher's shape, and each hostile file
fails with its own named check and nothing written."""

import gzip
import json
from decimal import Decimal

import pandas as pd
import pytest

from epc_ingest import columns as col
from epc_ingest import pipeline
from epc_ingest.core import output
from epc_ingest.core.checks import BuildStopped, Report
from epc_ingest.core.sources import load_registry
from epc_ingest.reader import read_year, read_zone_list

from synthetic import LABELS, NAMES, default_rows, make_release, make_row, sha256_file


def _build(tmp_path, **kwargs):
    registry = make_release(tmp_path, **kwargs)
    return pipeline.build(results=tmp_path / "results", registry_path=registry, source_root=tmp_path / "sources", log=lambda *a: None)


def test_synthetic_release_builds_and_reads_back(tmp_path):
    manifest = _build(tmp_path)
    assert manifest["summary"]["blocking_failed"] == 0
    assert manifest["csv"]["rows"] == 10 and manifest["parquet"]["row_groups"] == 2
    saved = output.read_table(tmp_path / "results" / "epc_domestic.parquet")
    # The published text is untouched: trailing space, embedded newline, quote, code values.
    row2 = saved[(saved["source_year"] == 2008) & (saved["source_row"] == 2)].iloc[0]
    assert row2["BUILDING_REFERENCE_NUMBER"] == "1000000002\n" and row2["uprn_sepcr"] == 1000000002
    assert row2["rrn"] is pd.NA or pd.isna(row2["rrn"])
    assert row2["REPORT_REFERENCE_NUMBER"] == "" and row2["historic_flag"] is True or bool(row2["historic_flag"])
    row3 = saved[(saved["source_year"] == 2008) & (saved["source_row"] == 3)].iloc[0]
    assert row3["ADDRESS1"] == 'FLAT 1/2 "THE OLD MILL"' and pd.isna(row3["uprn_osg"]) and row3["OSG_REFERENCE_NUMBER"] == ""
    assert row3["datazone_2001_status"] == "not_a_datazone" and row3["datazone_2011_status"] == "not_a_datazone"
    row4 = saved[(saved["source_year"] == 2008) & (saved["source_row"] == 4)].iloc[0]
    assert row4["uprn_osg"] == 906700556768 and row4["pc_norm"] == "G128QQ" and row4["FLAT_TOP_STOREY"] == "00"
    assert row4["datazone_2001_status"] == "empty" and pd.isna(row4["datazone_2001"])
    row1 = saved[(saved["source_year"] == 2026) & (saved["source_row"] == 1)].iloc[0]
    assert row1["ADDRESS1"] == "1 TEST STREET " and row1["datazone_2011"] == "S01006982"
    assert row1["energy_consumption_current_num"] == Decimal("250.00") and row1["total_floor_area_int"] == 85
    # The CSV withholds the address lines and keeps the postcode.
    with gzip.open(tmp_path / "results" / "epc_domestic.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        header = fh.readline().rstrip("\n").split(",")
    assert "ADDRESS1" not in header and "POSTCODE" in header and "pc_norm" in header
    assert len(header) == 127 and header[:3] == ["epc_release", "source_year", "source_row"]
    report = (tmp_path / "results" / "BUILD_REPORT.md").read_text()
    assert "TEST STREET" not in report and "FK10" not in report and "(withheld)" in report


def test_build_report_and_manifest_hold_no_address(tmp_path):
    _build(tmp_path)
    for name in ("manifest.json", "BUILD_REPORT.md"):
        text = (tmp_path / "results" / name).read_text()
        assert "TEST STREET" not in text and "THE OLD MILL" not in text


def _expect_failure(tmp_path, check_name, **kwargs):
    with pytest.raises(BuildStopped):
        _build(tmp_path, **kwargs)
    assert not (tmp_path / "results" / "manifest.json").exists()
    return check_name


def _year(rows, **spec):
    return dict(rows=rows, **spec)


def test_wrong_label_row_fails(tmp_path):
    labels = list(LABELS)
    labels[5] = "ADDRESS3"
    registry = make_release(tmp_path, years={2008: _year(default_rows(2008), labels=labels)})
    report = Report()
    reg = load_registry(registry, tmp_path / "sources")
    with pytest.raises(BuildStopped):
        read_year(reg.root / reg.members[0]["file"], reg.members[0], col.load_published(), output.load_schema(col.SCHEMA),
                  {2001: set(), 2011: set()}, "TEST", report)
    assert [c.name for c in report.blocking_failures] == ["2008.header_labels"]


def test_106_fields_fails(tmp_path):
    names = NAMES[:-1]
    rows = [[r[n] for n in names] for r in default_rows(2008)]
    registry = make_release(tmp_path, years={2008: _year(rows, names=names)})
    reg = load_registry(registry, tmp_path / "sources")
    report = Report()
    with pytest.raises(BuildStopped):
        read_year(reg.root / reg.members[0]["file"], reg.members[0], col.load_published(), output.load_schema(col.SCHEMA),
                  {2001: set(), 2011: set()}, "TEST", report)
    assert "2008.header_names" in {c.name for c in report.blocking_failures}


def _failing_check(tmp_path, year_spec, zones=None):
    registry = make_release(tmp_path, years={2008: year_spec})
    reg = load_registry(registry, tmp_path / "sources")
    report = Report()
    with pytest.raises(BuildStopped):
        read_year(reg.root / reg.members[0]["file"], reg.members[0], col.load_published(), output.load_schema(col.SCHEMA),
                  zones or {2001: {"S01000416"}, 2011: {"S01006982"}}, "TEST", report)
    return {c.name: c.detail for c in report.blocking_failures}


def test_non_utf8_byte_fails(tmp_path):
    good = default_rows(2008)
    import io, csv
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(NAMES); w.writerow(LABELS)
    for r in good:
        w.writerow([r[n] for n in NAMES])
    raw = b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8").replace(b"ALLOA", b"ALL\xd3A")
    failures = _failing_check(tmp_path, _year(good, raw_bytes=raw))
    assert list(failures) == ["2008.utf8"]


def test_created_at_in_another_year_fails(tmp_path):
    rows = default_rows(2008)
    rows[2]["CREATED_AT"] = "05/04/2009 10:00:00"
    failures = _failing_check(tmp_path, rows)
    assert "2008.created_at_year" in failures and "2009" in failures["2008.created_at_year"]


def test_historic_in_capitals_fails(tmp_path):
    rows = default_rows(2008)
    rows[0]["HISTORIC"] = "TRUE"
    failures = _failing_check(tmp_path, rows)
    assert "2008.derived_values_parse" in failures and "HISTORIC" in failures["2008.derived_values_parse"]


def test_repeated_rrn_fails(tmp_path):
    rows = default_rows(2008)
    rows[3]["REPORT_REFERENCE_NUMBER"] = rows[0]["REPORT_REFERENCE_NUMBER"]
    failures = _failing_check(tmp_path, rows)
    assert "2008.rrn_unique_in_file" in failures


def test_malformed_date_and_non_integer_floor_area_stop_the_build(tmp_path):
    rows = default_rows(2008)
    rows[0]["LODGEMENT_DATE"] = "2008-3-1"
    rows[1]["TOTAL_FLOOR_AREA"] = "85.5"
    rows[2]["INSPECTION_DATE"] = "01/03/2008"
    failures = _failing_check(tmp_path, rows)
    detail = failures["2008.derived_values_parse"]
    assert "LODGEMENT_DATE row 1" in detail and "TOTAL_FLOOR_AREA row 2" in detail and "INSPECTION_DATE row 3" in detail


def test_text_longer_than_width_fails(tmp_path):
    rows = default_rows(2008)
    rows[0]["IMPROVEMENTS"] = "x" * 4001
    failures = _failing_check(tmp_path, rows)
    assert failures["2008.text_within_width"] == "longest value per column over its width"


def test_well_formed_zone_not_in_list_fails_the_build(tmp_path):
    rows = default_rows(2008)
    rows[0]["DATA_ZONE"] = "S01999999 (Nowhere)"
    with pytest.raises(BuildStopped) as stop:
        _build(tmp_path, years={2008: rows})
    assert "datazone_2001_status.no_unknown_code" in str(stop.value)


def test_changed_member_byte_and_wrong_row_pin_fail(tmp_path):
    registry = make_release(tmp_path)
    path = tmp_path / "sources" / "epc_test" / "extracted" / "2008.csv"
    data = path.read_bytes()
    path.write_bytes(data.replace(b"Owner-occupied", b"owner-occupied", 1))
    with pytest.raises(BuildStopped) as stop:
        pipeline.build(results=tmp_path / "results", registry_path=registry, source_root=tmp_path / "sources", log=lambda *a: None)
    assert "source.epc_test/extracted/2008.csv" in str(stop.value)
    path.write_bytes(data)
    tmp2 = tmp_path / "second"
    tmp2.mkdir()
    registry2 = make_release(tmp2, pin_rows={2008: 4})
    with pytest.raises(BuildStopped) as stop:
        pipeline.build(results=tmp2 / "results", registry_path=registry2, source_root=tmp2 / "sources", log=lambda *a: None)
    assert "2008.rows" in str(stop.value)


def test_verify_archive_hashes_the_archive(tmp_path):
    registry = make_release(tmp_path)
    (tmp_path / "sources" / "epc_test" / "archive.7z").write_bytes(b"changed")
    pipeline.build(results=tmp_path / "results", registry_path=registry, source_root=tmp_path / "sources", log=lambda *a: None)
    with pytest.raises(BuildStopped) as stop:
        pipeline.build(results=tmp_path / "results2", registry_path=registry, source_root=tmp_path / "sources", verify_archive=True, log=lambda *a: None)
    assert "archive.7z" in str(stop.value)


def test_padded_uprn_gives_the_same_integer(tmp_path):
    rows = default_rows(2008)
    rows[0]["OSG_REFERENCE_NUMBER"] = "000035000001"
    rows[1]["OSG_REFERENCE_NUMBER"] = "35000001"
    rows[1]["BUILDING_REFERENCE_NUMBER"] = rows[0]["BUILDING_REFERENCE_NUMBER"]   # one dwelling, two certificates
    manifest = _build(tmp_path, years={2008: rows})
    saved = output.read_table(tmp_path / "results" / "epc_domestic.parquet")
    assert saved["uprn_osg"].iloc[0] == saved["uprn_osg"].iloc[1] == 35000001
    assert saved["OSG_REFERENCE_NUMBER"].iloc[0] == "000035000001"


def test_generated_schema_matches_the_file():
    assert col.schema(col.load_published()) == {k: v for k, v in __import__("yaml").safe_load(col.SCHEMA.read_text()).items()}
    assert len(col.load_published()) == 107


def test_datazone_lists_read(tmp_path):
    registry = make_release(tmp_path)
    reg = load_registry(registry, tmp_path / "sources")
    assert read_zone_list(reg.root / reg.datazone_lists[2001]["file"], reg.datazone_lists[2001]) == ["S01000001", "S01000416", "S01006505"]
    assert read_zone_list(reg.root / reg.datazone_lists[2011]["file"], reg.datazone_lists[2011]) == ["S01006506", "S01006982", "S01013481"]


def test_uprn_not_one_to_one_fails_the_build(tmp_path):
    rows = default_rows(2008)
    rows[1]["OSG_REFERENCE_NUMBER"] = rows[0]["OSG_REFERENCE_NUMBER"]   # one Gazetteer UPRN, two register numbers
    with pytest.raises(BuildStopped) as stop:
        _build(tmp_path, years={2008: rows})
    assert "table.uprn_one_to_one" in str(stop.value)


def test_rrn_repeated_across_files_fails_the_build(tmp_path):
    a, b = default_rows(2008), default_rows(2026)
    b[0]["REPORT_REFERENCE_NUMBER"] = a[0]["REPORT_REFERENCE_NUMBER"]
    with pytest.raises(BuildStopped) as stop:
        _build(tmp_path, years={2008: a, 2026: b})
    assert "table.rrn_unique" in str(stop.value)


def test_a_nullable_column_missing_in_every_row_builds(tmp_path):
    rows = default_rows(2008)
    for r in rows:
        r["REPORT_REFERENCE_NUMBER"] = ""
        r["POSTCODE"] = ""
        r["DATA_ZONE_2011"] = ""
    manifest = _build(tmp_path, years={2008: rows})
    assert manifest["summary"]["blocking_failed"] == 0
    saved = output.read_table(tmp_path / "results" / "epc_domestic.parquet")
    assert saved["rrn"].isna().all() and saved["pc_norm"].isna().all() and saved["datazone_2011"].isna().all()
    assert (saved["datazone_2011_status"] == "empty").all()


def test_a_failed_rebuild_keeps_the_last_accepted_build(tmp_path):
    results = tmp_path / "results"
    first = tmp_path / "first"
    first.mkdir()
    registry = make_release(first)
    manifest = pipeline.build(results=results, registry_path=registry, source_root=first / "sources", log=lambda *a: None)
    before = {p.name: p.read_bytes() for p in results.iterdir()}
    assert set(before) == {"epc_domestic.parquet", "epc_domestic.csv.gz", "manifest.json", "BUILD_REPORT.md"}
    # A late failure: the whole-table check on an unknown data zone, after both files are written.
    second = tmp_path / "second"
    second.mkdir()
    rows = default_rows(2008)
    rows[0]["DATA_ZONE"] = "S01999999 (Nowhere)"
    registry2 = make_release(second, years={2008: rows})
    with pytest.raises(BuildStopped):
        pipeline.build(results=results, registry_path=registry2, source_root=second / "sources", log=lambda *a: None)
    after = {p.name: p.read_bytes() for p in results.iterdir()}
    assert after == before
    assert json.loads(after["manifest.json"])["parquet"]["sha256"] == manifest["parquet"]["sha256"]
    # An early failure: the reader stops on the second file after the first part is written.
    third = tmp_path / "third"
    third.mkdir()
    bad = default_rows(2026)
    bad[0]["HISTORIC"] = "TRUE"
    registry3 = make_release(third, years={2008: default_rows(2008), 2026: bad})
    with pytest.raises(BuildStopped):
        pipeline.build(results=results, registry_path=registry3, source_root=third / "sources", log=lambda *a: None)
    assert {p.name: p.read_bytes() for p in results.iterdir()} == before
