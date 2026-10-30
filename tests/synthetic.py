"""A synthetic release: a few rows per annual file in the publisher's exact shape (two header
rows, byte order mark, CRLF, 107 fields), plus the two reference lists and a registry that pins
them by hash. Every test that needs source files builds one of these in a temporary folder."""

from __future__ import annotations

import csv
import hashlib
import io
import struct
from pathlib import Path

import yaml

from epc_ingest import columns as col
from epc_ingest.core.sources import PACKAGE

PUBLISHED = col.load_published()
NAMES = [c["name"] for c in PUBLISHED]
LABELS = [c["label"] for c in PUBLISHED]
ZONES_2001 = ["S01000001", "S01000416", "S01006505"]
ZONES_2011 = ["S01006506", "S01006982", "S01013481"]


def make_row(year: int, n: int, **overrides) -> dict:
    """One valid certificate row, every published column filled, then overrides applied."""
    row = {name: "" for name in NAMES}
    row.update({
        "HISTORIC": "False", "BUILDING_REFERENCE_NUMBER": str(1000000000 + n), "OSG_REFERENCE_NUMBER": str(35000000 + n),
        "ADDRESS1": f"{n} TEST STREET ", "ADDRESS2": "", "ADDRESS3": "ALLOA", "POSTCODE": "FK10 1AA",
        "INSPECTION_DATE": f"{year}-03-0{1 + n % 9}", "TYPE_OF_ASSESSMENT": "RdSAP, existing dwelling",
        "LODGEMENT_DATE": f"{year}-03-1{n % 10}", "ENERGY_CONSUMPTION_CURRENT": "250.00", "TOTAL_FLOOR_AREA": "85",
        "3_YR_ENERGY_COST_CURRENT": "2400.1234", "3_YR_ENERGY_SAVINGS_POTENTIAL": "300.0000",
        "CURRENT_ENERGY_EFFICIENCY": "65", "CURRENT_ENERGY_RATING": "D", "POTENTIAL_ENERGY_EFFICIENCY": "80",
        "POTENTIAL_ENERGY_RATING": "C", "ENVIRONMENT_IMPACT_CURRENT": "60", "CURRENT_ENVIRONMENTAL_RATING": "D",
        "ENVIRONMENT_IMPACT_POTENTIAL": "75", "POTENTIAL_ENVIRONMENTAL_RATING": "C",
        "CO2_EMISS_CURR_PER_FLOOR_AREA": "35.50", "IMPROVEMENTS": "Loft insulation|Cavity wall insulation",
        "WALL_DESCRIPTION": "Cavity wall, as built, no insulation (assumed)", "WALL_ENERGY_EFF": "Poor", "WALL_ENV_EFF": "Poor",
        "CO2_EMISSIONS_CURRENT": "3.20", "CO2_EMISSIONS_POTENTIAL": "1.10",
        "DATA_ZONE": "S01000416 (Ythsie)", "DATA_ZONE_2011": "S01006982 (Ythsie - 05)",
        "LOCAL_AUTHORITY_LABEL": "Clackmannanshire", "TENURE": "Owner-occupied", "PROPERTY_TYPE": "House",
        "BUILT_FORM": "Detached", "CREATED_AT": f"0{1 + n % 9}/04/{year} 10:{n % 60:02d}:00",
        "REPORT_REFERENCE_NUMBER": f"{year}-{n:04d}-0000-0000-0001",
    })
    row.update(overrides)
    return row


def default_rows(year: int) -> list:
    """Five rows that between them carry the awkward cells of the real extract: a trailing
    newline inside a quoted cell, a double quote, an empty UPRN, an empty RRN, a superseded
    certificate, junk and empty data zones, a code value in a count column."""
    return [
        make_row(year, 1),
        make_row(year, 2, HISTORIC="True", BUILDING_REFERENCE_NUMBER="1000000002\n", REPORT_REFERENCE_NUMBER=""),
        make_row(year, 3, OSG_REFERENCE_NUMBER="", ADDRESS1='FLAT 1/2 "THE OLD MILL"', DATA_ZONE="00Q", DATA_ZONE_2011="NA"),
        make_row(year, 4, OSG_REFERENCE_NUMBER="906700556768", DATA_ZONE="", DATA_ZONE_2011="", POSTCODE="g12 8qq",
                 LOW_ENERGY_FIXED_LIGHT_COUNT="-1", FLAT_TOP_STOREY="00"),
        make_row(year, 5, HISTORIC="True", CURRENT_ENERGY_EFFICIENCY="21241", TOTAL_FLOOR_AREA="0", IMPROVEMENTS="A, B|C"),
    ]


def write_year_file(path: Path, year: int, rows: list, names: list = None, labels: list = None, raw_bytes: bytes = None) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(names if names is not None else NAMES)
    writer.writerow(labels if labels is not None else LABELS)
    for r in rows:
        writer.writerow([r[n] for n in (names if names is not None else NAMES)] if isinstance(r, dict) else r)
    body = b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
    if raw_bytes is not None:
        body = raw_bytes
    path.write_bytes(body)


def write_dbf(path: Path, codes: list, column: str = "DataZone") -> None:
    """A minimal dBASE III file with one character field."""
    width = 9
    header_length = 32 + 32 + 1
    record_length = 1 + width
    header = bytearray(32)
    header[0] = 0x03
    struct.pack_into("<IHH", header, 4, len(codes), header_length, record_length)
    field = bytearray(32)
    field[0:len(column)] = column.encode("ascii")
    field[11] = ord("C")
    field[16] = width
    body = b"".join(b" " + code.encode("ascii").ljust(width) for code in codes)
    path.write_bytes(bytes(header) + bytes(field) + b"\x0d" + body + b"\x1a")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_release(root: Path, years: dict = None, zones_2001: list = ZONES_2001, zones_2011: list = ZONES_2011,
                 pin_rows: dict = None) -> Path:
    """Write a synthetic source tree under `root` and return the path of its registry.
    `years` maps year to a list of rows (dict or raw list) or to a dict with `rows` and any of
    `names`, `labels`, `raw_bytes` for a deliberately broken file."""
    years = years if years is not None else {2008: default_rows(2008), 2026: default_rows(2026)}
    source = root / "sources"
    (source / "epc_test" / "extracted").mkdir(parents=True)
    (source / "datazones").mkdir()
    members = []
    for year in sorted(years):
        spec = years[year] if isinstance(years[year], dict) else {"rows": years[year]}
        path = source / "epc_test" / "extracted" / f"{year}.csv"
        write_year_file(path, year, spec["rows"], spec.get("names"), spec.get("labels"), spec.get("raw_bytes"))
        rows = (pin_rows or {}).get(year, len(spec["rows"]))
        members.append({"year": year, "file": f"epc_test/extracted/{year}.csv", "sha256": sha256_file(path),
                        "bytes": path.stat().st_size, "rows": rows})
    archive = source / "epc_test" / "archive.7z"
    archive.write_bytes(b"not a real archive")
    note = source / "epc_test" / "publication_note.pdf"
    note.write_bytes(b"%PDF-1.4 test")
    dbf = source / "datazones" / "SG_SIMD_2012.dbf"
    write_dbf(dbf, zones_2001)
    lookup = source / "datazones" / "DataZone2011_lookup.csv"
    lookup.write_text("DZ2011_Code,DZ2011_Name\n" + "".join(f"{c},Zone {c}\n" for c in zones_2011), encoding="cp1252")
    base = yaml.safe_load((PACKAGE / "sources.yaml").read_text())
    registry = dict(base)
    registry["release"] = {"epc_release": "TEST", "extracted_from_register": "2026-09-01", "downloaded": "2026-10-05",
                           "archive": {"file": "epc_test/archive.7z", "sha256": sha256_file(archive), "bytes": archive.stat().st_size},
                           "note": {"file": "epc_test/publication_note.pdf", "sha256": sha256_file(note), "bytes": note.stat().st_size},
                           "members": members}
    registry["datazone_lists"] = {
        2001: dict(base["datazone_lists"][2001], file="datazones/SG_SIMD_2012.dbf", sha256=sha256_file(dbf), zones=len(zones_2001)),
        2011: dict(base["datazone_lists"][2011], file="datazones/DataZone2011_lookup.csv", sha256=sha256_file(lookup), zones=len(zones_2011)),
    }
    path = root / "sources.yaml"
    path.write_text(yaml.safe_dump(registry, sort_keys=False, allow_unicode=True))
    return path
