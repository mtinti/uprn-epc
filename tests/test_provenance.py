"""The column provenance site: every column traced, every reference real, the awkward cases
stated by hand (docs/plans/Column_Provenance_Site_Plan.md). The lineage is derived from the
schema, the registry, the check catalogue and the reader's constants; these tests hold it to
the decision log, the descriptions file and the names the build emits, in a synthetic build run
with and without --verify-archive."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from epc_ingest import columns as col
from epc_ingest import lineage as lin
from epc_ingest import pipeline, provenance_site
from epc_ingest.core.sources import load_registry
from epc_ingest.reader import derive_datazone

from synthetic import make_release

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "epc_ingest"
SCHEMA = yaml.safe_load((PACKAGE / "output_schema.yaml").read_text())["fields"]
NAMES = [f["name"] for f in SCHEMA]
POSTCODE_SHAPE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b")


@pytest.fixture(scope="module")
def L():
    return lin.lineage()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    counts = provenance_site.write(out)
    return out, counts


@pytest.fixture(scope="module")
def emitted(tmp_path_factory):
    """The check names of a synthetic build, plain and with --verify-archive."""
    names = {}
    for flag in (False, True):
        root = tmp_path_factory.mktemp("build")
        registry = make_release(root)
        m = pipeline.build(results=root / "results", registry_path=registry, source_root=root / "sources", verify_archive=flag, log=lambda *a: None)
        names[flag] = [c["name"] for c in m["checks"]]
    return names


# --- coverage --------------------------------------------------------------------------------------

def test_every_column_has_a_lineage_record(L):
    assert list(L) == NAMES and len(L) == 130
    for r in L.values():
        assert r["inputs"] and r["transformation"]["rule"] and r["checks"] and r["decisions"], r["name"]


def test_every_column_has_a_description_with_an_attribution_kind():
    d = lin.load_descriptions()
    assert set(d["columns"]) == set(NAMES)
    for name, e in d["columns"].items():
        assert e["attribution"] in ("note", "project") and e["text"].strip(), name
        if e["attribution"] == "note":
            assert isinstance(e["page"], int) and 7 <= e["page"] <= 17 and e["note_name"], name
        else:
            assert "page" not in e and "note_name" not in e, name
    assert d["review"]["record"] and (ROOT / d["review"]["record"]).is_file()


def test_the_field_the_note_omits_and_the_two_aliases():
    d = lin.load_descriptions()["columns"]
    assert d["DATA_ZONE_2011"]["attribution"] == "project" and "not defined in the publication note" in d["DATA_ZONE_2011"]["text"].lower()
    assert d["DATA_ZONE"]["attribution"] == "note" and d["DATA_ZONE"]["text"] != d["DATA_ZONE_2011"]["text"]
    assert d["ADDRESS3"]["note_name"] == "POST_TOWN"
    assert d["3_YR_ENERGY_SAVINGS_POTENTIAL"]["note_name"] == "3_YR_ENERGY_SAVING_POTENTIAL"
    published = sum(1 for e in d.values() if e["attribution"] == "note")
    assert published == 106
    for name in ("WALL_ENERGY_EFF", "WALL_ENV_EFF"):
        assert d[name]["shared_entry"] == "WALL_DESCRIPTION" and d[name]["text"] == d["WALL_DESCRIPTION"]["text"]
    assert d["ROOF_DESCRIPTION"]["see_also"] == "WALL_DESCRIPTION"


def test_the_note_hash_in_the_descriptions_is_the_pinned_one():
    d = lin.load_descriptions()
    registry = load_registry()
    assert d["note"]["sha256"] == registry.release["note"]["sha256"]
    assert d["note"]["file"] == registry.release["note"]["file"]


# --- references ------------------------------------------------------------------------------------

def test_every_input_reference_is_a_pinned_object_or_a_column(L):
    registry = load_registry()
    pinned = {m["file"]: m["sha256"] for m in registry.members}
    pinned[registry.release["archive"]["file"]] = registry.release["archive"]["sha256"]
    for spec in registry.datazone_lists.values():
        pinned[spec["file"]] = spec["sha256"]
    for r in L.values():
        for i in r["inputs"]:
            if i["kind"] == "pinned_file":
                assert pinned[i["path"]] == i["sha256"], (r["name"], i["path"])
            elif i["kind"] == "column":
                assert i["field"] in L and L[i["field"]]["group"] == "published", (r["name"], i["field"])
            else:
                assert i["kind"] == "registry" and r["name"] == "epc_release"


def test_decisions_parse_and_every_cited_decision_exists_with_a_status(L):
    decisions = lin.load_decisions()
    assert len(decisions) == 13
    for d in decisions.values():
        assert d["status"] in ("in_force", "superseded") and d["date"] and d["decision"] and d["why"], d["id"]
        if d.get("amends"):
            assert d["amends"] in decisions and d["keeps"], d["id"]
    for r in L.values():
        for d in r["decisions"]:
            assert d in decisions, (r["name"], d)


def test_the_effective_policy_for_the_address_columns_and_the_dated_joins(L):
    decisions = lin.load_decisions()
    for name in ("ADDRESS1", "ADDRESS2", "ADDRESS3"):
        current, history = lin.effective_decisions(L[name]["decisions"], decisions)
        assert "address-lines-loaded" in current and "recipe-public-data-private" in history, name
        assert L[name]["export"]["csv"] is True
    current, history = lin.effective_decisions(L["POSTCODE"]["decisions"], decisions)
    assert "recipe-public-data-private" in current          # not amended for the postcode
    for name in ("inspection_date_parsed", "lodgement_date_parsed", "uprn_osg"):
        current, history = lin.effective_decisions(L[name]["decisions"], decisions)
        assert "join-by-inspection-date" in current and "join-latest-lodged-with-ties" not in current, name
    assert L["inspection_date_parsed"]["export"]["joined_on"]
    assert [ix["index"] for ix in L["uprn_osg"]["export"]["indexes"]] == ["IX_epc_domestic_uprn_osg"]


def test_every_index_membership_is_recorded_against_the_import_script(L):
    """The inspection date is the second key of both join indexes, the flag is included in both,
    the SEPCR number in the postcode index, and the three key columns form the primary key: each
    as the import script the loader runs declares it."""
    from epc_ingest import sql_check
    sql = sql_check.render_import()
    for ix in sql_check.JOIN_INDEXES:
        assert sql_check.index_sql("epc_domestic", ix) in sql
    roles = {n: {(m["index"], m["role"]) for m in L[n]["export"]["indexes"]} for n in L}
    assert roles["inspection_date_parsed"] == {("IX_epc_domestic_uprn_osg", "key column 2 of 2"), ("IX_epc_domestic_pc_norm", "key column 2 of 2")}
    assert roles["historic_flag"] == {("IX_epc_domestic_uprn_osg", "included column"), ("IX_epc_domestic_pc_norm", "included column")}
    assert roles["uprn_sepcr"] == {("IX_epc_domestic_pc_norm", "included column")}
    assert roles["pc_norm"] == {("IX_epc_domestic_pc_norm", "key column 1 of 2")}
    for i, k in enumerate(col.KEY, 1):
        assert roles[k] == {("PK_epc_domestic", f"primary key, column {i} of 3")}
    assert roles["CURRENT_ENERGY_RATING"] == set()
    # Every column an index names has the membership, and no other column has one.
    named = set(col.KEY) | {c for ix in sql_check.JOIN_INDEXES for c in ix["key"] + ix["include"]}
    assert {n for n in L if roles[n]} == named


# --- the check catalogue ---------------------------------------------------------------------------

def test_every_cited_check_is_a_catalogue_entry_that_applies_to_the_column(L):
    catalogue = {e["id"]: e for e in lin.load_catalogue()}
    exported = {n for n, r in L.items() if r["export"]["csv"]}
    for r in L.values():
        for cid in r["checks"]:
            e = catalogue[cid]
            field = next(f for f in SCHEMA if f["name"] == r["name"])
            assert lin._applies(e, field, exported), (r["name"], cid)
    # A real check attached to a column it does not guard is wrong.
    rrn_field = next(f for f in SCHEMA if f["name"] == "rrn")
    assert not lin._applies(catalogue["table.uprn_one_to_one"], rrn_field, exported)
    assert "table.rrn_unique" not in L["uprn_osg"]["checks"] and "table.rrn_unique" in L["rrn"]["checks"]


def test_emitted_names_match_the_catalogue_both_ways(emitted):
    catalogue = lin.load_catalogue()
    for flag, names in emitted.items():
        for n in names:
            assert lin.catalogue_entry_for(n, catalogue) is not None, (flag, n)
        hit = {e["id"] for e in catalogue if any(re.search(e["pattern"], n) for n in names)}
        unconditional = {e["id"] for e in catalogue if not e["condition"]}
        conditional = {e["id"] for e in catalogue if e["condition"]}
        assert unconditional <= hit, (flag, unconditional - hit)
        assert (conditional <= hit) is flag, (flag, conditional & hit)


def test_sampled_coverage_and_the_archive_condition_are_stated():
    catalogue = {e["id"]: e for e in lin.load_catalogue()}
    assert "three rows" in catalogue["readback.parquet.sampled_rows_equal_source"]["coverage"]
    assert catalogue["source.archive"]["condition"] == "--verify-archive" and catalogue["source.note"]["condition"] == "--verify-archive"


# --- the data zone columns -------------------------------------------------------------------------

def test_the_four_zone_columns_name_their_list_and_membership_decides_the_status(L):
    registry = load_registry()
    for source, (code_col, status_col, vintage) in col.DATAZONE_COLUMNS.items():
        for name in (code_col, status_col):
            lists = [i for i in L[name]["inputs"] if i["kind"] == "pinned_file"]
            assert len(lists) == 1 and lists[0]["path"] == registry.datazone_lists[vintage]["file"], name
            assert [i["field"] for i in L[name]["inputs"] if i["kind"] == "column"] == [source]
    assert derive_datazone("S01006506 Somewhere", {"S01006506"}) == ("S01006506", "code")
    assert derive_datazone("S01006506 Somewhere", {"S01000001"}) == ("S01006506", "unknown_code")


# --- the site --------------------------------------------------------------------------------------

def test_the_site_has_a_page_per_column_and_every_link_resolves(site):
    out, counts = site
    assert counts["columns"] == 130 and counts["decisions"] == 13
    assert {p.stem for p in (out / "columns").glob("*.md")} - {"index"} == set(NAMES)
    for page in out.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+\.md)(?:#[^)]*)?\)", page.read_text()):
            if target.startswith(("http://", "https://")):
                continue
            assert (page.parent / target).resolve().is_file(), (page.relative_to(out), target)


def test_a_page_never_claims_a_check_passed(site):
    out, _ = site
    text = (out / "columns" / "uprn_osg.md").read_text()
    checks = text.split("## How it is checked")[1].split("## Why")[0]
    assert 'manifest.json["checks"]' in checks
    assert not re.search(r"\b(passed|passes)\b", checks.split("\n", 3)[3])


def test_the_address_page_shows_the_policy_in_force_before_its_history(site):
    out, _ = site
    text = (out / "columns" / "ADDRESS1.md").read_text()
    why = text.split("## Why")[1].split("## In SQL Server")[0]
    hist = why.index("History:")
    assert why.index("address-lines-loaded") < hist and "recipe-public-data-private" in why[hist:]
    assert "What still stands" in why
    assert "| yes |" in text          # in the CSV


def test_the_dated_join_pages_state_one_tie_policy(site):
    """Two in-force decisions amend the same earlier one; the page must not present the earlier
    tie rule as standing beside the decision that revised it (review of 31 October 2026)."""
    out, _ = site
    for name in ("uprn_osg", "lodgement_date_parsed", "inspection_date_parsed", "historic_flag"):
        why = (out / "columns" / f"{name}.md").read_text().split("## Why")[1].split("## In SQL Server")[0]
        assert "tie-prefers-current-then-latest-lodged" in why.split("History")[0], name
        for sentence in why.split("\n"):
            if "What still stands" in sentence:            # the latest amendment of its target: its text is the policy
                assert sentence.startswith("`tie-prefers-current-then-latest-lodged`"), (name, sentence)
            if "What still stood then" in sentence:        # an earlier amendment: must point at the later one
                assert "Revised again by" in sentence and "tie-prefers-current-then-latest-lodged" in sentence, (name, sentence)


def test_no_page_holds_a_postcode_shape_or_an_address_value(site):
    out, _ = site
    for page in out.rglob("*.md"):
        text = page.read_text()
        assert not POSTCODE_SHAPE.search(text), page.name
        assert "TEST STREET" not in text and "ALLOA" not in text, page.name


def test_note_text_is_labelled_as_the_notes_wherever_it_appears(site):
    out, _ = site
    d = lin.load_descriptions()["columns"]
    for name, e in d.items():
        text = (out / "columns" / f"{name}.md").read_text()
        if e["attribution"] == "note":
            assert "**Publication note**" in text and e["text"] in text, name
        else:
            assert "**Project description**" in text and "**Publication note**" not in text, name
    assert "`POST_TOWN`" in (out / "columns" / "ADDRESS3.md").read_text()


def test_the_inspection_date_page_names_both_indexes_and_a_mangled_label_is_explained(site):
    out, _ = site
    text = (out / "columns" / "inspection_date_parsed.md").read_text().split("## In SQL Server")[1]
    assert "IX_epc_domestic_uprn_osg" in text and "IX_epc_domestic_pc_norm" in text and "key column 2 of 2" in text
    label = (out / "columns" / "TOTAL_FLOOR_AREA.md").read_text()
    assert "\ufffd" in label and "U+FFFD" in label and "publication note prints the intended character" in label
    assert "U+FFFD" not in (out / "columns" / "TENURE.md").read_text()


def test_regeneration_removes_pages_no_longer_written(tmp_path):
    provenance_site.write(tmp_path)
    stale = [tmp_path / "columns" / "gone.md", tmp_path / "decisions" / "gone.md"]
    for p in stale:
        p.write_text("# gone")
    provenance_site.write(tmp_path)
    assert not any(p.exists() for p in stale) and (tmp_path / "columns" / "uprn_osg.md").is_file()


def test_the_generator_and_the_lineage_read_metadata_only():
    """Neither module may open the Parquet, the CSV, the manifest or a source file."""
    for module in ("lineage.py", "provenance_site.py"):
        text = (PACKAGE / module).read_text()
        for forbidden in ("read_parquet", "\"manifest.json\"", "results/", "duckdb", "pyarrow", ".csv.gz", "from .reader", "import pandas", "open("):
            assert forbidden not in text, (module, forbidden)


def test_the_docs_extra_declares_what_the_site_needs():
    import tomllib
    docs = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["optional-dependencies"]["docs"]
    assert {d.split("==")[0] for d in docs} >= {"mkdocs", "mkdocs-material", "pypdf"}
