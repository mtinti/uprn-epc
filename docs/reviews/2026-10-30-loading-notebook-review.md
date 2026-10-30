# Loading notebook review — 2026-10-30

Scope: loader/upload_epc.ipynb, its generator loader/make_notebook.py, notebook tests, shipped import/digest SQL and current manifest. Notebook cell numbers below are zero-based JSON cell indexes; the displayed step numbers are also supplied.

Verdict: fix the Step 6 query before distributing the notebook. One definite functional defect found. The pyodbc upload path has not been independently validated by this review.

## 1. [P2] Limit the twice-assessed dwelling selector to one UPRN

Location: loader/upload_epc.ipynb, Step 6, code cell 12; loader/make_notebook.py:406.

The sample query uses:

    uprn_osg = (
        SELECT MIN(uprn_osg)
        FROM <table>
        WHERE uprn_osg IS NOT NULL
        GROUP BY uprn_osg
        HAVING COUNT(*) = 2
    )

GROUP BY returns one row for every qualifying UPRN; MIN within each group does not choose a single group. The equality comparison requires one scalar result. A read-only query against the current Parquet counted **559,442 UPRNs with exactly two certificates**, so this example fails on the actual release rather than merely on an unusual fixture.

A minimal two-UPRN fixture reproduced the scalar-subquery cardinality error in DuckDB. SQL Server documents the same restriction in [Microsoft's subquery rules](https://learn.microsoft.com/en-us/sql/relational-databases/performance/subqueries).

Use SELECT TOP (1) uprn_osg ... GROUP BY uprn_osg HAVING COUNT(*) = 2 ORDER BY uprn_osg, or apply MIN outside the grouped qualifying-UPRN subquery. Fix the generator and regenerate the notebook.

Regression: at least two qualifying dwellings, each with two certificates; the selector must return exactly one dwelling and the outer example must execute successfully. Include zero qualifying dwellings so the fallback behavior is explicit.

## Load behavior to keep explicit

Steps 3–5 do not provide all-or-nothing replacement of an existing accepted table. Step 3 commits DROP/CREATE before Step 4 inserts and commits each chunk; Step 5 validates afterward. A later upload, index or digest failure leaves the old table gone and the destination incomplete or unvalidated.

The notebook already documents dropping/recreating and restarting from Step 3, so this is recorded as an operational limitation rather than a hidden implementation defect. Use a dedicated destination for a first load. If the notebook is intended for refreshing an accepted table, load and validate a separate candidate table before promoting it. The Step 3 transaction protects against CREATE failure only.

## What checked successfully

- All seven code cells parse as Python.
- Notebook has no saved execution counts or outputs; it does not provide evidence of a completed notebook run.
- Embedded uncompressed CSV SHA256, expected row count and digest total match results/manifest.json.
- Step 3's parser extracts 127 columns, with the expected five nullable derived columns. Existing test compares the parsed order against the CSV header.
- Step 5's section extraction was evaluated without connecting to a database: it selects the complete table-check block and substitutes dbo.epc_domestic consistently.
- Notebook-specific test command:

    /opt/homebrew/Caskroom/miniforge/base/bin/python3 -m pytest -q -p no:cacheprovider tests/test_notebook.py

  Result: **2 passed in 0.31 seconds**.

## Validation gap before the real upload

The prior SQL Server probe validates a BULK INSERT path. This notebook instead uses pyodbc fast_executemany, binds every field as SQL_WVARCHAR, and relies on SQL Server conversions. The notebook tests parse code and inspect schema/manifest values; neither executes that transport path.

The review environment does not have pyodbc installed, and no production server connection or destructive notebook cell was executed. Before a full notebook upload, run the actual Step 3–5 path against a disposable table with a small fixture covering:

- empty published strings beside nullable derived values;
- non-ASCII text, embedded newline and quotes;
- a maximum-width text value and a combined row exceeding 8,000 characters;
- padded/large UPRNs, exact decimals, dates, timestamps and flags;
- a failed batch and a deliberately changed loaded value that fails the digest.

Use fixture-specific expectations. Verify the actual pyodbc/ODBC driver path, not a substitute BULK INSERT. Full upload runtime and fast_executemany memory use remain unmeasured.

No notebook, generator, source data or database table was modified. Earlier reviews are preserved.
