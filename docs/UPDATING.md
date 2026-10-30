# Taking a new quarterly release

The Scottish Government overwrites the same download URL every quarter. A new release is a
new build with a new `epc_release`, never an update of the old table.

1. Download the archive into a new folder `data/sources/epc_<release>/` with a `SOURCES.md`
   like the one for 2026Q2; hash the archive and the note; extract the annual files into
   `extracted/`; hash each.
2. Profile the files with `tools/profile_sources.py` and `tools/profile_columns.py` (the
   scripts of the 2026Q2 profile, kept outside the package). Compare with
   `docs/columns_2026-10-29.json`: a new column, a changed label, a longer value or a new
   code value is a change to `epc_ingest/published_columns.yaml` and a decision to record.
3. Replace the `release` block of `epc_ingest/sources.yaml` with the new archive, note,
   members and row counts. The pins of the old release stay in git history and in the
   old release's `SOURCES.md`.
4. If the header changed, regenerate the schema with `python -m epc_ingest.columns` and
   bump `SCHEMA_VERSION` in `epc_ingest/columns.py`; the tests compare the file with the
   generator.
5. `python -m epc_ingest.pipeline --verify-archive`. Read `results/BUILD_REPORT.md`: the
   counts that observe (double-latest UPRNs, empty UPRNs, ratings above 100, zone statuses)
   will have moved; a check that fails is either a real change in the data or a pin to
   correct, and either is a decision to record in `epc_ingest/decisions.yaml`.
6. `python -m epc_ingest.sql_check`, `python -m epc_ingest.dictionary` and
   `python loader/make_notebook.py` (the notebook carries the build's hash and digest);
   `python -m pytest`. With docker: `sh loader/sqlserver_probe.sh` for the import scripts on the
   full build and `sh loader/notebook_probe.sh` for the notebook's cells on a fixture.
7. Copy the archive to `onedrive:EPC/` and, if the restricted Zenodo record is in use, add
   the new archive as a new version of it.
8. Load with `loader/load_epc_to_sqlserver.py` and the new `results/manifest.json`, into a
   table of its own or alongside the old release: the key carries `epc_release`, so both can
   share one table if a project wants to compare releases.
