# Column provenance site implementation review — 31 October 2026

## Scope and outcome

Reviewed the provenance implementation against the revised site plan: lineage, check catalogue, descriptions and extraction script, amended decisions, page generation, tests, MkDocs configuration and Pages workflow/publishing script.

One P2 finding remains. The original plan findings are substantially implemented: note aliases and project attribution, lookup dependencies for status columns, conditional check definitions and sampled coverage, and amendment-aware decision presentation.

## Finding

### [P2] Record every index membership, not just the leading columns

Location: `epc_ingest/lineage.py:72–74` and `159–160`; rendering at `epc_ingest/provenance_site.py:173–174`.

`INDEXES` maps only `uprn_osg` and `pc_norm` to one index each. Consequently, lineage returns `index: null` for `inspection_date_parsed`, even though the loader creates both join indexes with that column as their second key. It also returns null for `historic_flag` (included in both indexes), `uprn_sepcr` (included in the postcode index), and the three primary-key columns.

The generated “In SQL Server” sections therefore omit these memberships. This is material to a per-column provenance site whose plan promises to document whether each column is indexed: a reader visiting the inspection-date page cannot discover its indexed role there.

Evidence: `epc_ingest/sql_check.py:234` defines the primary key; lines 247–248 define both composite join indexes and their included columns. Direct inspection of `lineage()` confirmed null index metadata for the inspection date, historic flag and SEPCR identifier. Existing tests check only the leading UPRN column and its index's text, so they do not detect the omission.

Suggested correction: represent a column's index memberships as a list, distinguishing key position from included-column membership and covering the primary key. Prefer shared index metadata used by both SQL generation and lineage. Render all memberships and test the inspection date in both indexes, the included columns, and the primary-key columns against the loader's definitions.

## Validation

- Full test suite: **68 passed**, using Miniforge Python with its bin directory first on PATH.
- Generated the site in a temporary directory: **130 column pages, 23 sources, 12 decisions, 30 check families**.
- Strict MkDocs build: **passed**.
- Current `decisions.yaml` SHA256 matches the checked-in build manifest.
- Reviewed reader transformations and SQL definitions against the new lineage and catalogue.

No application code was changed. The review did not publish the site, exercise live GitHub Pages deployment, repeat the private full-data build, or independently verify the PDF quotations visually. Passing tests and the strict build validate generation and links, but do not resolve the semantic index omission above.
