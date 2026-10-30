"""Generate the SQL Server scripts: import the CSV, then check the loaded table against the build.

    python -m epc_ingest.sql_check          # rewrites docs/sql/import_csv.sql and check_loaded_digest.sql

Copied from datazone-ahah's sql_check.py with the types EPC uses and one rule it did not have:
a published column is NOT NULL and an empty CSV cell restores to the empty string, while a
nullable derived column restores to NULL. The check script confirms the declared columns,
types, widths, nullability and key, and recomputes the row digest the build recorded, compared
against the manifest, never against the loaded table. The CLI never connects to a database.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .columns import SCHEMA, TABLE
from .core.output import load_schema
from .core.text_output import DECIMAL_PRECISION, DECIMAL_SCALE, exported_columns, load_contract

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
CONTRACT = PACKAGE / "export_contract.yaml"
OUT = ROOT / "docs" / "sql" / "check_loaded_digest.sql"
IMPORT_OUT = ROOT / "docs" / "sql" / "import_csv.sql"

SQL_TYPE = {"string": "nvarchar", "int16": "smallint", "int32": "int", "int64": "bigint",
            "decimal": "decimal", "date": "date", "datetime": "datetime2", "bool": "bit"}
DECIMAL_DECLARED = f"decimal({DECIMAL_PRECISION},{DECIMAL_SCALE})"
# A decimal(19,4) renders as at most 15 integer digits, a sign, a point and 4 decimals: 21.
DECIMAL_TEXT = 40
CONCAT_CHUNK = 200
COLLATION = "Latin1_General_100_BIN2_UTF8"
# Staging holds UTF-8 bytes; the widest columns stage as max so a non-ASCII-heavy value fits.
STAGING_MAX_FROM = 1000


def declared_type(field: dict) -> str:
    kind = field["type"]
    if kind == "string":
        return f"nvarchar({field['width']})"
    if kind == "decimal":
        return DECIMAL_DECLARED
    if kind == "datetime":
        return "datetime2(0)"
    return SQL_TYPE[kind]


def _render(field: dict) -> str:
    """One column as the text the digest hashes, never NULL: CONCAT_WS drops a NULL argument,
    which would shift every later field. Each rendering equals the Python one byte for byte:
    style 23 for a date, 120 for a timestamp, 0 or 1 for a bit, fixed 4 decimals for a decimal."""
    name, kind = field["name"], field["type"]
    if kind in ("int16", "int32", "int64"):
        return f"ISNULL(CONVERT(varchar(20), [{name}]), NCHAR(0))"
    if kind == "decimal":
        return f"ISNULL(CONVERT(varchar({DECIMAL_TEXT}), [{name}]), NCHAR(0))"
    if kind == "date":
        return f"ISNULL(CONVERT(varchar(10), [{name}], 23), NCHAR(0))"
    if kind == "datetime":
        return f"ISNULL(CONVERT(varchar(19), [{name}], 120), NCHAR(0))"
    if kind == "bool":
        return f"ISNULL(CONVERT(varchar(1), [{name}]), NCHAR(0))"
    return f"ISNULL([{name}], NCHAR(0))"


def _restore(field: dict) -> str:
    """The staged text of one column as its declared type. BULK INSERT reads an empty cell as
    NULL, so a published column (never NULL) gets the empty string back and a nullable derived
    column stays NULL. A required typed column whose text does not convert yields NULL here and
    the NOT NULL constraint stops the insert, which is the intended failure."""
    name, kind = field["name"], field["type"]
    if kind == "string":
        return f"NULLIF([{name}], N'')" if field["nullable"] else f"ISNULL([{name}], N'')"
    if kind in ("int16", "int32", "int64"):
        return f"CONVERT({SQL_TYPE[kind]}, NULLIF([{name}], ''))"
    if kind == "decimal":
        return (f"CASE WHEN CONVERT(varchar({DECIMAL_TEXT}), CONVERT({DECIMAL_DECLARED}, NULLIF([{name}], ''))) = [{name}] "
                f"THEN CONVERT({DECIMAL_DECLARED}, [{name}]) END")
    if kind == "date":
        return f"CONVERT(date, NULLIF([{name}], ''), 23)"
    if kind == "datetime":
        return f"CONVERT(datetime2(0), NULLIF([{name}], ''), 120)"
    if kind == "bool":
        return f"CONVERT(bit, NULLIF([{name}], ''))"
    raise ValueError(kind)


def _table_sql(table: str, name: str, schema: dict, contract: dict) -> str:
    columns = exported_columns(schema, contract, table)
    fields = {f["name"]: f for f in schema["fields"]}

    def declared_row(i, c):
        f = fields[c]
        kind = f["type"]
        # sys.columns reports datetime2(0) with precision 19 and scale 0.
        precision = f"{DECIMAL_PRECISION}, {DECIMAL_SCALE}" if kind == "decimal" else "19, 0" if kind == "datetime" else "NULL, NULL"
        max_length = 2 * f["width"] if kind == "string" else "NULL"
        return f"    (N'{c}', {i}, N'{SQL_TYPE[kind]}', {precision}, {max_length}, {1 if f['nullable'] else 0})"
    declared = ",\n".join(declared_row(i, c) for i, c in enumerate(columns, 1))
    key = ", ".join(f"[{k}]" for k in schema["key"])
    rendered = [_render(fields[c]) for c in columns]
    chunks = [rendered[i:i + CONCAT_CHUNK] for i in range(0, len(rendered), CONCAT_CHUNK)]
    for chunk in chunks:
        chunk[0] = f"CONVERT(nvarchar(max), {chunk[0]})"
    if len(chunks) == 1:
        expression = ",\n           ".join(chunks[0])
    else:
        expression = ",\n           ".join("CONCAT_WS(NCHAR(31),\n           " + ",\n           ".join(chunk) + ")" for chunk in chunks)
    text_columns = [c for c in columns if fields[c]["type"] == "string"]
    reserved = "\n       OR ".join(
        f"DATALENGTH(REPLACE(REPLACE([{c}] COLLATE {COLLATION}, NCHAR(0), N''), NCHAR(31), N'')) <> DATALENGTH([{c}])"
        for c in text_columns)
    return f"""
-- ============================================================================================
-- {name}: structure, key, then the digest
-- ============================================================================================
IF OBJECT_ID(N'{name}', N'U') IS NULL
    INSERT INTO #result VALUES (N'{name}', N'table exists', N'a table', N'not found', NULL, 0);
ELSE
BEGIN
    -- 1. Structure. A digest cannot establish any of this. max_length is in bytes, so an
    -- nvarchar(n) declares 2n; NULL means not compared.
    DECLARE @declared TABLE (name sysname, ordinal int, type_name sysname,
                             numeric_precision int, numeric_scale int, max_length int, is_nullable bit);
    INSERT INTO @declared (name, ordinal, type_name, numeric_precision, numeric_scale, max_length, is_nullable) VALUES
{declared};

    INSERT INTO #result
    SELECT N'{name}', N'columns declared and in order', N'0 differences',
           CONVERT(nvarchar(200), COUNT(*)) + N' differences', COUNT(*), CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
    FROM (
        -- Bound to the one object being checked by OBJECT_ID, never by name alone.
        SELECT d.name FROM @declared d
        LEFT JOIN (SELECT c.name, c.column_id, t.name AS type_name, c.precision, c.scale, c.max_length, c.is_nullable
                   FROM sys.columns c JOIN sys.types t ON t.user_type_id = c.user_type_id
                   WHERE c.object_id = OBJECT_ID(N'{name}', N'U')) c
               ON c.name = d.name AND c.column_id = d.ordinal AND c.type_name = d.type_name
              AND (d.numeric_precision IS NULL
                   OR (c.precision = d.numeric_precision AND c.scale = d.numeric_scale))
              AND (d.max_length IS NULL OR c.max_length = d.max_length)
              AND c.is_nullable = d.is_nullable
        WHERE c.name IS NULL
        UNION ALL
        SELECT c.name FROM sys.columns c
        WHERE c.object_id = OBJECT_ID(N'{name}', N'U')
          AND c.name NOT IN (SELECT name FROM @declared)
    ) AS differences;

    -- 2. The natural key: the digest is order independent, so a duplicated row and a missing
    -- one can cancel out.
    INSERT INTO #result
    SELECT N'{name}', N'natural key {key} unique and not null', N'0 offending rows',
           CONVERT(nvarchar(200), COUNT_BIG(*)) + N' offending rows', COUNT_BIG(*),
           CASE WHEN COUNT_BIG(*) = 0 THEN 1 ELSE 0 END
    FROM (SELECT {key} FROM {name} GROUP BY {key} HAVING COUNT_BIG(*) > 1) AS duplicates;

    -- 3. Reserved framing characters in the text columns.
    INSERT INTO #result
    SELECT N'{name}', N'no reserved framing characters in text', N'0 rows',
           CONVERT(nvarchar(200), COUNT_BIG(*)) + N' rows', COUNT_BIG(*),
           CASE WHEN COUNT_BIG(*) = 0 THEN 1 ELSE 0 END
    FROM {name}
    WHERE {reserved};

    -- 4. The row count and the digest, rendered as the CSV renders each row, NCHAR(0) for a
    -- null, fields joined with NCHAR(31) in contract order, hashed as UTF-8, the signed
    -- eight-byte prefixes summed as decimal. The first operand of each chunk is nvarchar(max)
    -- so CONCAT_WS cannot truncate a long row.
    INSERT INTO #result
    SELECT N'{name}', N'row count', CONVERT(nvarchar(200), e.row_count),
           CONVERT(nvarchar(200), q.n), ABS(q.n - e.row_count),
           CASE WHEN q.n = e.row_count THEN 1 ELSE 0 END
    FROM #expected e CROSS JOIN (SELECT COUNT_BIG(*) AS n FROM {name}) AS q
    WHERE e.name = N'{name}';

    INSERT INTO #result
    SELECT N'{name}', N'row digest, definition version ' + CONVERT(nvarchar(10), e.digest_version),
           CONVERT(nvarchar(200), e.digest_total), CONVERT(nvarchar(200), ISNULL(q.total, 0)),
           CASE WHEN ISNULL(q.total, 0) = e.digest_total THEN 0 ELSE 1 END,
           CASE WHEN ISNULL(q.total, 0) = e.digest_total THEN 1 ELSE 0 END
    FROM #expected e CROSS JOIN (
        SELECT SUM(CONVERT(decimal(38,0), CONVERT(bigint, SUBSTRING(HASHBYTES('SHA2_256',
                   CONVERT(varchar(max), CONCAT_WS(NCHAR(31),
           {expression}) COLLATE {COLLATION})), 1, 8)))) AS total
        FROM {name}) AS q
    WHERE e.name = N'{name}';
END
"""


def _import_sql(table: str, name: str, schema: dict, contract: dict) -> str:
    columns = exported_columns(schema, contract, table)
    fields = {f["name"]: f for f in schema["fields"]}
    spec = contract["tables"][table]

    def staging_type(f):
        if f["type"] == "string" and f["width"] >= STAGING_MAX_FROM:
            return "varchar(max)"
        return "varchar(8000)"
    staging = ",\n    ".join(f"[{c}] {staging_type(fields[c])} COLLATE {COLLATION} NULL" for c in columns)
    typed = ",\n    ".join(f"[{c}] {declared_type(fields[c])}" + ("" if fields[c]["nullable"] else " NOT NULL") for c in columns)
    key = ", ".join(f"[{k}]" for k in schema["key"])
    select = ",\n    ".join(_restore(fields[c]) for c in columns)
    names = ",\n    ".join(f"[{c}]" for c in columns)
    return f"""
-- --------------------------------------------------------------------------------------------
-- {name}: stage as text, then restore the declared types. BULK INSERT reads an empty cell as
-- NULL. A published column is NOT NULL and gets the empty string back (ISNULL); a nullable
-- derived column stays NULL (NULLIF). A required typed column that does not convert stops the
-- insert on its NOT NULL constraint.
-- --------------------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging_{name};
CREATE TABLE staging_{name} (
    {staging}
);

-- EDIT the path. FORMAT = 'CSV' honours RFC 4180 quoting, embedded newlines included.
-- ROWTERMINATOR is LF, as the contract specifies. CODEPAGE = '65001' makes BULK INSERT read
-- the file as UTF-8: without it the bytes are read in the server's OEM code page whatever
-- the staging collation says, and a non-breaking space (C2 A0) arrives as two other
-- characters (found in the container probe of 30 October 2026).
BULK INSERT staging_{name}
FROM '/path/to/{spec["file"][:-3]}'
WITH (FORMAT = 'CSV', FIELDQUOTE = '"', FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a',
      CODEPAGE = '65001', FIRSTROW = 2, TABLOCK);

DROP TABLE IF EXISTS {name};
CREATE TABLE {name} (
    {typed},
    CONSTRAINT PK_{name} PRIMARY KEY ({key})
);

INSERT INTO {name} (
    {names}
)
SELECT
    {select}
FROM staging_{name};

DROP TABLE IF EXISTS staging_{name};

-- The two join routes.
CREATE INDEX IX_{name}_uprn_osg ON {name} ([uprn_osg], [lodgement_date_parsed]) INCLUDE ([historic_flag]);
CREATE INDEX IX_{name}_pc_norm ON {name} ([pc_norm], [lodgement_date_parsed]) INCLUDE ([uprn_sepcr], [historic_flag]);
"""


def render_import() -> str:
    contract = load_contract(CONTRACT)
    schema = load_schema(SCHEMA)
    return f"""-- Import the EPC CSV into SQL Server, then check it with check_loaded_digest.sql.
-- Generated by python -m epc_ingest.sql_check from the output schema and the export contract.
--
-- Decompress the file first and edit the path below. Run it against a database of your own:
-- it drops and recreates the two tables it names. 3.8 million rows: expect minutes, not seconds.
--
-- Verify the file hash against results/manifest.json before importing. After importing, run
-- check_loaded_digest.sql with that manifest's row count and digest total.

SET NOCOUNT ON;
SET XACT_ABORT ON;
{_import_sql(TABLE, TABLE, schema, contract)}"""


def render() -> str:
    contract = load_contract(CONTRACT)
    schema = load_schema(SCHEMA)
    digest = contract["digest"]
    return f"""-- Check the imported table against the build that produced its CSV.
-- Generated by python -m epc_ingest.sql_check from the output schema and the export contract.
--
-- It reads the table; it never repairs, replaces or promotes anything. The expected values
-- come from results/manifest.json, which is the build's own record, never from the loaded table.
--
-- What this establishes: the declared columns, types, widths, nullability and order are
-- present, the natural key is unique and not null, no text contains the framing characters,
-- the row count matches, and the recomputed digest matches.
-- What it does not: the digest truncates each SHA-256 to eight bytes and adds the results, so
-- collisions and cancelling changes are possible. It detects accidental load corruption.

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- STEP 1. EDIT. Paste this build's numbers from results/manifest.json (csv.rows, csv.digest.total).
IF OBJECT_ID(N'tempdb..#expected', N'U') IS NOT NULL DROP TABLE #expected;
CREATE TABLE #expected (name sysname PRIMARY KEY, row_count bigint NOT NULL,
                        digest_total decimal(38,0) NOT NULL, digest_version int NOT NULL);
INSERT INTO #expected (name, row_count, digest_total, digest_version) VALUES
    (N'{TABLE}', 0, 0, {digest['version']})   -- EDIT: rows and total from manifest csv.digest
;

IF EXISTS (SELECT 1 FROM #expected WHERE digest_version <> {digest['version']})
    THROW 51000, 'This script implements digest definition version {digest['version']} only.', 1;
IF EXISTS (SELECT 1 FROM #expected WHERE row_count <= 0)
    THROW 51000, 'Expected row count and digest total have not been filled in from the manifest.', 1;

IF OBJECT_ID(N'tempdb..#result', N'U') IS NOT NULL DROP TABLE #result;
CREATE TABLE #result (table_name sysname, check_name nvarchar(200), expected nvarchar(200),
                      actual nvarchar(200), difference bigint NULL, passed bit NOT NULL);
{_table_sql(TABLE, TABLE, schema, contract)}
-- ============================================================================================
-- The result. A skipped check is not a pass, so an absent row fails the count below.
-- ============================================================================================
SELECT table_name, check_name, expected, actual, difference,
       CASE passed WHEN 1 THEN 'pass' ELSE 'FAIL' END AS outcome
FROM #result ORDER BY table_name, check_name;

DECLARE @failed int = (SELECT COUNT(*) FROM #result WHERE passed = 0);
DECLARE @ran int = (SELECT COUNT(*) FROM #result);
IF @failed > 0 OR @ran <> 5
    THROW 51000, 'The imported table does not match the build: see the result above.', 1;
"""


def main(argv=None) -> int:
    directory = Path(argv[0]) if argv else OUT.parent
    directory.mkdir(parents=True, exist_ok=True)
    for path, text in ((directory / IMPORT_OUT.name, render_import()), (directory / OUT.name, render())):
        path.write_text(text)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
