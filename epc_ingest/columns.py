"""The table's columns: key and provenance, the 107 published columns, the derived columns.

`python -m epc_ingest.columns` writes output_schema.yaml from published_columns.yaml and the
derived list below, so the schema is a reviewable file and the build reads only the file. The
tests check that the file matches what this module would write.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

PACKAGE = Path(__file__).resolve().parent
PUBLISHED = PACKAGE / "published_columns.yaml"
SCHEMA = PACKAGE / "output_schema.yaml"
SCHEMA_VERSION = "epc_domestic_v1"
TABLE = "epc_domestic"
KEY = ["epc_release", "source_year", "source_row"]

# nvarchar(n) for a published text column: the smallest bucket strictly above the longest value
# measured, so a longer value in a later release fails the schema check, not the load. A column
# that is empty in every row gets the smallest bucket that still reads as a text column.
WIDTH_BUCKETS = (8, 32, 100, 128, 512, 1000, 4000)
EMPTY_COLUMN_WIDTH = 128

# Published columns the derived columns are computed from, by rule name (reader.py).
DATE_COLUMNS = {"INSPECTION_DATE": "inspection_date_parsed", "LODGEMENT_DATE": "lodgement_date_parsed"}
DATETIME_COLUMN = ("CREATED_AT", "created_at_parsed")
INT_COLUMNS = {"CURRENT_ENERGY_EFFICIENCY": "current_energy_efficiency_int",
               "POTENTIAL_ENERGY_EFFICIENCY": "potential_energy_efficiency_int",
               "ENVIRONMENT_IMPACT_CURRENT": "environment_impact_current_int",
               "ENVIRONMENT_IMPACT_POTENTIAL": "environment_impact_potential_int",
               "TOTAL_FLOOR_AREA": "total_floor_area_int"}
DECIMAL_COLUMNS = {"ENERGY_CONSUMPTION_CURRENT": "energy_consumption_current_num",
                   "CO2_EMISSIONS_CURRENT": "co2_emissions_current_num",
                   "CO2_EMISS_CURR_PER_FLOOR_AREA": "co2_emiss_curr_per_floor_area_num"}
DATAZONE_COLUMNS = {"DATA_ZONE": ("datazone_2001", "datazone_2001_status", 2001),
                    "DATA_ZONE_2011": ("datazone_2011", "datazone_2011_status", 2011)}
DATAZONE_STATUSES = ("code", "empty", "not_a_datazone", "unknown_code")

KEY_FIELDS = [
    {"name": "epc_release", "type": "string", "width": 8, "nullable": False, "group": "key",
     "description": "The release of the extract this row came from, 2026Q2. A later release is a new build."},
    {"name": "source_year", "type": "int16", "nullable": False, "group": "key",
     "description": "The annual file the row came from (2008 to 2026), which is the year of CREATED_AT."},
    {"name": "source_row", "type": "int32", "nullable": False, "group": "key",
     "description": "1 for the first data row of the file, which is file row 3 after the two header rows."},
]

DERIVED_FIELDS = [
    {"name": "rrn", "type": "string", "width": 24, "nullable": True, "source": "REPORT_REFERENCE_NUMBER",
     "description": "The report reference number as published where not empty, NULL where empty (9% of rows, mostly 2013 to 2016). Unique where present."},
    {"name": "uprn_sepcr", "type": "int64", "nullable": False, "source": "BUILDING_REFERENCE_NUMBER",
     "description": "The register's own 10-digit property reference, trimmed and as an integer. Not the Gazetteer UPRN. Present in every row."},
    {"name": "uprn_osg", "type": "int64", "nullable": True, "source": "OSG_REFERENCE_NUMBER",
     "description": "The One Scotland Gazetteer UPRN as an integer, NULL where the published cell is empty (4.7% of rows). The only column a join compares; a padded cohort UPRN matches once cast to bigint."},
    {"name": "pc_norm", "type": "string", "width": 8, "nullable": True, "source": "POSTCODE",
     "description": "POSTCODE upper-cased with every space removed, postcode-simd's pc_norm. NULL where the published cell is empty. Nothing repaired."},
    {"name": "datazone_2001", "type": "string", "width": 9, "nullable": True, "source": "DATA_ZONE",
     "description": "The 2001 data zone code when DATA_ZONE starts with S01 and six digits followed by a space or the end, otherwise NULL."},
    {"name": "datazone_2001_status", "type": "string", "width": 16, "nullable": False, "source": "DATA_ZONE",
     "description": "code, empty, not_a_datazone (for 00Q, NA and the like) or unknown_code (well formed, not in the pinned list; the build fails if any)."},
    {"name": "datazone_2011", "type": "string", "width": 9, "nullable": True, "source": "DATA_ZONE_2011",
     "description": "The 2011 data zone code by the same rule, otherwise NULL."},
    {"name": "datazone_2011_status", "type": "string", "width": 16, "nullable": False, "source": "DATA_ZONE_2011",
     "description": "As datazone_2001_status, for the 2011 column."},
    {"name": "inspection_date_parsed", "type": "date", "nullable": False, "source": "INSPECTION_DATE",
     "description": "INSPECTION_DATE (yyyy-mm-dd) as a date. A value that does not parse stops the build."},
    {"name": "lodgement_date_parsed", "type": "date", "nullable": False, "source": "LODGEMENT_DATE",
     "description": "LODGEMENT_DATE (yyyy-mm-dd) as a date. The date a certificate was lodged; the join by date uses it. Outliers (2002, 2006, 2108) are kept as published."},
    {"name": "created_at_parsed", "type": "datetime", "nullable": False, "source": "CREATED_AT",
     "description": "CREATED_AT (dd/mm/yyyy hh:mm:ss) as a timestamp to the second. Its year is the file year."},
    {"name": "historic_flag", "type": "bool", "nullable": False, "source": "HISTORIC",
     "description": "1 where HISTORIC is True (the certificate has been superseded), 0 where False. Any other value stops the build."},
    {"name": "current_energy_efficiency_int", "type": "int32", "nullable": False, "source": "CURRENT_ENERGY_EFFICIENCY",
     "description": "The current energy efficiency rating as an integer. A SAP rating runs 1 to 100; values above 100 are publisher errors kept as published and counted in the build report."},
    {"name": "potential_energy_efficiency_int", "type": "int32", "nullable": False, "source": "POTENTIAL_ENERGY_EFFICIENCY",
     "description": "The potential energy efficiency rating as an integer."},
    {"name": "environment_impact_current_int", "type": "int32", "nullable": False, "source": "ENVIRONMENT_IMPACT_CURRENT",
     "description": "The current environmental impact rating as an integer."},
    {"name": "environment_impact_potential_int", "type": "int32", "nullable": False, "source": "ENVIRONMENT_IMPACT_POTENTIAL",
     "description": "The potential environmental impact rating as an integer."},
    {"name": "total_floor_area_int", "type": "int32", "nullable": False, "source": "TOTAL_FLOOR_AREA",
     "description": "Total floor area in square metres as an integer. 0 in every 2008 and 2009 row."},
    {"name": "energy_consumption_current_num", "type": "decimal", "nullable": False, "source": "ENERGY_CONSUMPTION_CURRENT",
     "description": "Primary energy indicator (kWh per square metre per year) as decimal(19,4)."},
    {"name": "co2_emissions_current_num", "type": "decimal", "nullable": False, "source": "CO2_EMISSIONS_CURRENT",
     "description": "Current emissions (tonnes of CO2 per year) as decimal(19,4)."},
    {"name": "co2_emiss_curr_per_floor_area_num", "type": "decimal", "nullable": False, "source": "CO2_EMISS_CURR_PER_FLOOR_AREA",
     "description": "Current emissions per floor area (kg of CO2 per square metre per year) as decimal(19,4)."},
]


def load_published(path: Path = PUBLISHED) -> list:
    raw = yaml.safe_load(Path(path).read_text())
    if raw.get("version") != 1:
        raise ValueError("Unsupported published-columns version")
    columns = raw["columns"]
    names = [c["name"] for c in columns]
    if len(set(names)) != len(names):
        raise ValueError("a published column name repeats")
    return columns


def width(max_len: int) -> int:
    if max_len == 0:
        return EMPTY_COLUMN_WIDTH
    for bucket in WIDTH_BUCKETS:
        if bucket > max_len:
            return bucket
    raise ValueError(f"a value of {max_len} characters does not fit any width bucket")


def fields(published: list) -> list:
    out = [dict(f) for f in KEY_FIELDS]
    for c in published:
        out.append({"name": c["name"], "type": "string", "width": width(c["max_len"]), "nullable": False,
                    "group": "published", "label": c["label"], "max_len": c["max_len"],
                    "description": f"As published. Publisher's label: {c['label']}."})
    for f in DERIVED_FIELDS:
        d = dict(f)
        d["group"] = "derived"
        out.append(d)
    names = [f["name"] for f in out]
    folded = {}
    for name in names:
        folded.setdefault(name.lower(), []).append(name)
    clashes = {k: v for k, v in folded.items() if len(v) > 1}
    if clashes:
        raise ValueError(f"column names that differ only by case: {clashes}")
    return out


def schema(published: list) -> dict:
    f = fields(published)
    return {"version": SCHEMA_VERSION, "table": TABLE, "key": KEY, "columns": len(f), "fields": f}


def write(published: list | None = None) -> None:
    published = published or load_published()
    text = "# Frozen output schema of epc_domestic. Order, type, width and nullability are the contract.\n" \
           "# Generated by python -m epc_ingest.columns; do not edit by hand.\n" + \
           yaml.safe_dump(schema(published), sort_keys=False, allow_unicode=True, width=120)
    SCHEMA.write_text(text)


def main(argv=None) -> int:
    write()
    print(f"wrote {SCHEMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
