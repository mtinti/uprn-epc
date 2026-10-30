"""A fixture release for running the upload notebook against SQL Server through pyodbc: the
default awkward rows of every test, plus the cases the notebook review of 30 October 2026 asked
for. Writes the delivery folder (CSV, two SQL scripts, the notebook built from the fixture's manifest).

    python loader/notebook_probe/build_fixture.py <scratch folder>
"""
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from synthetic import default_rows, make_release, make_row
from epc_ingest import pipeline

HERE = Path(sys.argv[1]).resolve()   # a scratch folder: work/, delivery/ and fixture_manifest.json are written under it
HERE.mkdir(parents=True, exist_ok=True)
rows_2010 = default_rows(2010)
rows_2024 = default_rows(2024) + [
    # Non-ASCII in several columns: accents, a no-break space, curly quotes, the euro sign, an em dash.
    make_row(2024, 6, ADDRESS3="Càfé – Àlloa", IMPROVEMENTS="Loft insulation ‘top-up’ €500|Draught-proofing ü",
             LOCAL_AUTHORITY_LABEL="Ñorth Ayrshire", MAINHEAT_DESCRIPTION="Boiler and radiators, mains gas – 90 % efficient"),
    # Every wide column one short of its width: the row is far over 8,000 characters.
    make_row(2024, 7, IMPROVEMENTS="I" * 3999, PHOTO_SUPPLY="P" * 999, WALL_DESCRIPTION="W" * 511, ROOF_DESCRIPTION="R" * 511,
             FLOOR_DESCRIPTION="F" * 511, MAINHEAT_DESCRIPTION="M" * 511, MAINHEATCONT_DESCRIPTION="C" * 511,
             HOTWATER_DESCRIPTION="H" * 511, ALTERNATIVE_IMPROVEMENTS="A" * 511, LZC_ENERGY_SOURCES="L" * 511),
    # Large and negative decimals at the 4-decimal edge, a far date, a small-hours timestamp, zero floor area.
    make_row(2024, 8, ENERGY_CONSUMPTION_CURRENT="123456789012345.6789", CO2_EMISSIONS_CURRENT="-0.0001",
             CO2_EMISS_CURR_PER_FLOOR_AREA="0", LODGEMENT_DATE="2108-12-13", INSPECTION_DATE="2002-02-03",
             CREATED_AT="01/01/2024 00:00:00", TOTAL_FLOOR_AREA="0", CURRENT_ENERGY_EFFICIENCY="21241"),
    # One current certificate and nothing else for this UPRN: the dwelling step 7 picks.
    make_row(2024, 9, OSG_REFERENCE_NUMBER="35000099", BUILDING_REFERENCE_NUMBER="1000000099"),
    # A twelve-digit UPRN at the top of the Gazetteer range.
    make_row(2024, 10, OSG_REFERENCE_NUMBER="999999999999", BUILDING_REFERENCE_NUMBER="1000000100"),
]
work = HERE / "work"
shutil.rmtree(work, ignore_errors=True); work.mkdir()
registry = make_release(work, years={2010: rows_2010, 2024: rows_2024})
manifest = pipeline.build(results=work / "results", registry_path=registry, source_root=work / "sources", log=lambda *a: None)
assert manifest["summary"]["blocking_failed"] == 0, manifest["summary"]
print("fixture rows", manifest["csv"]["rows"], "digest", manifest["csv"]["digest"]["total"])
delivery = HERE / "delivery"
shutil.rmtree(delivery, ignore_errors=True); delivery.mkdir()
shutil.copy(work / "results" / "epc_domestic.csv.gz", delivery)
shutil.copy(work / "results" / "manifest.json", HERE / "fixture_manifest.json")
for name in ("import_csv.sql", "check_loaded_digest.sql"):
    shutil.copy(ROOT / "docs" / "sql" / name, delivery)
subprocess.run([sys.executable, str(ROOT / "loader" / "make_notebook.py"), str(work / "results"), str(delivery / "upload_epc.ipynb")], check=True)
