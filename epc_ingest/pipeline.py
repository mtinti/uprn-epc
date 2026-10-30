"""Build the table: verify the pins, read every annual file, check, write, read back, record.

    python -m epc_ingest.pipeline                    # writes results/
    python -m epc_ingest.pipeline --verify-archive   # also hashes the 7z archive and the note first

The files are read one year at a time and written as one row group and one CSV part each, so
the 3.8 million rows are never held in memory at once.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

from . import checks as table_checks
from . import columns as col
from .core import output
from .core import text_output as tx
from .core.checks import BuildStopped, Report
from .core.sources import REGISTRY, ROOT, SOURCE_ROOT, load_registry, sha256, verify
from .reader import read_year, read_zone_list

PACKAGE = Path(__file__).resolve().parent
CONTRACT = PACKAGE / "export_contract.yaml"
DECISIONS = PACKAGE / "decisions.yaml"
RESULTS = ROOT / "results"
TABLE = col.TABLE
# Never printed in the build report, which travels with the code.
WITHHELD_FROM_REPORT = ("ADDRESS1", "ADDRESS2", "ADDRESS3", "POSTCODE")


def build(results: Path = RESULTS, registry_path: Path = REGISTRY, source_root: Path = SOURCE_ROOT,
          verify_archive: bool = False, log=print) -> dict:
    report = Report()
    registry = load_registry(registry_path, source_root)
    verify(registry, report, archive=verify_archive)
    schema = output.load_schema(col.SCHEMA)
    contract = tx.load_contract(CONTRACT)
    published = col.load_published()
    decisions_sha256 = sha256(DECISIONS)
    report.equal("schema.matches_generator", schema["fields"], col.fields(published),
                 detail="output_schema.yaml is what python -m epc_ingest.columns writes")
    report.require()

    zones = {}
    for vintage, spec in registry.datazone_lists.items():
        codes = read_zone_list(registry.root / spec["file"], spec)
        report.equal(f"datazones_{vintage}.count", len(codes), spec["zones"])
        report.equal(f"datazones_{vintage}.distinct", len(set(codes)), len(codes))
        zones[vintage] = set(codes)
    report.require()

    results.mkdir(parents=True, exist_ok=True)
    metadata = output.table_metadata(registry, schema, decisions_sha256)
    parquet = results / f"{TABLE}.parquet"
    csv_path = results / contract["tables"][TABLE]["file"]
    columns = tx.exported_columns(schema, contract, TABLE)
    kinds = {f["name"]: f["type"] for f in schema["fields"]}
    decimal_columns = [c for c in columns if kinds[c] == "decimal"]

    pq_writer = output.ParquetWriter(schema, parquet, metadata)
    csv_writer = tx.CsvWriter(contract, csv_path)
    per_year, samples, total = {}, [], 0
    for member in registry.members:
        year = int(member["year"])
        t0 = dt.datetime.now()
        frame, picked = read_year(registry.root / member["file"], member, published, schema, zones, registry.epc_release, report)
        samples += picked
        pq_writer.write(frame)
        rendered = tx.render(frame, schema, columns, contract)
        csv_writer.write(rendered)
        hashes = tx.row_hashes(rendered, contract)
        year_total = sum(hashes)
        total += year_total
        bad = 0
        for name in decimal_columns:
            for v, text in zip(frame[name], rendered[name]):
                if text != contract["digest"]["null_marker"] and tx.parse_decimal(text) != v:
                    bad += 1
        report.equal(f"{year}.decimal_round_trip", bad, 0, detail="every decimal cell: file text, Decimal, 4-place text, Decimal")
        report.require()
        per_year[str(year)] = {"rows": len(frame), "digest_total": str(year_total)}
        log(f"  {year}: {len(frame):,} rows in {(dt.datetime.now() - t0).seconds}s")
        del frame, rendered, hashes
    parquet_sha = pq_writer.close()
    csv_info = csv_writer.close()
    csv_info["digest"] = tx.digest_record(contract, csv_info["rows"], total)
    csv_info["digest_per_year"] = per_year

    # Read back. Parquet: structure, then each row group rendered again must give the year's
    # digest, and the sampled rows must equal the source cells text for text.
    parquet_info = output.readback_structure(parquet, schema, metadata, report)
    report.equal("readback.parquet.rows", parquet_info["rows"], csv_info["rows"])
    report.equal("readback.parquet.row_groups", parquet_info["row_groups"], len(registry.members))
    report.require()
    sample_differences, sample_cells = 0, 0
    by_key = {(s["source_year"], s["source_row"]): s for s in samples}
    for i, member in enumerate(registry.members):
        year = str(member["year"])
        saved = output.read_table(parquet, row_group=i)
        rendered = tx.render(saved, schema, columns, contract)
        report.equal(f"readback.parquet.{year}.digest", str(sum(tx.row_hashes(rendered, contract))), per_year[year]["digest_total"],
                     detail="the row group rendered again gives the digest recorded while writing")
        years = set(saved["source_year"].tolist())
        report.equal(f"readback.parquet.{year}.one_year_per_row_group", sorted(years), [int(year)])
        for k, row in saved[saved["source_row"].isin([s["source_row"] for s in samples if s["source_year"] == int(year)])].iterrows():
            s = by_key[(int(row["source_year"]), int(row["source_row"]))]
            for name, cell in s["cells"].items():
                sample_cells += 1
                if row[name] != cell:
                    sample_differences += 1
        del saved, rendered
    report.equal("readback.parquet.sampled_rows_equal_source", sample_differences, 0,
                 detail=f"{len(samples)} rows (first, middle, last of each file), {sample_cells:,} published cells compared with the source text")
    report.require()
    tx.readback_csv_digest(csv_path, columns, schema, contract, report, "readback.csv", csv_info["rows"], total)
    report.require()

    observations = table_checks.check_table(parquet, schema, report)
    report.observe("table", observations)
    report.observe("samples", [{"source_year": s["source_year"], "source_row": s["source_row"]} for s in samples])

    manifest = {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "table": TABLE, "epc_release": registry.epc_release,
        "schema_version": schema["version"], "schema_sha256": schema["sha256"],
        "registry_sha256": registry.sha256, "published_columns_sha256": sha256(col.PUBLISHED),
        "contract_sha256": contract["sha256"], "decisions_sha256": decisions_sha256,
        "parquet": dict(parquet_info, sha256=parquet_sha), "csv": csv_info,
        "publisher": registry.publisher, "licence": registry.licence, "attribution": registry.attribution,
        "redistribution": registry.redistribution,
        "sources": {"archive": registry.release["archive"], "note": registry.release["note"],
                    "members": [{"year": m["year"], "file": m["file"], "sha256": m["sha256"], "rows": m["rows"]} for m in registry.members]},
        "datazone_lists": {str(k): {"file": v["file"], "sha256": v["sha256"], "zones": v["zones"]} for k, v in registry.datazone_lists.items()},
        "grain": output.GRAIN,
        "summary": report.summary(), "checks": report.to_records(), "observations": report.observations,
    }
    (results / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (results / "BUILD_REPORT.md").write_text(build_report(manifest, samples, schema))
    return manifest


def build_report(manifest: dict, samples: list, schema: dict) -> str:
    obs = manifest["observations"]["table"]
    lines = [f"# Build report: {manifest['table']}, release {manifest['epc_release']}, {manifest['built_at'][:19]}Z", "",
             f"Schema `{manifest['schema_version']}`. {manifest['parquet']['rows']:,} rows by {manifest['parquet']['columns']} columns in the Parquet, "
             f"{manifest['csv']['columns']} in the CSV (the three address lines withheld).",
             f"CSV `{manifest['csv']['file']}` SHA256 `{manifest['csv']['sha256']}`, digest total `{manifest['csv']['digest']['total']}`.",
             f"Parquet SHA256 `{manifest['parquet']['sha256']}`.", "",
             "## Rows per year", "", "| Year | Rows | HISTORIC True | HISTORIC False | Empty UPRN | Empty RRN | Digest total |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for year, d in manifest["csv"]["digest_per_year"].items():
        h = obs["historic_per_year"][year]
        lines.append(f"| {year} | {d['rows']:,} | {h['True']:,} | {h['False']:,} | {obs['uprn_osg_empty_rows_per_year'].get(year, obs['uprn_osg_empty_rows_per_year'].get(int(year), 0)):,} | "
                     f"{obs['rrn_empty_rows_per_year'].get(year, obs['rrn_empty_rows_per_year'].get(int(year), 0)):,} | `{d['digest_total']}` |")
    lines += ["", "## What the release holds", ""]
    facts = [
        ("Distinct Gazetteer UPRNs (`uprn_osg`)", f"{obs['uprn_osg_distinct']:,}"),
        ("Distinct register numbers (`uprn_sepcr`)", f"{obs['uprn_sepcr_distinct']:,}"),
        ("Rows with no Gazetteer UPRN", f"{obs['uprn_osg_empty_rows']:,}"),
        ("UPRNs by digit count", ", ".join(f"{k}: {v:,}" for k, v in obs["uprn_osg_digits"].items())),
        ("UPRNs with exactly one `HISTORIC = False` certificate", f"{obs['uprn_osg_with_one_current']:,}"),
        ("UPRNs with two or more `HISTORIC = False` certificates (`ambiguous_latest`)", f"{obs['uprn_osg_with_two_or_more_current']:,}"),
        ("UPRNs whose certificates are all `HISTORIC = True` (`no_current_certificate`)", f"{obs['uprn_osg_all_historic']:,}"),
        ("(UPRN, lodgement day) pairs with two or more certificates (`ambiguous_as_of` candidates)", f"{obs['same_uprn_osg_same_lodgement_day_pairs']:,}"),
        ("Rows with an empty RRN", f"{obs['rrn_empty_rows']:,}"),
        ("`datazone_2001_status`", ", ".join(f"{k}: {v:,}" for k, v in obs["datazone_2001_status"].items())),
        ("`datazone_2011_status`", ", ".join(f"{k}: {v:,}" for k, v in obs["datazone_2011_status"].items())),
        ("Distinct 2001 and 2011 data zone codes", f"{obs['datazone_2001_distinct']:,} and {obs['datazone_2011_distinct']:,}"),
        ("Rows with an empty postcode", f"{obs['postcode_empty_rows']:,}"),
        ("Distinct `pc_norm`", f"{obs['pc_norm_distinct']:,}"),
        ("`pc_norm` not 5 to 7 characters", f"{obs['pc_norm_not_5_to_7_chars']:,}"),
        ("Rows with `TOTAL_FLOOR_AREA` 0", f"{obs['total_floor_area_zero_rows']:,} (range {obs['total_floor_area_range']})"),
        ("Rows with a rating above 100", ", ".join(f"{c}: {obs[c + '_over_100']:,}" for c in ("current_energy_efficiency_int", "potential_energy_efficiency_int", "environment_impact_current_int", "environment_impact_potential_int"))),
        ("Rows lodged before inspection", f"{obs['lodgement_before_inspection_rows']:,}"),
        ("Lodgement date range", f"{obs['lodgement_date_range'][0]} to {obs['lodgement_date_range'][1]}; {obs['lodgement_year_outside_2008_2026']:,} rows outside 2008 to 2026"),
        ("Rows with empty `TYPE_OF_ASSESSMENT`", f"{obs['type_of_assessment_empty_rows']:,}"),
        ("Rows with empty `ADDENDUM_TEXT`", f"{obs['addendum_text_empty_rows']:,}"),
        ("Cells with an embedded newline", ", ".join(f"{k}: {v}" for k, v in obs["cells_with_embedded_newline"].items()) or "none"),
    ]
    lines += ["| Fact | Value |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in facts]
    widths = {f["name"]: f["width"] for f in schema["fields"] if f["type"] == "string"}
    lines += ["", "## Longest text per column against its width", "", "| Column | Longest | nvarchar |", "| --- | ---: | ---: |"]
    for name, longest in obs["longest_text_per_column"].items():
        lines.append(f"| `{name}` | {longest} | {widths[name]} |")
    lines += ["", "## Checks", "", f"{manifest['summary']['blocking_passed']} passed, {manifest['summary']['blocking_failed']} failed.", "",
              "| Check | Result | Detail |", "| --- | --- | --- |"]
    for c in manifest["checks"]:
        lines.append(f"| `{c['name']}` | {'pass' if c['passed'] else 'FAIL'} | {str(c['detail'])[:160]} |")
    last = [s for s in samples if s["source_year"] == max(x["source_year"] for x in samples)][0]
    lines += ["", f"## One certificate cell for cell: {last['source_year']} row {last['source_row']}", "",
              "The source text of the pinned file, which the Parquet holds unchanged (checked for the first, middle and last row of every file). "
              "The address lines and the postcode are not printed here.", "", "| Column | Source text |", "| --- | --- |"]
    for name, cell in last["cells"].items():
        shown = "(withheld)" if name in WITHHELD_FROM_REPORT else cell.replace("|", "\\|").replace("\n", "\\n").replace("\r", "\\r")
        lines.append(f"| `{name}` | `{shown}` |" if shown else f"| `{name}` | |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    verify_archive = "--verify-archive" in argv
    try:
        manifest = build(verify_archive=verify_archive)
    except BuildStopped as stop:
        print(f"stopped: {stop}", file=sys.stderr)
        return 1
    print(f"built {manifest['parquet']['rows']:,} rows; {manifest['summary']['blocking_passed']} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
