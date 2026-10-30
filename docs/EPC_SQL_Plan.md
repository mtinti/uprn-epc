# Plan: shape the EPC table for SQL Server

Status: proposed, 29 October 2026; revised 30 October 2026 after
`docs/reviews/2026-10-30-ingestion-plan-review.md`. Companion to `EPC_Plan.md`, which covers the source, the
checks, the keys and the joins. This document covers only the shape of the output and how it
reaches SQL Server. It copies the path AHAH walks (`~/git_projects/AHAH/docs/AHAH_SQL_Plan.md`)
and postcode-simd before it, so the same writer, digest, loader and review steps apply.

Every type and length below is measured over all 3,787,069 rows of the 19 files
(`docs/columns_2026-10-29.json`, produced by `tools/profile_columns.py`).

## What AHAH does, and what EPC reuses

| Step | AHAH | EPC |
| --- | --- | --- |
| Declare the columns | `ahah_ingest/output_schema.yaml`: name, type, nullable, key, description | `epc_ingest/output_schema.yaml`, same format, one table |
| Decide what the CSV carries | `export_contract.yaml`: every column goes out | `export_contract.yaml`: every column, the three address lines included since the revision of 30 October 2026 (`EPC_Plan.md`, section 5) |
| Write the CSV | `core/text_output.py`, with `decimal` and `int32` added | the same, with `int64` added for the UPRN and `datetime` for `CREATED_AT`, each with one rendering in Python and in SQL and a round-trip test |
| Record the build | `results/manifest.json`: SHA256, rows, columns, digest total | the same, plus rows per source year |
| Generate the SQL | `sql_check.py` writes `import_csv.sql` and `check_loaded_digest.sql` | the same generator |
| Load | `loader/load_ahah_to_sqlserver.py` | copy with the EPC table name and expected values |

Two differences of scale. The table is 3.8 million rows by about 125 columns, roughly 7 GB as
text, so the build streams one source year at a time and never holds the table in memory; and the
loaded-digest check runs over 3.8 million rows, so its time is measured in the container probe
before the first real load and recorded in the README.

## The table

One table, `epc_domestic`, one row per published certificate, keyed by
`(epc_release, source_year, source_row)`. Three groups of columns, in this order:

1. **Key and provenance**, added by the build.
2. **The 107 published columns**, under the publisher's names, in the publisher's order, every
   value as text exactly as published. These are the record. Nothing is dropped or changed.
3. **Derived columns**, lower case, each from one published column by one documented rule
   (`EPC_Plan.md`, section 3). They exist so a join or a filter does not re-parse text. No
   derived name may equal a published name when both are folded to lower case, because SQL
   Server compares identifiers under the database collation, case-insensitive by default.
   Typed copies carry a suffix for their kind: `_parsed` for dates, `_flag` for bit, `_int`,
   `_num`. The schema check enforces this.

Empty against NULL: a published column is `NOT NULL` and holds the empty string where the
file is empty (`ADDENDUM_TEXT` in every row, `REPORT_REFERENCE_NUMBER` in 9%,
`OSG_REFERENCE_NUMBER` in 4.7%, both data zones, `ADDRESS2` in 40%). A derived column has
the nullability the table below declares. Nullable ones are NULL only in their documented
missing case (empty source, or data zone text that is not a code). `NOT NULL` ones come from
sources that are never empty and always parse; a value that does not parse stops the build
and never becomes NULL. The generated SQL copies nullability from the schema. `BULK INSERT`
reads an empty CSV cell as NULL, so the restore step is `ISNULL([col], N'')` for published
columns and `NULLIF([col], N'')` for nullable derived text; AHAH's `NULLIF` on every text
column is not copied.
The digest renders NULL as `NCHAR(0)` and the empty string as nothing, so a published empty
cell and a derived NULL hash differently and the loaded digest proves which one arrived.

### Key and provenance

| Column | SQL type | Notes |
| --- | --- | --- |
| `epc_release` | nvarchar(8) | `2026Q2`. A later release is a new build, never an update |
| `source_year` | smallint | the annual file, 2008 to 2026, which is the year of `CREATED_AT` |
| `source_row` | int | 1 for the first data row of the file (file row 3) |

### The published columns, by kind

The text columns are `nvarchar(n)`. `n` is the longest published value rounded up with headroom,
so a longer value in a later release stops the build at the schema check rather than at the load.
No column needs `nvarchar(max)`: the longest value in the whole extract is 3,330 characters, in
`IMPROVEMENTS`. The row digest still converts the first operand of each concatenation chunk to
`nvarchar(max)`, as AHAH's generator does: `CONCAT_WS` returns `nvarchar(4000)` unless an
operand is `max`, and a row of 125 bounded cells can exceed that, so without the conversion
the digest would hash a truncated row. Bounded cells do not bound the row.

| Kind | Columns | Measured | nvarchar(n) |
| --- | --- | --- | --- |
| Flags and bands | `HISTORIC`; the four rating bands; `MAINS_GAS_FLAG`; `SOLAR_WATER_HEATING_FLAG`; `GLAZED_AREA`; `EXTENSION_COUNT`; `WIND_TURBINE_COUNT` | 1 to 5 | 8 |
| Codes | `BUILDING_REFERENCE_NUMBER`; `OSG_REFERENCE_NUMBER`; `POSTCODE`; `REPORT_REFERENCE_NUMBER`; `CONSTITUENCY`; the two dates; `CREATED_AT` | 6 to 24 | 32 |
| Short categories | `TYPE_OF_ASSESSMENT`; `TENURE`; `TRANSACTION_TYPE`; `PROPERTY_TYPE`; `BUILT_FORM`; `FLOOR_LEVEL`; `HEAT_LOSS_CORRIDOOR`; `ENERGY_TARIFF`; `MECHANICAL_VENTILATION`; `CONSTRUCTION_AGE_BAND`; `LOCAL_AUTHORITY_LABEL`; `GLAZED_TYPE`; `MAIN_HEATING_CATEGORY`; `MAIN_FUEL`; `WINDOWS_DESCRIPTION` | up to 69 | 100 |
| Numbers as text | every cost, rating, count, demand, area and emission column | up to 15 | 32 |
| Geography text | `DATA_ZONE`; `DATA_ZONE_2011`; `CONSTITUENCY_LABEL`; `ADDRESS1`; `ADDRESS2`; `ADDRESS3` | up to 75 | 128 |
| Element summaries | the nine `_DESCRIPTION` columns and their 18 `_ENERGY_EFF` and `_ENV_EFF` columns; `SECONDHEAT_DESCRIPTION`; `LZC_ENERGY_SOURCES`; `ALTERNATIVE_IMPROVEMENTS` | up to 328 | 512 |
| Lists | `PHOTO_SUPPLY` | 570 | 1000 |
| Lists | `IMPROVEMENTS` | 3,330 | 4000 |
| Empty | `ADDENDUM_TEXT` | 0, empty in every row | 128, kept because it is published |

Twenty-eight columns hold `|`-separated lists: `IMPROVEMENTS`, `ALTERNATIVE_IMPROVEMENTS`,
`LZC_ENERGY_SOURCES`, `PHOTO_SUPPLY`, and the element description and rating columns, where a
dwelling with two wall types has two entries. They stay as published. Splitting them into a
measures table is a separate product.

### Derived columns

| Column | From | SQL type | Rule and measured range |
| --- | --- | --- | --- |
| `rrn` | `REPORT_REFERENCE_NUMBER` | nvarchar(24), NULL | as published where not empty; unique; `9999-9999-9999-9999-9999` shape in every non-empty row |
| `uprn_sepcr` | `BUILDING_REFERENCE_NUMBER` | bigint, not NULL | trimmed. Seven cells of the extract carry a trailing newline inside the quotes (six here, one in `ADDRESS1`); the text column keeps it, the derived column does not. 10 digits, 1000001613 to 1236813833 |
| `uprn_osg` | `OSG_REFERENCE_NUMBER` | bigint, NULL | trimmed, as an integer; the only column any join compares, so a padded cohort UPRN matches. 8 to 12 digits, 35000001 to 906700556768, all real (`docs/uprn_check_2026-10-30.md`). Empty in 4.7% |
| `pc_norm` | `POSTCODE` | nvarchar(8), NULL | upper case, spaces removed, postcode-simd's rule; 8 not 7 because the published column is 8 wide and a value without a space would not shrink; the build report counts values outside 5 to 7 characters |
| `datazone_2001`, `datazone_2011` | `DATA_ZONE`, `DATA_ZONE_2011` | nvarchar(9), NULL | the leading `S01` plus six digits, NULL otherwise |
| `datazone_2001_status`, `datazone_2011_status` | the same | nvarchar(16) | `code`, `empty`, `not_a_datazone`, `unknown_code` |
| `inspection_date_parsed`, `lodgement_date_parsed` | the two date columns | date, not NULL | `yyyy-mm-dd` in every row |
| `created_at_parsed` | `CREATED_AT` | datetime2(0), not NULL | `dd/mm/yyyy hh:mm:ss` in every row |
| `historic_flag` | `HISTORIC` | bit, not NULL | `True` or `False` in every row, nothing else |
| `current_energy_efficiency_int`, `potential_energy_efficiency_int`, `environment_impact_current_int`, `environment_impact_potential_int` | the same | int, not NULL | integers in every row. Ranges 0 to 21,241 and 0 to 38,128: a SAP rating runs 1 to 100, so values above 100 are publisher errors kept as published and counted |
| `total_floor_area_int` | `TOTAL_FLOOR_AREA` | int, not NULL | integer in every row, 0 to 1,498; 0 in every 2008 and 2009 row |
| `energy_consumption_current_num`, `co2_emissions_current_num`, `co2_emiss_curr_per_floor_area_num` | the same | decimal(19,4), not NULL | two decimal places in every row |

Every other published number stays text only until a project asks for it. The rule for adding
one is in the decision log: a typed copy is added with the measured scale, the text column is
never removed, and the build fails when a value does not parse.

Why `decimal(19,4)` and not AHAH's `decimal(38,20)`: the EPC values are published with 2 or
4 decimals (costs) and at most 8 (`FLOOR_HEIGHT`), and the typed copies are derived, not the
record. The text column is the record, so fidelity is already guaranteed by the digest over the
text. `decimal(19,4)` covers every value observed with the same no-float parse.

Values that are codes, not measurements, found in the profile and kept as published, with their
meaning recorded in the data dictionary as "observed, not documented by the publisher":

- `-1` in `LOW_ENERGY_FIXED_LIGHT_COUNT` and `FLAT_TOP_STOREY`;
- `00` to `20` zero-padded in `FLAT_TOP_STOREY`, which is why it stays text;
- `N`, `Y`, `false`, `true` mixed in `SOLAR_WATER_HEATING_FLAG`;
- negative values in the three `IMPACT_*_INSULATION` columns (they are reductions);
- ONS-style codes such as `00EM` in `LOCAL_AUTHORITY_LABEL` in a few rows;
- `FLOOR_HEIGHT` up to 2,550, `NUMBER_HABITABLE_ROOMS` up to 99, `NUMBER_OPEN_FIREPLACES` up
  to 100, `SPACE_HEATING_DEMAND` from −8,653,797 to 1,751,944,128.

## Files the build produces

| File | What |
| --- | --- |
| `results/epc_domestic.parquet` | the table, one row group per source year, schema and decision-log hash in the metadata |
| `results/epc_domestic.csv.gz` | the export, every column, written with mtime 0 |
| `results/manifest.json` | SHA256 of both, rows in total and per year, columns, digest version and total |
| `results/BUILD_REPORT.md` | every check with its result, the observed counts, three certificates cell for cell against the source |
| `docs/sql/import_csv.sql`, `docs/sql/check_loaded_digest.sql` | generated |
| `docs/DATA_DICTIONARY.md` | generated from the schema, the publisher's label row and the publication note |

## Load

As AHAH: `BULK INSERT` into a staging table of `nvarchar` columns, cast into the typed table,
then the check script recomputes the row digest and compares the count and total with the
manifest. Three things to settle in the container probe before the real load:

- the time of the digest over 3.8 million rows by about 125 columns, and whether it needs to run
  per `source_year`;
- that a cell with an embedded newline (seven of them) and a cell with a quote (six, in
  `ADDRESS1`) survive `BULK INSERT` with the format file, or that the loader switches to a
  row-by-row path for those files;
- that non-ASCII text survives. Found in the first probe, 30 October 2026: a UTF-8 collation on
  the staging columns does not make `BULK INSERT` read the file as UTF-8. Without
  `CODEPAGE = '65001'` the bytes are read in the server's OEM code page and a non-breaking
  space (C2 A0, common in `IMPROVEMENTS`) arrives as two other characters, so every text cell
  with a non-ASCII character differs and the digest fails. The generated import now sets
  `CODEPAGE = '65001'`. datazone-ahah's import has the same gap and passed only because its
  text is ASCII. SQL Server on Linux rejects `CODEPAGE`, so the container probe converts the
  CSV to UTF-16LE and imports it as `widechar`, which the second probe showed keeps a
  non-breaking space and an embedded newline intact;
- the clustered key `(epc_release, source_year, source_row)` and two nonclustered indexes,
  `(uprn_osg, lodgement_date_parsed)` and `(pc_norm, lodgement_date_parsed)`, for the two join routes.

## Tests specific to this plan

- Round trip for the new `int64` and `datetime` renderings: Python text, Parquet, CSV, SQL
  Server, and back, byte for byte.
- A synthetic file with a 4,001-character `IMPROVEMENTS` fails the schema check with a message
  naming the column and the length. This is the production rule; there is no `max` column.
- A synthetic row whose cells each fit their width but together exceed 8,000 characters loads,
  and changing its last cell changes the loaded digest.
- An empty `ADDENDUM_TEXT` reads back from SQL Server as the empty string, not NULL; an empty
  `OSG_REFERENCE_NUMBER` reads back as the empty string with `uprn_osg` NULL; the digest
  matches the manifest in both cases.
- A schema with `INSPECTION_DATE` and `inspection_date` fails the schema check before any SQL
  is generated.
- A malformed `LODGEMENT_DATE` and a non-integer `TOTAL_FLOOR_AREA` each stop the build with
  a message naming the column, the row and the value; neither becomes NULL.
- The generated `CREATE TABLE` declares NULL and NOT NULL exactly as `output_schema.yaml` does,
  checked field for field.
- The seven trailing-newline cells and six quoted cells load and digest the same on both sides.
- A padded `000035000001` and `35000001` in `OSG_REFERENCE_NUMBER` give the same `uprn_osg`,
  and a cohort table holding `000035000001` as text joins to the EPC row in the example query.
- `FLAT_TOP_STOREY` `00` stays `00` in the text column.
- Every typed copy equals its text column parsed, for every row, after read-back.
