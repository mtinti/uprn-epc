# Plan: ingest the Scottish domestic EPC register extract

Status: proposed, 29 October 2026. The source archive is downloaded and hashed
(`~/git_projects/epc_project/download/`, to be moved into this repository under `data/sources/`).
Nothing is built yet.

## Aim

Bring the Scottish Government's extract of domestic Energy Performance Certificates (EPC) into
the safe haven as a pinned, checked table, so a research project can attach the energy
performance of a dwelling to its records. Decided on 29 October 2026: **projects link by UPRN**, the Unique Property Reference
Number of the One Scotland Gazetteer, so the rating is a property of the dwelling, not of the
postcode. The postcode and the data zone are carried for the onward joins to SIMD and AHAH and
as a fallback where a certificate has no UPRN. The build keeps every published certificate and
every published value, and adds only the keys and statuses needed to join safely.

The build follows the one already used for SIMD, in
[postcode-simd](https://github.com/mtinti/postcode-simd), and the one written for AHAH on
29 October 2026 (`~/git_projects/AHAH/docs/AHAH_Plan.md`, `AHAH_SQL_Plan.md`). Each section
below names the part of those builds that solved the same problem. The three products fit
together: postcode-simd gives a postcode its data zones and SIMD, AHAH is keyed by data zone,
and EPC is keyed by postcode and carries its own data zones.

## What the extract is

The Scottish Energy Performance Certificate Register (SEPCR) holds every EPC lodged in Scotland.
The Scottish Government publishes an extract of every domestic certificate, one CSV per year of
lodgement, as "Domestic Energy Performance Certificates, Extended Historic Dataset". The release
in hand is to Q2 2026: lodgements from December 2008 to the end of June 2026, extracted from the
register on 1 September 2026, issued September 2026.

| | |
| --- | --- |
| Publisher | Scottish Government, EPCenquiries@gov.scot |
| Catalogue page | https://data.gov.scot/dataset/domestic_energy_performance_certificates___extended_historic_dataset_to_q1_2026 (the page keeps the `q1_2026` slug; the file it links is the Q2 2026 release) |
| Download | one 7z archive, 535,084,142 bytes, SHA256 `708cc7510a0215ba7f9bf73ccc9604b1e818b04f355e06c6adb192611103c351`, downloaded 5 October 2026 |
| Contents | 19 annual CSVs, `2008.csv` to `2026.csv`, 7.6 GB uncompressed, and the publication note (PDF, 17 pages, with the data dictionary) |
| Rows | 3,787,069 certificates over the 19 files (profile of 29 October 2026, `docs/profile_2026-10-29.json`) |
| Columns | 107 in every file. The note's dictionary lists 106 because it omits `DATA_ZONE_2011`; it also calls `ADDRESS3` `POST_TOWN` and spells `3_YR_ENERGY_SAVING_POTENTIAL` without the S. The mapping records all three |
| Licence | Open Government Licence for every field except the four address fields (`ADDRESS1`, `ADDRESS2`, `ADDRESS3`, `POSTCODE`), which carry Royal Mail's copyright notice and permitted purposes (publication note, pages 2 to 4) |
| Updates | quarterly. Each release is a new archive with every year republished |

What a certificate row is: one lodgement of one assessment of one dwelling. A dwelling can have
many certificates over time. `HISTORIC` is `True` when a later certificate for the same property
reference exists, `False` for the latest one (the note, page 5). It says nothing about expiry.

### Facts found in the files that the plan must handle

Every one of these comes from reading all 19 files on 29 October 2026 with
`tools/profile_sources.py`. The numbers are in `docs/profile_2026-10-29.json`.

- **Two header rows.** Row 1 is the machine name (`BUILDING_REFERENCE_NUMBER`), row 2 the
  publisher's label (`Property_UPRN`, `Date of Certificate`). The label row is itself a
  dictionary and feeds the data dictionary. The reader skips it and checks that all 19 files
  carry the same two rows.
- **Encoding.** UTF-8 with a byte order mark. The label row already contains the replacement
  character U+FFFD where the publisher lost `²` and `£` (`kWh/m�/year`). No data row contains it.
  The build reads UTF-8 strictly and fails on an undecodable byte.
- **The file year is the year of `CREATED_AT`**, the lodgement timestamp, not of
  `LODGEMENT_DATE`. Every row of `2014.csv` has a 2014 `CREATED_AT`; 87 of its rows have another
  `LODGEMENT_DATE` year, one of them 2017. `2018.csv` has a `LODGEMENT_DATE` in 2108, and
  2016 one in 2006. Values stay as published; the check is on `CREATED_AT`.
- **`REPORT_REFERENCE_NUMBER` (RRN) is missing from 340,010 rows (9%)**, most of them 2013 to 2016.
  Where present it is unique over all files: 3,447,059 distinct values, none repeated.
  `(BUILDING_REFERENCE_NUMBER, CREATED_AT)` is not unique (23 repeated pairs in the first
  200,000 rows of 2012). So the row key is a surrogate built from the pinned file: release,
  file year, row number. The RRN is a checked unique column where present.
- **Two data zone columns, both with the name appended.** `DATA_ZONE` is the 2001 data zone,
  `S01000416 (Ythsie)`; `DATA_ZONE_2011` is the 2011 data zone, `S01006982 (Ythsie - 05)`.
  From 2015 `DATA_ZONE` is empty in 4% to 12% of rows a year, and from 2021 `DATA_ZONE_2011` in 4%
  to 8%. The 2026 file also has `00Q...` and `00R...` in `DATA_ZONE` (418 rows) and `NA` in
  `DATA_ZONE_2011`. There is no 2022 data zone.
- **Two property numbers.** `BUILDING_REFERENCE_NUMBER` is the register's own 10-digit number,
  present in every row. `OSG_REFERENCE_NUMBER` is the Gazetteer UPRN, the one projects link on.
  It is present in 3,608,532 rows (95.3%) and empty in 178,537, from 0.1% of rows in 2008 to 8.1% in
  2021. Where both are present they are one to one: 1,885,772 distinct UPRNs, each with exactly
  one register number and the reverse. The note says a UPRN has 9 to 12 digits; about 1% of
  values have 8. They are real: every one exists in OS Open UPRN and lies in Clackmannanshire
  (`docs/uprn_check_2026-10-30.md`). Length follows the issuing council. The build keeps the
  text as published and derives `uprn_osg` as a bigint; every join compares the bigint, so a
  cohort UPRN padded to 12 digits matches.
- **One latest certificate per dwelling, almost.** 22 of the 1,882,946 UPRNs with a
  `HISTORIC = False` certificate have two. So that check observes rather than fails.
- **Postcodes are formatted with one space** in every row but 10 (empty, 2009). The 2001 and 2011
  zones were assigned by the register from the address, not by the build.
- **Values the publisher did not clean.** `TOTAL_FLOOR_AREA` is `0` in every row of 2008 and
  2009 (212,886 rows), although the note says rows outside 15 to 1500 m² are excluded; from
  2010 none is outside that range. `CURRENT_ENERGY_EFFICIENCY` has three- and four-digit values
  (199 rows of 2026). Six rows have an empty `CURRENT_ENERGY_RATING`. `TYPE_OF_ASSESSMENT` is
  empty in 7,490 rows from 2023. Lodgement before inspection: a few hundred rows a year to 2021,
  none from 2022. None of this is repaired. It is counted and reported.
- **Seven cells carry a trailing newline inside their quotes**, six in `BUILDING_REFERENCE_NUMBER`
  and one in `ADDRESS1`, and six `ADDRESS1` cells contain a double quote. The text columns keep
  them; the derived key columns are trimmed. The load test includes them.
- **Categories are consistent across years** (tenure, property type, transaction type, rating
  bands A to G). RdSAP appears in 2012 and replaces SAP for existing dwellings from 2013.

## The design, step by step

### 1. Pin the source

Every file the build reads is named in a registry with its URL, publisher, licence and SHA256.
Changed bytes stop the build.

- In postcode-simd: `simd_ingest/sources.yaml`, where an archive is a remote object and each
  extracted member has its own pin, and `core/fetch.py`. In AHAH: `ahah_ingest/sources.yaml`
  and `data/sources/*/SOURCES.md`.

The registry pins the 7z archive and each of its 20 members (19 CSVs and the note). The 7z
expands to 7.6 GB, so the build works from the extracted members, verifies each member's hash,
and verifies the archive only when asked (`--verify-archive`). The release is recorded as
`epc_release: 2026Q2` with the extraction date from the note (1 September 2026).

The catalogue resource URL will be overwritten by the Q3 release. The fetcher therefore cannot
re-download this release later; the local copy is the source. Keep a copy on OneDrive under
`onedrive:EPC/` as the instructions for projects say, and compare sizes after the copy.

Two reference lists are pinned alongside, each copied from the sibling project that already
pins it, with the same URL and hash, so the three projects agree on what a valid zone is:

- 2011 data zones: the Scottish Government 2011 data zone lookup, `DataZone2011_lookup.csv`,
  6,976 zones, sha256 `688416b875733f62d5ceede1ac2b73c9db021e816ea8a9c6c58da0f105b601b6`, as in
  AHAH `ahah_ingest/sources.yaml` under `datazone_lists`.
- 2001 data zones: the SIMD 2012 boundary table `SG_SIMD_2012.dbf`, 6,505 rows, one per zone,
  member sha256 `4dc58c30c7d023e4e39739e9d2e56fa9f4153a41ef4eeacbe9ba95d60e319095`, as in
  postcode-simd `simd_ingest/sources.yaml` under `sg_simd_2012`. AHAH has no 2001 list because
  its data start at the 2011 geography. The extract carries no 2022 zone, so AHAH's 2022 list is
  not pinned here.

### 2. Archive the source

Decided 29 October 2026: **a restricted Zenodo record, not an open one.** The address fields are
under Royal Mail's notice, which permits sharing only for the listed energy purposes and only
with the notice attached, and the archive cannot be split. postcode-simd cites the NRS postcode
products for the same reason and uploads nothing. EPC goes one step further because data.gov.scot
overwrites the download URL at every quarterly release, so without a copy the build could not be
repeated after three months. The record holds the 7z archive, the publication note, the checksum
list and the download metadata, with access on request and the purpose stated; the metadata
and hashes are public. Draft deposition 23784712 was created and its four files uploaded and
checksum-matched on 29 October 2026. On 30 October 2026 Michele decided to leave it as an
unpublished draft for now and to revisit publication later. Until then the draft serves as the
private off-site copy; the registry mirror entry points at the draft and must be updated if it is
ever published. The registry
records the catalogue page, the resource URL, the hash, the size and the Zenodo record as the
mirror, with `redistribution: restricted`, a third setting beside `upload` and `cite`.

- In postcode-simd: `docs/plans/Zenodo_Plan.md` and the `redistribution` block of `sources.yaml`.

### 3. Read and check

The reader streams one annual file at a time. 3.8 million rows by 107 columns with long free
text (`IMPROVEMENTS`, element descriptions) do not fit the whole-table pandas path AHAH uses;
the build writes one Parquet row group per file and runs the whole-table checks (key, RRN
uniqueness, one latest certificate per property) with DuckDB or pyarrow over the written
Parquet. The read-back check then compares the Parquet with the source file row for row.

Every published column is kept as text exactly as published, in its published order, under its
published name. Typed copies are added only for the columns a join or a check needs, each
derived by one documented rule (types and measured ranges in `EPC_SQL_Plan.md`):

| Derived column | From | Rule |
| --- | --- | --- |
| `epc_release`, `source_year`, `source_row` | the pinned file | key. `source_row` is 1 for the first data row (file row 3) |
| `rrn` | `REPORT_REFERENCE_NUMBER` | as published; NULL where empty; unique where not NULL |
| `uprn_sepcr` | `BUILDING_REFERENCE_NUMBER` | the register's own 10-digit reference, not the One Scotland Gazetteer UPRN (note, page 7) |
| `uprn_osg` | `OSG_REFERENCE_NUMBER` | the Gazetteer UPRN, where present |
| `pc_norm` | `POSTCODE` | upper case, ASCII spaces removed, as postcode-simd's `pc_norm`. Nothing repaired |
| `datazone_2001`, `datazone_2011` | `DATA_ZONE`, `DATA_ZONE_2011` | the code only, when the text starts with `S01` followed by six digits and a space or the end; otherwise NULL |
| `datazone_2001_status`, `datazone_2011_status` | the same | `code`, `empty`, `not_a_datazone` (for `00Q`, `NA` and the like), `unknown_code` (well formed but not in the pinned list) |
| `created_at_parsed`, `lodgement_date_parsed`, `inspection_date_parsed` | the three date columns | parsed; `CREATED_AT` is `dd/mm/yyyy hh:mm:ss`, the others `yyyy-mm-dd`. A value that does not parse stops the build |
| `historic_flag` | `HISTORIC` | boolean; any value other than `True` or `False` stops the build |
| `current_energy_efficiency_int`, `total_floor_area_int` and the other typed copies listed in `EPC_SQL_Plan.md` | the same | typed copies with a suffix for their kind; nullability and missing-value handling follow `EPC_SQL_Plan.md`, and a required value that is missing or does not parse stops the build; the published text stays beside them |

The build fails, rather than warns, when:

- a member's hash differs from its pin;
- the two header rows of a file differ from the pinned header rows, or a row has other than 107 fields;
- a byte is not UTF-8;
- the `CREATED_AT` year of a row differs from the file year;
- a date does not parse; `HISTORIC` is not `True` or `False`;
- the surrogate key repeats; a non-empty RRN repeats anywhere in the release;
- a UPRN maps to more than one register number, or the reverse (today none does);
- a parsed data zone code is well formed but not in the pinned list of its vintage.

The build counts and reports, without failing: empty UPRN, UPRNs with more than one
`HISTORIC = False` certificate (22 today), empty RRN, empty and malformed data zones,
empty postcodes, `TOTAL_FLOOR_AREA` outside 15 to 1500, efficiency ratings above 100,
empty rating bands, lodgement before inspection, `LODGEMENT_DATE` outside the file year.
These counts are in the build report and, for each release, in the decision log as evidence.

- In postcode-simd: `core/checks.py` and `docs/HOW_IT_IS_BUILT.md`. In AHAH:
  `ahah_ingest/checks.py`, `results/BUILD_REPORT.md`.

### 4. One table, keyed by certificate

The output is one table, `epc_domestic`, one row per published certificate, keyed by
`(epc_release, source_year, source_row)`. It carries the 107 published columns as text, in
published order, then the derived columns of the table above. Nothing is dropped, nothing is
recalculated. Column names of the published columns are the publisher's; the derived columns
are lower case.

Type rules for SQL Server follow the AHAH SQL plan: text columns `nvarchar(n)` sized from the
longest published value with headroom, and no `nvarchar(max)` anywhere, because the longest
value in the extract is 3,330 characters (`EPC_SQL_Plan.md` has the widths; a longer value in
a later release fails the schema check); dates `date` and `datetime2(0)`;
booleans `bit` only where the column is never NULL, else `tinyint` (AHAH review round 3);
typed numbers `int` or `decimal` with the same no-float rule.

Two naming rules, from the review of 30 October 2026. First, SQL Server compares column names
under the database collation, which is case-insensitive by default, so a derived column may
not differ from a published one by case alone: `INSPECTION_DATE` and `inspection_date` are
the same name. Every derived column therefore carries a suffix that names its kind
(`_parsed`, `_flag`, `_int`, `_num`) or is a new word (`rrn`, `uprn_osg`, `pc_norm`,
`datazone_2011`). The schema check folds every name to lower case and fails on a duplicate.
Second, empty and NULL mean different things. A published column is never NULL: an empty
cell is the empty string, as published, and the column is declared `NOT NULL`. A derived
column follows the nullability declared for it in the schema. The ones whose source can be
empty (`rrn`, `uprn_osg`, `pc_norm`, the two data zone codes) are nullable and NULL exactly
in the documented missing cases: an empty source cell, or a data zone text that is not a code.
The ones whose source is always present and always parses (the three dates, `historic_flag`,
`uprn_sepcr`, the ratings, the floor area, the three decimals) are `NOT NULL`, and a source
value that does not parse stops the build; it never becomes NULL. A cohort UPRN that is not
an integer is a linkage status (`no_uprn`), not a source failure. The generated SQL takes
its nullability from the schema, so the two cannot differ.
The CSV writes an empty string and a NULL both as an empty cell; `BULK INSERT` reads an empty
cell as NULL; the restore step puts `ISNULL(…, N'')` on published columns and
`NULLIF(…, N'')` on nullable derived text. The
digest renders the empty string as nothing and NULL as `NCHAR(0)`, so the two are distinct on
both sides. AHAH's generator assumes no text column can be blank and must be changed, not
copied, for this.

Why one table and not a normalised set (dwelling, certificate, measures): the published grain is
the certificate, and a project's first use is to pick one certificate per dwelling and date and
read a handful of columns. Splitting `IMPROVEMENTS` on `|` into a measures table is a possible
later product with its own plan.

- In AHAH: `ahah_ingest/output_schema.yaml`, `export_contract.yaml`, `docs/DATA_DICTIONARY.md`.

### 5. What leaves the build

Decided 30 October 2026: the repository publishes the recipe, not the data. The code, the
registry with hashes, the plan, the data dictionary and the example queries are public and cite
the source. The built Parquet, CSV and SQL table stay private, inside the safe haven and in the
restricted Zenodo draft. This is the `cite` model that postcode-simd uses for its products.
Anyone can rebuild the table from the public catalogue download and get the same hashes.

Inside the build, the export contract decides which columns go into the CSV for SQL Server.
**Revised 30 October 2026 (decision `address-lines-loaded`): every column goes out, the three
address lines included.** The CSV travels only to the HIC OneDrive and into the HIC SQL Server,
so withholding the lines protected a file that never leaves the safe haven, while costing the
only key for the 178,537 certificates without a Gazetteer UPRN and the only check on a UPRN
linkage against the cohort's own address. The register is published openly with the addresses.
A view without the three columns is the suggested analyst-facing object. The original proposal,
kept for the record: every column except `ADDRESS1`, `ADDRESS2` and `ADDRESS3`; `POSTCODE` and
`pc_norm` stay, because they are the join key. The Parquet keeps everything. Reasons given then:

- Royal Mail's notice allows address data for research into energy efficiency and under the
  non-commercial research exception. Health research that links EPC to patient records is not
  one of the listed purposes. Whether it falls under the research exception is a question for
  the information governance lead, not for the build. Since no built data leave the safe
  haven, the question is narrower than it was: it is only whether the SQL table inside the
  safe haven may carry the three address lines, not whether they may be published.
- Address lines are the strongest property-level key, so a project that needs them (for
  matching a cohort's addresses to a dwelling) can ask for a build with a different contract,
  recorded as a decision.

postcode-simd withholds coordinates the same way, through `export_contract.yaml`.

### 6. Load into SQL Server and check the load

As in AHAH: the build writes a gzip CSV, a manifest with row count and a digest of every row,
a generated import script and a generated check script that recomputes the digest on the loaded
table. The loader verifies the file hash first. At 3.8 million rows the digest is computed in
SQL over the whole table once; the AHAH check runs on 35,000 rows, so the probe against a
throwaway SQL Server 2022 container (`loader/sqlserver_probe.sh`) must time it before the first
real load.

The row digest: the digest renders each cell as text with the same rules on both sides and
concatenates them. `CONCAT_WS` returns `nvarchar(4000)` unless an operand is `nvarchar(max)`,
and a row of bounded cells can still exceed 4,000 characters in total, so the first operand of
every concatenation chunk is converted to `nvarchar(max)`, as AHAH's generator already does.
Bounded column widths do not remove that need. The test set includes a row whose cells each
fit their column but together exceed 8,000 characters, with a quote, a comma, a newline and a
`|` in `IMPROVEMENTS`; changing its last cell must change the loaded digest.

- In AHAH: `ahah_ingest/sql_check.py`, `loader/load_ahah_to_sqlserver.py`, `loader/sqlserver_probe.sh`.

### 7. Example joins

The main query joins by UPRN. Each query is a left join so no cohort row disappears, each row
gets a status, and the choice of certificate is explicit in the query, never a default. The
cohort table has a unique `cohort_row_id` as well as the person identifier, and every
partition, grouping and join is by that row: a person appears many times in a longitudinal
cohort, and pooling a person's rows would hand a later certificate to an earlier observation
(implementation review, 30 October 2026). The query stops if the row identifier is NULL or repeats:

1. **By UPRN, the certificate with the latest inspection on or before a date.** For a cohort
   row with a UPRN and a date, the certificate of that `uprn_osg` with the latest
   `inspection_date_parsed` on or before the date. The inspection is when the assessor saw the
   dwelling, so it is the date that describes the home; the lodgement date is administrative
   and follows it, the same day in 43% of certificates, within a week in 83%, over a month in
   7% (decided 30 October 2026; the query used the lodgement date before). The query returns
   both dates, the certificate's age in days at the cohort date counted from the inspection,
   and a flag for the 2,036 certificates lodged before their inspection date. It does not decide
   whether the certificate has expired; a certificate is valid for ten years from lodgement, and
   the project applies that rule or another. A tie is two or more certificates of one UPRN
   inspected on the latest eligible day; older same-day pairs do not count once a later
   certificate is eligible. Revised 31 October 2026 (decision `tie-prefers-current-then-latest-lodged`):
   the query breaks a tie by preferring the `HISTORIC = False` certificate, then the latest
   `created_at_parsed`, and reports `epc_tie_candidates` and `epc_tie_rule`; only a pair neither
   separates gets `ambiguous_as_of` and no values (22 UPRNs of the 49,705 whose latest inspection
   day is a tie). Before that revision no tie was broken. Without a date, the `HISTORIC = False`
   certificate. The 22 dwellings with two of those get `ambiguous_latest` and no values; the
   2,826 UPRNs whose certificates are all `HISTORIC = True` get `no_current_certificate`.
   Statuses: `matched`, `no_uprn` (the cohort UPRN is empty or not an integer),
   `uprn_not_in_epc` (the dwelling has no certificate, which is most of the housing stock),
   `no_certificate_by_date`, `ambiguous_as_of`, `ambiguous_latest`, `no_current_certificate`.
   The join compares `uprn_osg` with the cohort UPRN cast to bigint, never as text.
2. **By postcode, the fallback.** For a cohort row without a UPRN, one row per dwelling in
   that `pc_norm`: for each dwelling, the certificate of the latest inspection on or before the date,
   with the same tie rule as the UPRN route. The dwelling is `uprn_sepcr`, the register's own
   number, which is present in every row and one to one with the Gazetteer UPRN where that
   exists, so dwellings without a Gazetteer UPRN are still one dwelling each. A postcode has
   many dwellings, so this returns many rows per cohort row and the project decides how to
   summarise them. The README says plainly that
   this is a property of the postcode's dwellings, not of the patient's.
3. **Onward to SIMD and AHAH.** From `pc_norm` through postcode-simd's `link_as_of.sql` to the
   data zone and SIMD of the lodgement date, and from `datazone_2011` to `ahah_datazone`
   version 4. The EPC's own `datazone_2011` and postcode-simd's `DataZone2011Code` for the same
   postcode can differ; the query shows both and the README says why (the register assigned
   its zone from the address at lodgement; postcode-simd from the postcode's grid reference or
   output area centroid).

The published text of `OSG_REFERENCE_NUMBER` stays in the table as provenance only. No query
compares it.

- In postcode-simd: `docs/sql/spd/link_as_of.sql`, `docs/LINKAGE_BY_ERA.md`. In AHAH: the join
  in `README.md` and the status pattern of `SIMD_Procedure_Plan.md`.

### 8. Record the decisions

Every policy choice goes into a decision log with its reason and evidence, and its hash travels
in the Parquet metadata and the manifest:

- values as published, text first, typed copies second;
- the surrogate key, because RRN is missing from 9% of rows;
- the file year rule (`CREATED_AT`);
- data zone parsing and the two reference lists;
- the address columns withheld from the CSV; the recipe published, the built data kept private;
  restricted Zenodo draft, unpublished, as the off-site copy of the source;
- which checks fail and which observe, with this release's counts.

- In postcode-simd: `simd_ingest/decisions.yaml`, `docs/UPDATING.md`. In AHAH: `ahah_ingest/decisions.yaml`.

## Disclosure

A certificate row names a dwelling: address, postcode, property reference, floor area, age
band. The table is for use inside the safe haven. What leaves is decided at extraction. An EPC
rating attached to a patient record at postcode level is a property of the postcode's
dwellings, not of the patient's dwelling; the UPRN join gives the patient's dwelling. The
README says so. A dwelling-level EPC attached to a patient record adds floor area, age band
and built form to what is known about the person's home, which the output checks must weigh.

## Tests

- Hashes: a changed member stops the build; a changed archive stops `--verify-archive`.
- Reader: a synthetic file with a wrong label row, 106 fields, a non-UTF-8 byte, a `CREATED_AT`
  in another year, `HISTORIC = TRUE` in capitals, and a repeated RRN each fails with its own
  message.
- Parsing: `S01000416 (Ythsie)` gives `S01000416` and `code`; `00Q...`, `NA`, empty and
  `S01000416(Ythsie)` give their statuses; a well formed code not in the list fails the build.
- Values: a sample of rows from each year, chosen in advance, equals the source cell for cell,
  including a row with a multi-line `IMPROVEMENTS`.
- Latest certificate: at most one `HISTORIC = False` per `uprn_osg`, or the documented exception.
- Joins: a UPRN with three certificates returns the right one at three dates, `no_certificate_by_date`
  before the first, `ambiguous_as_of` for two certificates lodged on the same day with a
  cohort date on and after that day, and `matched` again once a single later certificate is
  eligible, `ambiguous_latest` for a synthetic dwelling with two
  latest certificates, and `no_current_certificate` for one whose certificates are all
  historic; a UPRN with no certificate gets `uprn_not_in_epc`; a cohort UPRN written
  `000035000001` matches the EPC row `35000001` in the join itself, not only in the parser. A postcode with two
  dwellings and three certificates returns the right rows at three dates; lower case and
  no-space postcodes match; an empty postcode gets `no_postcode`.
- SQL Server: the import and check scripts load a synthetic table and pass, and fail on a
  changed value; the table includes a row whose cells each fit their width but exceed 8,000
  characters together, an empty `ADDENDUM_TEXT` that reads back as the empty string, an empty
  `OSG_REFERENCE_NUMBER` whose `uprn_osg` reads back as NULL, a malformed `LODGEMENT_DATE`
  and a non-integer `TOTAL_FLOOR_AREA` that each stop the build before any file is written,
  generated SQL whose NULL and NOT NULL match the schema field for field, and a schema with two names
  differing only by case, which the schema check rejects before any SQL runs. The digest time on the full table is measured
  in the probe and recorded.

## Order of work

1. Done 5 October 2026: archive downloaded, hashed, extracted; publication note read.
2. Done 29 October 2026: all 19 files profiled (`docs/profile_2026-10-29.json`).
3. Done 30 October 2026: download moved to `data/sources/epc_2026Q2/` with a `SOURCES.md`;
   registry `epc_ingest/sources.yaml` with the 19 member hashes and row counts; the two data
   zone lists pinned from the sibling projects; archive, note and checksums copied to
   `onedrive:EPC/`.
4. Done 30 October 2026: reader, derived columns, per-year and whole-table checks, Parquet and
   CSV writers with the digest, SQL generator, loader and probe; 33 tests on a synthetic
   release (`tests/`), each hostile file failing with its own named check.
5. Done 30 October 2026: the real build (`results/manifest.json`, `results/BUILD_REPORT.md`),
   the generated SQL scripts, the data dictionary.
6. Done 30 October 2026: the container probe (`docs/sql/SQLSERVER_PROBE_2026-10-30.md`):
   import 413 s, digest 26 s, every check passed after two fixes (read the file as UTF-8;
   datetime2 precision). The real load into the HIC server is for Michele to run with
   `loader/load_epc_to_sqlserver.py`.
7. Done 30 October 2026: the three example queries and the onward sketch in `docs/sql/`,
   tested in DuckDB; the README.
8. Ask information governance whether the table inside the safe haven may carry the address
   lines; record the answer and, if needed, a second export contract.

## Open questions

- ~~Per dwelling or per postcode.~~ Settled 29 October 2026: per dwelling, linked by UPRN. The
  postcode route is the fallback.
- ~~Whether the 8-digit UPRNs lost a leading zero.~~ Settled 30 October 2026 by checking every
  distinct UPRN against OS Open UPRN (`docs/uprn_check_2026-10-30.md`): all 17,933 8-digit values
  exist and lie in Clackmannanshire; 99.9% of all lengths exist. Length follows the issuing
  council. The README must say: compare UPRNs as integers, never as text.
- How the cohort gets its UPRNs. This is outside the build. The routes, in order, are in
  `docs/ADDRESS_MATCHING_review.md` (29 October 2026): ask Public Health Scotland for the
  CHI-UPRN Residential Linkage (CURL) first; otherwise match CHI address text to the One
  Scotland Gazetteer inside the safe haven, deterministic passes first, probabilistic on the
  residue, with a reviewed sample per pass.
- What share of the cohort's UPRNs will have a certificate. Most dwellings never had one, so the
  README must give the coverage: 1.9 million dwellings with a certificate against about
  2.7 million in Scotland.
- ~~Whether `HISTORIC = False` is unique per property reference across the whole release.~~
  Answered by the profile of 29 October 2026: 22 UPRNs carry two certificates in force. The join
  reports them as `ambiguous_latest`.
- ~~Which 2001 data zone list to pin.~~ Settled 30 October 2026: reuse the SIMD 2012 boundary
  table that postcode-simd already pins, `SG_SIMD_2012.dbf` (6,505 rows, one per 2001 data zone,
  member sha256 `4dc58c30c7d023e4e39739e9d2e56fa9f4153a41ef4eeacbe9ba95d60e319095`, from
  https://maps.gov.scot/ATOM/shapefiles/SG_SIMD_2012.zip, mirrored at Zenodo record 23119743).
  Same source, same hash, so the two projects agree on what a valid 2001 zone is.
- ~~Whether this lives in its own repository or inside postcode-simd.~~ Settled 30 October 2026:
  its own repository. Three products with the same build recipe argue for a shared core package
  later; not now.
