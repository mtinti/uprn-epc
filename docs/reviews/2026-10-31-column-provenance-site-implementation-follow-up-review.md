# Column provenance site implementation follow-up — 31 October 2026

## Scope

Reviewed commit `7ad5913` against its parent and the preceding implementation review, including the shared SQL index definitions, lineage memberships, site rendering, replacement-character explanations, regression tests and review response.

## Outcome

No new actionable findings in the reviewed changes. The previous P2 index-membership finding is closed.

- `sql_check.JOIN_INDEXES` now supplies both SQL generation and provenance.
- Lineage records both inspection-date key memberships, both historic-flag included memberships, the SEPCR included membership, and all three primary-key positions.
- Column pages render each membership and distinguish key positions from included columns.
- Tests cover the memberships, columns without indexes, and both index names on the inspection-date page.
- The new U+FFFD explanation preserves published labels and appears conditionally on affected column pages; the data dictionary also explains the source encoding issue.

## Validation

- Full test suite: **70 passed**.
- Generated import SQL matches `docs/sql/import_csv.sql` **byte for byte**.
- Site generation: **130 columns, 23 sources, 12 decisions, 30 check families**.
- Strict MkDocs build: **passed**, using temporary output directories.

No application code changed during this review. Live Pages publishing and a real SQL Server load were not rerun; this change preserves the generated import SQL. The publication-note quotations were not independently rechecked against the PDF in this follow-up.
