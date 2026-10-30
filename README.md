# epc-scotland

Scottish domestic Energy Performance Certificates (EPCs) for SQL Server, one row per
certificate, joinable to a cohort by UPRN and date. The recipe is public; the built table is
not.

The Scottish Government publishes an extended historic extract of the domestic EPC register
every quarter: every certificate lodged since December 2008, superseded ones included, with the
address, the postcode, the One Scotland Gazetteer UPRN, the ratings, the floor area, the age
band and 90 other fields. This project turns one release of it into one table, every value
exactly as published, built the way [postcode-simd](https://github.com/mtinti/postcode-simd)
and [datazone-ahah](https://github.com/mtinti/datazone-ahah) are built: pinned sources, blocking
checks, typed copies by documented rules, a CSV with a row digest, generated import and check
scripts, and a loader.

## What is in the table

`epc_domestic`, release 2026Q2: 3,787,069 certificates from 19 annual files (2008 to 2026),
130 columns in the Parquet and 127 in the CSV and the SQL table, keyed by `epc_release`,
`source_year`, `source_row`. Three groups of columns, in this order:

1. **Key and provenance**: the release, the annual file, the row in it.
2. **The 107 published columns**, under the publisher's names, as text exactly as published.
   An empty cell is the empty string, never NULL.
3. **Derived columns**, each a typed copy of one published column by one rule: `uprn_osg`
   (bigint), `uprn_sepcr`, `rrn`, `pc_norm`, the two data zone codes with a status, the three
   dates, `historic_flag`, four ratings, the floor area and three decimals. Their names carry a
   kind suffix (`_parsed`, `_flag`, `_int`, `_num`) so none equals a published name in another case.

The data dictionary, `docs/DATA_DICTIONARY.md`, lists every column. The build report,
`results/BUILD_REPORT.md`, gives this release's counts.

Four things to know before joining:

- **Join by `uprn_osg` as an integer, never as text.** The UPRNs run from 8 to 12 digits
  because each council has its own number range; the short ones are real
  (`docs/uprn_check_2026-10-30.md`). A cohort UPRN padded with zeros matches once both sides
  are bigint.
- **Most dwellings have no certificate.** About 1.9 million UPRNs appear in the release against
  about 2.7 million dwellings in Scotland. A cohort row with no match is `uprn_not_in_epc`, not
  an error, and the README of any project using this must say what share matched.
- **Same-day pairs are common.** 42,870 (UPRN, lodgement day) pairs carry two or more
  certificates in this release, against 22 UPRNs with two current certificates. The dated join
  reports such a pair as `ambiguous_as_of` only when it falls on the latest eligible day; the
  build report counts them and a project should expect that status, not treat it as rare.
- **`HISTORIC = True` means superseded, not expired.** A certificate is valid for ten years.
  The dated join returns the latest certificate lodged on or before the cohort date and its age
  in days; the project decides about expiry.
- **The address lines are not in the CSV or the SQL table.** `ADDRESS1` to `ADDRESS3` and
  `POSTCODE` carry a Royal Mail notice rather than the Open Government Licence. The three
  address lines stay in the Parquet only; the postcode and `pc_norm` go out because they are the
  fallback join key. Whether the table inside the safe haven may carry the address lines is a
  question for information governance, recorded in `docs/EPC_Plan.md`.

## Build

```
pip install -r requirements.txt
python -m epc_ingest.pipeline --verify-archive   # results/epc_domestic.parquet, .csv.gz, manifest.json, BUILD_REPORT.md
python -m epc_ingest.sql_check                   # docs/sql/import_csv.sql, check_loaded_digest.sql
python -m epc_ingest.dictionary                  # docs/DATA_DICTIONARY.md
python -m pytest
```

The build reads the pinned files under `data/sources/` (hashes in each folder's `SOURCES.md`
and in `epc_ingest/sources.yaml`), one annual file at a time, and stops on any changed byte, a
header that differs from the pin, a row count that differs, a date, flag, integer or decimal
that does not parse, a text longer than its column, a data zone code that is well formed but
in neither pinned list, a repeated report reference number, or two property numbers that are
not one to one. It never goes through a float. The source files are not in this repository:
`data/sources/epc_2026Q2/SOURCES.md` says where they came from and how to get them again.

## Load into SQL Server

Carry `results/epc_domestic.csv.gz`, `results/manifest.json`, the two scripts in `docs/sql/`
and `loader/load_epc_to_sqlserver.py` to the server; fill in the EDIT block; run the loader. It
verifies the file hash, imports with `BULK INSERT` through a staging table, restores the
empty strings on published columns and NULL on derived ones, builds the two join indexes, and
runs the check script, whose expected row count and digest come from the manifest, never from
the loaded table. The import names `CODEPAGE = '65001'` so the file is read as UTF-8; on SQL
Server for Linux, which rejects that option, convert the CSV to UTF-16 and import it as
`widechar`, as the probe does. `loader/sqlserver_probe.sh` runs the same scripts against a throwaway SQL
Server 2022 container, times the import and the digest, and asserts SQL Server's rendering of
chosen cells, the empty-against-NULL counts and the join statuses.

## Join

Three queries in `docs/sql/`, each a left join so no cohort row disappears, each returning one
status per cohort row, each choosing the certificate explicitly. The cohort table carries a
unique `cohort_row_id` beside the person identifier, because a person appears many times in a
longitudinal cohort and each observation must get the certificate for its own date and address;
the queries stop if the row identifier repeats.

- `join_by_uprn.sql`: the latest certificate lodged on or before the cohort date. Statuses
  `matched`, `no_uprn`, `uprn_not_in_epc`, `no_certificate_by_date`, `ambiguous_as_of` (two or
  more lodged on the latest eligible day).
- `join_latest_by_uprn.sql`: without a date, the `HISTORIC = False` certificate. Statuses
  `matched`, `no_uprn`, `uprn_not_in_epc`, `no_current_certificate`, `ambiguous_latest`.
- `join_by_postcode.sql`: the fallback for a cohort row without a UPRN, one row per dwelling in
  the postcode. What it gives is a property of the postcode's dwellings, not of the person's.
- `onward_to_simd_and_ahah.sql`: a sketch from a matched certificate to postcode-simd's SIMD of
  the lodgement date and to datazone-ahah version 4.

The queries are tested against the cases the plan names in DuckDB (`tests/test_joins.py`) and
against SQL Server by the container probe.

## Sources, licence and archive

Scottish Government, *Domestic Energy Performance Certificates, extended historic dataset to
Q2 2026*, https://data.gov.scot/dataset/domestic_energy_performance_certificates___extended_historic_dataset_to_q1_2026
(the slug says Q1; the file is Q2; the URL is overwritten every quarter). Extracted from the
register on 1 September 2026, downloaded 5 October 2026, archive SHA256
`708cc7510a0215ba7f9bf73ccc9604b1e818b04f355e06c6adb192611103c351`. Open Government Licence
v3.0 for every field except the three address lines and the postcode, which carry a Royal Mail
copyright notice (publication note, page 2). Two data zone reference lists are pinned from the
sibling projects (`data/sources/datazones/SOURCES.md`).

Because the download URL does not last and the address fields are not under the Open
Government Licence, the archive is held as an unpublished restricted Zenodo draft rather than
an open record, and a copy sits on the HIC OneDrive. The built table is private.

## Documents

- `docs/EPC_Plan.md`: the plan, the facts found in the files, the design, the decisions.
- `docs/EPC_SQL_Plan.md`: the table shape for SQL Server.
- `docs/ADDRESS_MATCHING_review.md`: how a cohort gets its UPRNs, which is outside this build.
- `docs/uprn_check_2026-10-30.md`: the check of the short UPRNs against OS Open UPRN.
- `docs/UPDATING.md`: taking a new quarterly release.
- `docs/reviews/`: the plan reviews and the responses.

Code: MIT (`LICENSE`). Michele Tinti, Health Informatics Centre, University of Dundee.
