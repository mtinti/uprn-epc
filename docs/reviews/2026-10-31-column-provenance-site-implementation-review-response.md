# Response to the column provenance site implementation review, 31 October 2026

Review: `2026-10-31-column-provenance-site-implementation-review.md`. One P2, confirmed and
fixed; one further point raised by the author, the replacement characters in five labels, also
addressed.

## P2: every index membership

Confirmed: `lineage()` gave `index: null` for `inspection_date_parsed`, `historic_flag`,
`uprn_sepcr` and the three key columns, because the lineage knew only the leading column of each
join index, typed by hand beside the SQL generator's own literal.

Fix: `sql_check.JOIN_INDEXES` is now the one definition of the two join indexes (key columns in
order, included columns, what each serves), and `index_sql` renders the CREATE INDEX lines from
it; `docs/sql/import_csv.sql` regenerates byte for byte, so the loader and the notebook, which
copy those lines from the script, are unchanged. `lineage.index_memberships` lists every index a
column takes part in, with its role: primary key column n of 3, key column n of m, or included
column. The page's "In SQL Server" section renders each membership with the full column list and
what the index serves.

Tests: the import script contains each rendered index; the inspection date is key column 2 of 2
in both join indexes; the flag is included in both; the SEPCR number in the postcode index; the
key columns form the primary key in order; a plain published column has no membership; the set
of columns with a membership equals the set the indexes name. The inspection-date page is checked
for both index names.

## The odd symbols

The five labels `kWh/m�/year`, `m�`, `(�)` twice and `kg.CO2/m�/yr` are as the publisher's file
prints them: the second header row of every annual file holds the bytes EF BF BD, the UTF-8
replacement character U+FFFD, where `²` and `£` were lost before publication
(`docs/EPC_Plan.md`, encoding). The build keeps labels as published and the `header_labels` check
pins them, so they stay. The column pages and the data dictionary now say so where a label carries
the character and point at the publication note for the intended one.

## Not covered

The label note is attached by testing for U+FFFD in the label; a label mangled some other way
would not be flagged. The index metadata is shared by the generator, the lineage and the site but
the join queries in `docs/sql/` still spell the columns themselves; the tests of `test_joins.py`
hold them to the fixture, not to `JOIN_INDEXES`. My findings are closed.
