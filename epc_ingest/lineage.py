"""One provenance record per column: where it comes from, what was done to it, which checks guard
it, which decisions govern it, and how it leaves the build. Derived from the schema, the published
column list, the registry, the export contract, the check catalogue and the reader's own
constants, never typed by hand (docs/plans/Column_Provenance_Site_Plan.md, section 2).

    python -m epc_ingest.lineage [column]     # print one record, or every column's inputs
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from . import columns as col
from .core import text_output
from .core.sources import load_registry
from .sql_check import JOIN_INDEXES, declared_type

PACKAGE = Path(__file__).resolve().parent
CATALOGUE = PACKAGE / "check_catalogue.yaml"
CONTRACT = PACKAGE / "export_contract.yaml"
DECISIONS = PACKAGE / "decisions.yaml"
DESCRIPTIONS = PACKAGE / "column_descriptions.yaml"

# How each derived column is computed: the published column read, the rule in words, the code.
RULES = {
    "rrn": ("REPORT_REFERENCE_NUMBER", "the published text where it is not empty, NULL where it is", "epc_ingest/reader.py: read_year"),
    "uprn_sepcr": ("BUILDING_REFERENCE_NUMBER", "trimmed and cast to a 64-bit integer; a value that is not an integer stops the build", "epc_ingest/reader.py: _integer"),
    "uprn_osg": ("OSG_REFERENCE_NUMBER", "trimmed and cast to a 64-bit integer, NULL where the published cell is empty; a non-empty value that is not an integer stops the build", "epc_ingest/reader.py: _integer"),
    "pc_norm": ("POSTCODE", "upper-cased with every space removed, NULL where empty; nothing repaired", "epc_ingest/reader.py: norm_postcode"),
    "inspection_date_parsed": ("INSPECTION_DATE", "parsed as yyyy-mm-dd; a value that does not parse stops the build", "epc_ingest/core/text_output.py: parse_date"),
    "lodgement_date_parsed": ("LODGEMENT_DATE", "parsed as yyyy-mm-dd; a value that does not parse stops the build", "epc_ingest/core/text_output.py: parse_date"),
    "created_at_parsed": ("CREATED_AT", "parsed as dd/mm/yyyy hh:mm:ss; a value that does not parse stops the build", "epc_ingest/core/text_output.py: parse_datetime"),
    "historic_flag": ("HISTORIC", "True to 1 and False to 0, exactly those two spellings; anything else stops the build", "epc_ingest/reader.py: HISTORIC_VALUES"),
}
for _src, _tgt in col.INT_COLUMNS.items():
    RULES[_tgt] = (_src, "cast to a 32-bit integer; a value that is not an integer stops the build", "epc_ingest/reader.py: _integer")
for _src, _tgt in col.DECIMAL_COLUMNS.items():
    RULES[_tgt] = (_src, "parsed as a decimal that fits decimal(19,4) and renders back to the same 4-place text; otherwise the build stops", "epc_ingest/reader.py: _decimal")
for _src, (_code, _status, _vintage) in col.DATAZONE_COLUMNS.items():
    RULES[_code] = (_src, f"the leading S01 and six digits when followed by a space or the end of the text, otherwise NULL; checked against the pinned {_vintage} data zone list", "epc_ingest/reader.py: derive_datazone")
    RULES[_status] = (_src, f"code when the text starts with a well-formed code that is in the pinned {_vintage} list, unknown_code when well formed but not in it (which stops the build), empty when blank, not_a_datazone otherwise", "epc_ingest/reader.py: derive_datazone")
KEY_RULES = {
    "epc_release": "the registry's release identifier, the same on every row of a build",
    "source_year": "the year of the annual file the row was read from",
    "source_row": "the row's position in its file, 1 for the first data row (file row 3, after the two header rows)",
}
# Which decisions govern which columns, beyond the ones every column of a group shares.
DECISIONS_BY_COLUMN = {
    "source_year": ["file-year-is-created-at"],
    "uprn_osg": ["uprn-as-integer", "join-latest-lodged-with-ties", "join-by-inspection-date", "tie-prefers-current-then-latest-lodged"],
    "uprn_sepcr": ["uprn-as-integer"],
    "pc_norm": ["join-by-inspection-date"],
    "inspection_date_parsed": ["join-by-inspection-date", "tie-prefers-current-then-latest-lodged"],
    "lodgement_date_parsed": ["join-latest-lodged-with-ties", "join-by-inspection-date"],
    "historic_flag": ["join-latest-lodged-with-ties", "tie-prefers-current-then-latest-lodged"],
    "created_at_parsed": ["file-year-is-created-at", "tie-prefers-current-then-latest-lodged"],
    "ADDRESS1": ["recipe-public-data-private", "address-lines-loaded"],
    "ADDRESS2": ["recipe-public-data-private", "address-lines-loaded"],
    "ADDRESS3": ["recipe-public-data-private", "address-lines-loaded"],
    "POSTCODE": ["recipe-public-data-private"],
}
for _code, _status, _ in col.DATAZONE_COLUMNS.values():
    DECISIONS_BY_COLUMN[_code] = ["datazone-lists"]
    DECISIONS_BY_COLUMN[_status] = ["datazone-lists"]
GROUP_DECISIONS = {"key": ["one-table-per-certificate"],
                   "published": ["values-as-published", "derived-names-and-nullability", "bounded-widths-max-in-digest", "bulk-insert-codepage-utf8"],
                   "derived": ["derived-names-and-nullability"]}


def index_memberships(name: str) -> list:
    """Every index of the table the column takes part in, with its role: the primary key and
    the join indexes of sql_check.JOIN_INDEXES, the one definition the import script renders."""
    out = []
    if name in col.KEY:
        out.append({"index": f"PK_{col.TABLE}", "role": f"primary key, column {col.KEY.index(name) + 1} of {len(col.KEY)}",
                    "columns": list(col.KEY), "include": []})
    for ix in JOIN_INDEXES:
        full = f"IX_{col.TABLE}_{ix['suffix']}"
        if name in ix["key"]:
            out.append({"index": full, "role": f"key column {ix['key'].index(name) + 1} of {len(ix['key'])}", "columns": ix["key"], "include": ix["include"], "serves": ix["serves"]})
        elif name in ix["include"]:
            out.append({"index": full, "role": "included column", "columns": ix["key"], "include": ix["include"], "serves": ix["serves"]})
    return out
JOINED_ON = {"uprn_osg": "join_by_uprn.sql and join_latest_by_uprn.sql compare it to the cohort's UPRN",
             "pc_norm": "join_by_postcode.sql compares it to the cohort's normalised postcode",
             "inspection_date_parsed": "the dated joins rank certificates by it and keep those on or before the cohort date",
             "uprn_sepcr": "join_by_postcode.sql counts dwellings by it",
             "historic_flag": "join_latest_by_uprn.sql chooses the HISTORIC = False certificate without a date; the dated joins prefer it when two certificates share the latest eligible inspection day",
             "created_at_parsed": "the dated joins prefer the later register lodgement when a same-day pair has no single current certificate"}


def load_catalogue(path: Path = CATALOGUE) -> list:
    raw = yaml.safe_load(Path(path).read_text())
    if raw.get("version") != 1:
        raise ValueError(f"Unsupported check catalogue version {raw.get('version')!r}")
    return raw["checks"]


def load_decisions(path: Path = DECISIONS) -> dict:
    raw = yaml.safe_load(Path(path).read_text())
    return {d["id"]: d for d in raw["decisions"]}


def load_descriptions(path: Path = DESCRIPTIONS) -> dict:
    raw = yaml.safe_load(Path(path).read_text())
    return {"note": raw["note"], "review": raw["review"], "columns": {e["name"]: e for e in raw["columns"]}}


def catalogue_entry_for(name: str, catalogue: list) -> dict | None:
    for entry in catalogue:
        if re.search(entry["pattern"], name):
            return entry
    return None


def _applies(entry: dict, field: dict, exported: set) -> bool:
    a = entry["applies_to"]
    if isinstance(a, list):
        return field["name"] in a
    return {"all": True, "published": field["group"] == "published", "derived": field["group"] == "derived",
            "key": field["group"] == "key", "string": field["type"] == "string", "nonnull": not field["nullable"],
            "exported": field["name"] in exported}[a]


def lineage(schema_path: Path = col.SCHEMA, registry_path=None, catalogue_path: Path = CATALOGUE,
            contract_path: Path = CONTRACT) -> dict:
    """{column name: record}. Reads committed metadata only: never a source file, the Parquet,
    the CSV or the manifest."""
    schema = yaml.safe_load(Path(schema_path).read_text())
    registry = load_registry(registry_path) if registry_path else load_registry()
    catalogue = load_catalogue(catalogue_path)
    contract = text_output.load_contract(contract_path)
    exported = set(text_output.exported_columns(schema, contract, col.TABLE))
    published = {c["name"]: c for c in col.load_published()}
    position = {name: i + 1 for i, name in enumerate(published)}
    members = [{"kind": "pinned_file", "path": m["file"], "sha256": m["sha256"], "year": int(m["year"]), "rows": int(m["rows"])}
               for m in registry.members]
    archive = registry.release["archive"]
    out = {}
    for f in schema["fields"]:
        name, group = f["name"], f["group"]
        inputs, transformation = [], {}
        if group == "published":
            inputs = [{"kind": "pinned_file", "path": m["path"], "sha256": m["sha256"], "field": name,
                       "label": published[name]["label"], "position": position[name],
                       "condition": f"rows of the {m['year']} file", "by": "file position: the row's source_row"} for m in members]
            inputs.append({"kind": "pinned_file", "path": archive["file"], "sha256": archive["sha256"], "field": None,
                           "condition": "the archive the annual files were extracted from; hashed only under --verify-archive", "by": None})
            transformation = {"kind": "copied", "rule": "the cell's text exactly as published, trailing spaces and embedded newlines included; the empty string where the cell is empty",
                              "code": "epc_ingest/reader.py: read_year"}
        elif group == "derived":
            src, rule, code = RULES[name]
            inputs = [{"kind": "column", "field": src, "condition": None, "by": "the same row"}]
            for s, (c, st, vintage) in col.DATAZONE_COLUMNS.items():
                if name in (c, st):
                    spec = registry.datazone_lists[vintage]
                    inputs.append({"kind": "pinned_file", "path": spec["file"], "sha256": spec["sha256"], "field": spec["code_column"],
                                   "condition": f"the {vintage} data zone reference list, {spec['zones']} zones", "by": "membership of the parsed code"})
            transformation = {"kind": "derived", "rule": rule, "code": code}
        else:
            inputs = [{"kind": "registry", "field": "release.epc_release", "condition": None, "by": None}] if name == "epc_release" else \
                     [{"kind": "pinned_file", "path": m["path"], "sha256": m["sha256"], "field": None, "condition": f"the {m['year']} file", "by": "file position"} for m in members]
            transformation = {"kind": "assigned", "rule": KEY_RULES[name], "code": "epc_ingest/reader.py: read_year"}
        checks = [e["id"] for e in catalogue if _applies(e, f, exported)]
        decisions = list(dict.fromkeys(GROUP_DECISIONS[group] + DECISIONS_BY_COLUMN.get(name, [])))
        out[name] = {"name": name, "group": group, "type": f["type"], "width": f.get("width"), "nullable": bool(f["nullable"]),
                     "description": f["description"], "inputs": inputs, "transformation": transformation,
                     "checks": checks, "decisions": decisions,
                     "export": {"csv": name in exported, "sql_type": declared_type(f), "not_null": not f["nullable"],
                                "indexes": index_memberships(name),
                                "joined_on": JOINED_ON.get(name), "in_digest": name in exported}}
    return out


def effective_decisions(ids: list, decisions: dict) -> tuple:
    """Split a column's decision ids into those in force and the history behind them, so a page
    shows the policy that governs the column before the entries it revised."""
    in_force = [i for i in ids if decisions[i].get("status", "in_force") == "in_force"]
    amended = {decisions[i]["amends"] for i in ids if decisions[i].get("amends")}
    current = [i for i in in_force if i not in amended]
    history = [i for i in ids if i not in current]
    return current, history


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    L = lineage()
    if argv:
        print(json.dumps(L[argv[0]], indent=1, default=str))
    else:
        for name, r in L.items():
            print(f"{name}: {r['group']}, {len(r['inputs'])} inputs, {len(r['checks'])} checks, decisions {r['decisions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
