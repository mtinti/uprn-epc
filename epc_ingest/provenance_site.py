"""Write the column provenance site as Markdown for MkDocs (docs/plans/Column_Provenance_Site_Plan.md).

    python -m epc_ingest.provenance_site [out_dir]      # default build/provenance_docs

One page per column, one per pinned source file, one per decision, one defining the checks, and
index pages. Everything comes from committed metadata through `lineage` and the descriptions
file: the site describes the code at this commit and holds no data value, no address, no
postcode. It never opens the Parquet, the CSV, the manifest or a source file.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

import yaml

from . import columns as col
from .core.sources import load_registry
from .lineage import PACKAGE, effective_decisions, lineage, load_catalogue, load_decisions, load_descriptions

ROOT = PACKAGE.parent
REPO = "https://github.com/mtinti/uprn-epc"
GROUP_TITLE = {"key": "Key and provenance columns", "published": "Published columns, in published order", "derived": "Derived columns"}
REPLACEMENT_NOTE = (" The label is as printed in the file's second header row, where the publisher's export already holds the "
                    "replacement character U+FFFD (shown as \ufffd) in place of a lost ² or £; the publication note prints the intended character.")
TYPE_WORDS = {"string": "text", "int16": "16-bit integer", "int32": "32-bit integer", "int64": "64-bit integer", "bool": "flag",
              "date": "date", "datetime": "timestamp", "decimal": "decimal(19,4)"}


def _version() -> dict:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {"version": project["version"], "commit": commit}


def _slug(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", path).strip("-")


def _anchor(heading: str) -> str:
    """The id python-markdown's toc gives a heading: lower case, punctuation dropped, spaces to hyphens."""
    return re.sub(r"[^\w\s-]", "", heading).strip().lower().replace(" ", "-")


def _sentence(text: str) -> str:
    return text if text.endswith((".", "!", "?", ")", "]")) else text + "."


def _short(sha: str) -> str:
    return sha[:12] + "…"


def _col_link(name: str, prefix: str = "") -> str:
    return f"[`{name}`]({prefix}{name}.md)"


def _description_block(name: str, entry: dict | None, note: dict) -> list:
    if not entry:
        return []
    if entry["attribution"] == "note":
        where = f"page {entry['page']}"
        label = f" under the label *{entry['note_label']}*" if entry.get("note_label") else ""
        shared = f" The note describes `{entry['shared_entry']}` and the two rating columns of the element in one entry." if entry.get("shared_entry") else ""
        alias = f" The note calls this field `{entry['note_name']}`." if entry["note_name"] != name else ""
        scot = " Marked in the note as a Scotland-only field." if entry.get("scotland_only") else ""
        see = f" \"As above\" refers to the entry for {_col_link(entry['see_also'])}." if entry.get("see_also") else ""
        return [f"**Publication note** ({where}{label}; quoted from the Scottish Government's note, SHA256 `{_short(note['sha256'])}`, "
                f"Open Government Licence v3.0): {_sentence(entry['text'])}{shared}{alias}{scot}{see}", ""]
    return [f"**Project description** (written for this build, not from the publication note): {entry['text']}", ""]


def write(out: Path) -> dict:
    """Write every page, then remove any page this run did not write, so a page for a column,
    file or decision that no longer exists does not stay searchable."""
    out = Path(out)
    for sub in ("columns", "sources", "decisions"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    before = set(out.rglob("*.md"))
    counts = _write_pages(out)
    written = {out / p for p in counts.pop("_written")}
    for stale in sorted(before - written):
        stale.unlink()
    return counts


def _write_pages(out: Path) -> dict:
    written = []

    def emit(rel: str, lines: list) -> None:
        path = out / rel
        path.write_text("\n".join(lines).rstrip() + "\n")
        written.append(Path(rel))

    version = _version()
    registry = load_registry()
    catalogue = {e["id"]: e for e in load_catalogue()}
    decisions = load_decisions()
    descriptions = load_descriptions()
    L = lineage()
    by_file, by_decision = defaultdict(set), defaultdict(set)

    # --- one page per column
    for name, r in L.items():
        for i in r["inputs"]:
            if i["kind"] == "pinned_file":
                by_file[i["path"]].add(name)
        for d in r["decisions"]:
            by_decision[d].add(name)
        current, history = effective_decisions(r["decisions"], decisions)
        lines = [f"# `{name}`", "", r["description"], ""]
        lines += _description_block(name, descriptions["columns"].get(name), descriptions["note"])
        width = f"nvarchar({r['width']})" if r["type"] == "string" else ""
        lines += ["| Group | Type | Nullable | In the CSV | SQL Server type |", "| --- | --- | --- | --- | --- |",
                  f"| {r['group']} | {TYPE_WORDS[r['type']]} | {'yes, only in its documented missing case' if r['nullable'] else 'no'} | "
                  f"{'yes' if r['export']['csv'] else 'no'} | `{r['export']['sql_type']}`{' NOT NULL' if r['export']['not_null'] else ''} |", ""]
        lines += ["## Where it comes from", ""]
        if r["group"] == "published":
            m = r["inputs"][0]
            lines += [f"Field {m['position']} of 107 in every annual file of release {registry.epc_release}, machine name `{m['field']}`, "
                      f"publisher's label \"{m['label']}\". The row keeps its file position as `source_row`."
                      + (REPLACEMENT_NOTE if "\ufffd" in m["label"] else ""), "",
                      "| Pinned file | SHA256 | Rows |", "| --- | --- | --- |"]
            for i in r["inputs"]:
                if i["field"] is None:
                    continue
                year = re.search(r"(\d{4})\.csv$", i["path"]).group(1)
                rows = next(mm["rows"] for mm in registry.members if mm["file"] == i["path"])
                lines.append(f"| [`{i['path']}`](../sources/{_slug(i['path'])}.md) ({year}) | `{_short(i['sha256'])}` | {int(rows):,} |")
            arch = r["inputs"][-1]
            lines += ["", f"The annual files were extracted from [`{arch['path']}`](../sources/{_slug(arch['path'])}.md) "
                      f"(SHA256 `{_short(arch['sha256'])}`), which is hashed only under `--verify-archive`.", ""]
        elif r["group"] == "derived":
            lines += ["| Input | Field | Condition | Reaches the row by |", "| --- | --- | --- | --- |"]
            for i in r["inputs"]:
                if i["kind"] == "column":
                    lines.append(f"| this table | {_col_link(i['field'])} | | {i['by']} |")
                else:
                    lines.append(f"| [`{i['path']}`](../sources/{_slug(i['path'])}.md) (pinned, SHA256 `{_short(i['sha256'])}`) | `{i['field']}` | {i['condition']} | {i['by']} |")
            lines.append("")
        else:
            i = r["inputs"][0]
            if i["kind"] == "registry":
                lines += [f"The registry `epc_ingest/sources.yaml`, `{i['field']}`: {registry.epc_release}.", ""]
            else:
                lines += [f"The annual files themselves: which file a row was read from, and where in it. See the pages of the "
                          f"[pinned sources](../sources/index.md).", ""]
        t = r["transformation"]
        lines += ["## What was done to it", "", f"*{t['kind']}*. {t['rule']} (code: `{t['code']}`)", ""]
        lines += ["## How it is checked", "",
                  "What each check tests. Whether a build passed it is in that build's `manifest.json[\"checks\"]`, not here.", ""]
        for cid in r["checks"]:
            e = catalogue[cid]
            cond = f" Runs only under `{e['condition']}`." if e["condition"] else ""
            lines.append(f"- [`{cid}`](../checks.md#{_anchor(cid)}): {e['tests']}. Coverage: {e['coverage']}.{cond}")
        lines.append("")
        lines += ["## Why", ""]
        if current:
            lines += ["In force: " + ", ".join(f"[`{d}`](../decisions/{d}.md)" for d in current) + ".", ""]
        for d in current:
            dec = decisions[d]
            if dec.get("amends") and dec["amends"] in r["decisions"]:
                later = [x for x in current if x != d and decisions[x].get("amends") == dec["amends"] and decisions[x]["date"] > dec["date"]]
                revised = (" Revised again by " + ", ".join(f"[`{x}`](../decisions/{x}.md)" for x in later) + ", which governs where the two differ.") if later else ""
                stands = "What still stood then" if later else "What still stands"
                lines += [f"`{d}` amends [`{dec['amends']}`](../decisions/{dec['amends']}.md). {stands}: {dec['keeps']}{revised}", ""]
        if history:
            lines += ["History: " + ", ".join(f"[`{d}`](../decisions/{d}.md)" for d in history) + ".", ""]
        ex = r["export"]
        lines += ["## In SQL Server", ""]
        bits = [f"Declared `{ex['sql_type']}`{' NOT NULL' if ex['not_null'] else ', NULL in its documented missing case'}."]
        for ix in ex["indexes"]:
            members = "(" + ", ".join(f"`{c}`" for c in ix["columns"]) + ")" + (" INCLUDE (" + ", ".join(f"`{c}`" for c in ix["include"]) + ")" if ix["include"] else "")
            bits.append(f"In `{ix['index']}` as {ix['role']}: {members}." + (f" Serves {ix['serves']}." if ix.get("serves") else ""))
        if ex["joined_on"]:
            bits.append(f"Joins: {ex['joined_on']}.")
        bits.append("Covered by the row digest that the loaded table is checked against." if ex["in_digest"] else "Not in the CSV, so not in the row digest.")
        lines += [" ".join(bits), ""]
        emit(f"columns/{name}.md", lines)

    # --- column index
    lines = ["# Columns", "", f"{len(L)} columns of `{col.TABLE}`: {sum(1 for r in L.values() if r['group'] == 'key')} key, "
             f"{sum(1 for r in L.values() if r['group'] == 'published')} published, {sum(1 for r in L.values() if r['group'] == 'derived')} derived.", ""]
    for group, title in GROUP_TITLE.items():
        lines += [f"## {title}", "", "| Column | Type | Nullable | Description |", "| --- | --- | --- | --- |"]
        for name, r in L.items():
            if r["group"] == group:
                lines.append(f"| {_col_link(name)} | {TYPE_WORDS[r['type']]} | {'yes' if r['nullable'] else 'no'} | {r['description']} |")
        lines.append("")
    emit("columns/index.md", lines)

    # --- sources
    files = []
    for m in registry.members:
        files.append((m["file"], m["sha256"], f"annual file, {int(m['rows']):,} certificates created in {m['year']}", int(m["bytes"])))
    arch, note = registry.release["archive"], registry.release["note"]
    files.append((arch["file"], arch["sha256"], "the download: 19 annual CSV files and the publication note, hashed under --verify-archive", int(arch["bytes"])))
    files.append((note["file"], note["sha256"], "the publisher's note, 17 pages, with the data dictionary the column descriptions quote", int(note["bytes"])))
    for vintage, spec in registry.datazone_lists.items():
        files.append((spec["file"], spec["sha256"], f"the {vintage} data zone reference list, {spec['zones']} zones, pinned in {spec['pinned_in']}", None))
    lines = ["# Pinned sources", "", f"Release {registry.epc_release}, extracted from the register {registry.release['extracted_from_register']}, "
             f"downloaded {registry.release['downloaded']}. Publisher: {registry.publisher}.", "",
             f"Licence: {registry.licence}", "", "| File | SHA256 | What it is | Columns fed |", "| --- | --- | --- | ---: |"]
    for path, sha, what, _ in files:
        lines.append(f"| [`{path}`]({_slug(path)}.md) | `{_short(sha)}` | {what} | {len(by_file.get(path, ()))} |")
    draft = yaml.safe_load((PACKAGE / "sources.yaml").read_text()).get("zenodo_draft")
    lines += ["", f"The archive and the note are held off site in restricted Zenodo deposition {draft} (metadata public, files on request)." if draft else "", ""]
    emit("sources/index.md", lines)
    for path, sha, what, size in files:
        lines = [f"# `{path}`", "", what.capitalize() + ".", "", f"SHA256 `{sha}`" + (f", {size:,} bytes." if size else "."), ""]
        if path.endswith(".pdf"):
            lines += ["The data dictionary of this note is the source of the published columns' descriptions "
                      "(`epc_ingest/column_descriptions.yaml`), quoted with attribution.", ""]
        cols = sorted(by_file.get(path, ()), key=list(L).index)
        if cols:
            lines += [f"## Columns fed ({len(cols)})", ""] + [f"- {_col_link(c, '../columns/')}" for c in cols] + [""]
        emit(f"sources/{_slug(path)}.md", lines)

    # --- decisions
    lines = ["# Decisions", "", "The decision log (`epc_ingest/decisions.yaml`): what was decided, why, and what it governs. "
             "An entry that amends an earlier one says what of the earlier one still stands.", "",
             "| Decision | Date | Status | Amends | Columns governed |", "| --- | --- | --- | --- | ---: |"]
    for d, dec in decisions.items():
        lines.append(f"| [`{d}`]({d}.md) | {dec['date']} | {dec.get('status', 'in_force')} | "
                     f"{('[`' + dec['amends'] + '`](' + dec['amends'] + '.md)') if dec.get('amends') else ''} | {len(by_decision.get(d, ()))} |")
    emit("decisions/index.md", lines + [""])
    for d, dec in decisions.items():
        lines = [f"# `{d}`", "", f"Decided {dec['date']}. Status: {dec.get('status', 'in_force')}.", "",
                 f"**Decision.** {dec['decision']}", "", f"**Why.** {dec['why']}", ""]
        if dec.get("amends"):
            lines += [f"**Amends** [`{dec['amends']}`]({dec['amends']}.md). **Still stands:** {dec['keeps']}", ""]
        amended_by = [x for x, y in decisions.items() if y.get("amends") == d]
        if amended_by:
            lines += ["**Amended by** " + ", ".join(f"[`{x}`]({x}.md)" for x in amended_by) + ".", ""]
        cols = sorted(by_decision.get(d, ()), key=list(L).index)
        if cols:
            lines += [f"## Columns governed ({len(cols)})", ""] + [f"- {_col_link(c, '../columns/')}" for c in cols] + [""]
        emit(f"decisions/{d}.md", lines)

    # --- checks
    lines = ["# Checks", "", "Every check the build can emit, by family (`epc_ingest/check_catalogue.yaml`). Each is blocking: a failure "
             "stops the build and nothing is promoted. A build's manifest records which were emitted and their results; "
             "this page defines them and says how far each reaches.", ""]
    for cid, e in catalogue.items():
        a = e["applies_to"]
        applies = ", ".join(f"`{c}`" for c in a) if isinstance(a, list) and a else ("no column: table-level" if isinstance(a, list) else f"every {a} column" if a != "all" else "every column")
        lines += [f"## {cid}", "", f"Name pattern `{e['pattern']}`. {e['tests'][0].upper() + e['tests'][1:]}.", "",
                  f"Applies to {applies}. Coverage: {e['coverage']}." + (f" Runs only under `{e['condition']}`." if e["condition"] else " Runs in every build."), ""]
    emit("checks.md", lines)

    # --- home
    lines = [f"# {col.TABLE}: column provenance", "",
             f"Where every column of the table `{col.TABLE}` comes from, what was done to it, how it is checked and why. "
             f"Generated from the metadata of [uprn-epc]({REPO}) version {version['version']} at commit `{version['commit']}`.", "",
             "The table holds every certificate of the Scottish Government's extended historic extract of domestic Energy Performance "
             f"Certificates, release {registry.epc_release}, one row per certificate, values exactly as published, with typed copies for "
             "joining a cohort by UPRN and date. The table itself is private; this site holds no value of any row, no address and no postcode.", "",
             f"- [Columns](columns/index.md): {len(L)} pages, one per column.",
             f"- [Pinned sources](sources/index.md): the {len(files)} files the build reads or hashes.",
             f"- [Decisions](decisions/index.md): the {len(decisions)} decisions, in force and history.",
             "- [Checks](checks.md): what every check family tests and how far it reaches.", "",
             f"The data dictionary, the loader, the join queries and the build record are in the [repository]({REPO}). "
             "The source archive is held in a restricted Zenodo record whose metadata is public and whose files are on request.", ""]
    emit("index.md", lines)
    return {"columns": len(L), "sources": len(files), "decisions": len(decisions), "checks": len(catalogue), "_written": written}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]) if argv else ROOT / "build" / "provenance_docs"
    counts = write(out)
    print(f"wrote {out}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
