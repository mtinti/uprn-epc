"""The checks on the whole table, run over the written Parquet with DuckDB, and the counts the
build report states. Blocking: the key is unique; a present RRN is unique across the release;
the two property numbers are one to one; no data zone code is well formed but unknown. Everything
else is an observation."""

from __future__ import annotations

from pathlib import Path

import duckdb

from .core.checks import Report


def _one(con, sql: str):
    return con.execute(sql).fetchone()[0]


def check_table(parquet: Path, schema: dict, report: Report) -> dict:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW t AS SELECT * FROM read_parquet('{Path(parquet).as_posix()}')")
    key = ", ".join(schema["key"])
    report.equal("table.rows", _one(con, "SELECT COUNT(*) FROM t"), _one(con, f"SELECT COUNT(*) FROM (SELECT DISTINCT {key} FROM t)"),
                 detail="key unique")
    present = _one(con, "SELECT COUNT(*) FROM t WHERE rrn IS NOT NULL")
    report.equal("table.rrn_unique", present - _one(con, "SELECT COUNT(DISTINCT rrn) FROM t WHERE rrn IS NOT NULL"), 0,
                 detail=f"{present:,} present RRNs, none repeated across the release")
    many_sepcr = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_osg FROM t WHERE uprn_osg IS NOT NULL GROUP BY uprn_osg HAVING COUNT(DISTINCT uprn_sepcr) > 1)")
    many_osg = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_sepcr FROM t WHERE uprn_osg IS NOT NULL GROUP BY uprn_sepcr HAVING COUNT(DISTINCT uprn_osg) > 1)")
    report.equal("table.uprn_one_to_one", {"uprn_osg_with_many_sepcr": many_sepcr, "uprn_sepcr_with_many_osg": many_osg},
                 {"uprn_osg_with_many_sepcr": 0, "uprn_sepcr_with_many_osg": 0},
                 detail="where both are present, each Gazetteer UPRN has one register number and the reverse")
    for status_col in ("datazone_2001_status", "datazone_2011_status"):
        report.equal(f"table.{status_col}.no_unknown_code", _one(con, f"SELECT COUNT(*) FROM t WHERE {status_col} = 'unknown_code'"), 0,
                     detail="every well formed code is in the pinned list")
    nulls = {f["name"]: _one(con, f'SELECT COUNT(*) FROM t WHERE "{f["name"]}" IS NULL') for f in schema["fields"] if not f["nullable"]}
    report.equal("table.required_nonnull", {k: v for k, v in nulls.items() if v}, {})
    report.require()

    obs = {}
    obs["rows_per_year"] = dict(con.execute("SELECT source_year, COUNT(*) FROM t GROUP BY 1 ORDER BY 1").fetchall())
    obs["historic_per_year"] = {str(y): {"True": t, "False": f} for y, t, f in con.execute(
        "SELECT source_year, SUM(CASE WHEN historic_flag THEN 1 ELSE 0 END), SUM(CASE WHEN historic_flag THEN 0 ELSE 1 END) FROM t GROUP BY 1 ORDER BY 1").fetchall()}
    obs["uprn_osg_empty_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE uprn_osg IS NULL")
    obs["uprn_osg_empty_rows_per_year"] = dict(con.execute("SELECT source_year, COUNT(*) FROM t WHERE uprn_osg IS NULL GROUP BY 1 ORDER BY 1").fetchall())
    obs["uprn_osg_distinct"] = _one(con, "SELECT COUNT(DISTINCT uprn_osg) FROM t")
    obs["uprn_sepcr_distinct"] = _one(con, "SELECT COUNT(DISTINCT uprn_sepcr) FROM t")
    obs["uprn_osg_digits"] = dict(con.execute("SELECT LENGTH(CAST(uprn_osg AS VARCHAR)), COUNT(DISTINCT uprn_osg) FROM t WHERE uprn_osg IS NOT NULL GROUP BY 1 ORDER BY 1").fetchall())
    obs["uprn_osg_with_two_or_more_current"] = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_osg FROM t WHERE uprn_osg IS NOT NULL AND NOT historic_flag GROUP BY 1 HAVING COUNT(*) > 1)")
    obs["uprn_osg_with_one_current"] = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_osg FROM t WHERE uprn_osg IS NOT NULL AND NOT historic_flag GROUP BY 1 HAVING COUNT(*) = 1)")
    obs["uprn_osg_all_historic"] = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_osg FROM t WHERE uprn_osg IS NOT NULL GROUP BY 1 HAVING SUM(CASE WHEN historic_flag THEN 0 ELSE 1 END) = 0)")
    obs["uprn_sepcr_with_two_or_more_current"] = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_sepcr FROM t WHERE NOT historic_flag GROUP BY 1 HAVING COUNT(*) > 1)")
    obs["same_uprn_osg_same_lodgement_day_pairs"] = _one(con, "SELECT COUNT(*) FROM (SELECT uprn_osg, lodgement_date_parsed FROM t WHERE uprn_osg IS NOT NULL GROUP BY 1, 2 HAVING COUNT(*) > 1)")
    obs["rrn_empty_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE rrn IS NULL")
    obs["rrn_empty_rows_per_year"] = dict(con.execute("SELECT source_year, COUNT(*) FROM t WHERE rrn IS NULL GROUP BY 1 ORDER BY 1").fetchall())
    for status_col in ("datazone_2001_status", "datazone_2011_status"):
        obs[status_col] = dict(con.execute(f"SELECT {status_col}, COUNT(*) FROM t GROUP BY 1 ORDER BY 1").fetchall())
    obs["datazone_2001_distinct"] = _one(con, "SELECT COUNT(DISTINCT datazone_2001) FROM t")
    obs["datazone_2011_distinct"] = _one(con, "SELECT COUNT(DISTINCT datazone_2011) FROM t")
    obs["postcode_empty_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE pc_norm IS NULL")
    obs["pc_norm_distinct"] = _one(con, "SELECT COUNT(DISTINCT pc_norm) FROM t")
    obs["pc_norm_not_5_to_7_chars"] = _one(con, "SELECT COUNT(*) FROM t WHERE pc_norm IS NOT NULL AND LENGTH(pc_norm) NOT BETWEEN 5 AND 7")
    obs["total_floor_area_zero_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE total_floor_area_int = 0")
    obs["total_floor_area_range"] = list(con.execute("SELECT MIN(total_floor_area_int), MAX(total_floor_area_int) FROM t").fetchone())
    for c in ("current_energy_efficiency_int", "potential_energy_efficiency_int", "environment_impact_current_int", "environment_impact_potential_int"):
        obs[f"{c}_over_100"] = _one(con, f"SELECT COUNT(*) FROM t WHERE {c} > 100")
        obs[f"{c}_range"] = list(con.execute(f"SELECT MIN({c}), MAX({c}) FROM t").fetchone())
    obs["lodgement_before_inspection_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE lodgement_date_parsed < inspection_date_parsed")
    obs["lodgement_date_range"] = [str(v) for v in con.execute("SELECT MIN(lodgement_date_parsed), MAX(lodgement_date_parsed) FROM t").fetchone()]
    obs["lodgement_year_outside_2008_2026"] = _one(con, "SELECT COUNT(*) FROM t WHERE EXTRACT(year FROM lodgement_date_parsed) NOT BETWEEN 2008 AND 2026")
    obs["type_of_assessment_empty_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE TYPE_OF_ASSESSMENT = ''")
    obs["addendum_text_empty_rows"] = _one(con, "SELECT COUNT(*) FROM t WHERE ADDENDUM_TEXT = ''")
    obs["cells_with_embedded_newline"] = {c: n for c, n in ((f["name"], _one(con, f'SELECT COUNT(*) FROM t WHERE "{f["name"]}" LIKE \'%\' || chr(10) || \'%\'')) for f in schema["fields"] if f.get("group") == "published") if n}
    obs["longest_text_per_column"] = {f["name"]: _one(con, f'SELECT MAX(LENGTH("{f["name"]}")) FROM t') for f in schema["fields"] if f["type"] == "string"}
    con.close()
    return obs
