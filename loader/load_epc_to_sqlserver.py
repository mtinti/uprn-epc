"""Load the EPC CSV into SQL Server and check that the load is faithful.

Carry five files to the machine that will run this: the CSV (epc_domestic.csv.gz or the
decompressed epc_domestic.csv), results/manifest.json, the two SQL scripts from docs/sql
(import_csv.sql and check_loaded_digest.sql), and this file. Put them in one folder, fill in
the block marked EDIT below, and run:

    python load_epc_to_sqlserver.py                 # verify, import, check
    python load_epc_to_sqlserver.py --check-only    # only re-run the checks
    python load_epc_to_sqlserver.py --print-sql     # write the filled SQL, connect to nothing

The expected hash, row count and digest come from manifest.json beside this script, so a new
build needs a new manifest, not a new copy of this script. 3.8 million rows by 127 columns:
the import takes minutes and the digest check several more.

It connects with Windows integrated authentication unless you paste an ODBC connection string.
No password is stored here. If a password is unavoidable, pass it in the environment as
EPC_SQL_PASSWORD together with EPC_SQL_USER, and it is used without being written anywhere.
"""

from __future__ import annotations

# =================================================================================================
# EDIT: everything this script needs to know about your server.
# =================================================================================================

SERVER = r"<SERVER\INSTANCE>"          # for example  r"NHSSQL01\PROD,1433"
DATABASE = r"<DATABASE>"               # it must already exist; this script does not create it

MAIN_TABLE = "epc_domestic"            # one row per published certificate

# The folder holding the CSV file, as this machine sees it.
CSV_DIRECTORY = r"<C:\path\to\the\csv\folder>"

# The same folder as the SQL Server sees it. BULK INSERT reads from the server's own filesystem.
SERVER_CSV_DIRECTORY = CSV_DIRECTORY

# Leave empty for Windows integrated authentication, or paste your site's own string whole.
ODBC_CONNECTION_STRING = ""

# =================================================================================================
# Nothing below needs editing.
# =================================================================================================

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENERATED_NAME = "epc_domestic"


def fail(message: str) -> None:
    sys.exit("stopped: " + message)


def manifest() -> dict:
    path = HERE / "manifest.json"
    if not path.is_file():
        fail("manifest.json is not beside this script. Copy it from results/ in the project.")
    m = json.loads(path.read_text(encoding="utf-8"))
    if m.get("table") != GENERATED_NAME or m["csv"]["digest"]["version"] != 1:
        fail("manifest.json is not an epc_domestic build with digest definition version 1")
    return m


def check_settings() -> None:
    for name, value in (("SERVER", SERVER), ("DATABASE", DATABASE), ("CSV_DIRECTORY", CSV_DIRECTORY)):
        if "<" in str(value):
            fail(f"{name} is still a placeholder. Fill in the EDIT block at the top of this file.")
    if not Path(CSV_DIRECTORY).is_dir():
        fail(f"CSV_DIRECTORY does not exist: {CSV_DIRECTORY}")
    for name in ("import_csv.sql", "check_loaded_digest.sql"):
        if not (HERE / name).is_file():
            fail(f"{name} is not beside this script. Copy it from docs/sql in the project.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_files(m: dict) -> None:
    """The files travelled, so check them before they reach the database. The compressed form
    is what usually travels, so decompress it here if only that is present."""
    csv_spec = m["csv"]
    packed = Path(CSV_DIRECTORY) / csv_spec["file"]
    path = Path(CSV_DIRECTORY) / csv_spec["file"][:-3]
    if not path.is_file() and packed.is_file():
        actual = sha256(packed)
        if actual != csv_spec["sha256"]:
            fail(f"{packed.name}: expected sha256 {csv_spec['sha256'][:16]}, found {actual[:16]}")
        print(f"  {packed.name}: sha256 matches, decompressing")
        with gzip.open(packed, "rb") as source, path.open("wb") as target:
            while True:
                block = source.read(1 << 20)
                if not block:
                    break
                target.write(block)
    if not path.is_file():
        fail(f"neither {path.name} nor {packed.name} is in {CSV_DIRECTORY}")
    size = path.stat().st_size
    if size != csv_spec["uncompressed_bytes"]:
        fail(f"{path.name}: expected {csv_spec['uncompressed_bytes']:,} bytes, found {size:,}. "
             "A transfer that changed the line endings will do this.")
    actual = sha256(path)
    if actual != csv_spec["uncompressed_sha256"]:
        fail(f"{path.name}: expected sha256 {csv_spec['uncompressed_sha256'][:16]}, found {actual[:16]}")
    print(f"  {path.name}: {size:,} bytes, sha256 matches, {csv_spec['rows']:,} rows x {csv_spec['columns']} columns")


def _parts(name: str) -> tuple:
    clean = name.replace("[", "").replace("]", "").strip()
    if "." in clean:
        schema, bare = clean.rsplit(".", 1)
        return schema + ".", bare
    return "", clean


def rename_tables(sql: str) -> str:
    """Put your table name into the generated scripts. Every replacement is parked on a marker
    first, because the file name contains the table name."""
    schema, bare = _parts(MAIN_TABLE)
    replacements = [(f"staging_{GENERATED_NAME}", f"{schema}staging_{bare}"),
                    (f"PK_{GENERATED_NAME}", f"PK_{bare}"),
                    (f"IX_{GENERATED_NAME}_", f"IX_{bare}_"),
                    (f"{GENERATED_NAME}.csv", "\x01csv\x01"),
                    (GENERATED_NAME, f"{schema}{bare}")]
    parked = {}
    for n, (old, new) in enumerate(replacements):
        marker = f"\x00{n}\x00"
        parked[marker] = new
        sql = sql.replace(old, marker)
    for marker, new in parked.items():
        sql = sql.replace(marker, new)
    return sql.replace("\x01csv\x01", f"{GENERATED_NAME}.csv")


def filled_import(m: dict) -> str:
    sql = rename_tables((HERE / "import_csv.sql").read_text(encoding="utf-8"))
    separator = "\\" if "\\" in SERVER_CSV_DIRECTORY else "/"
    csv_name = m["csv"]["file"][:-3]
    target = SERVER_CSV_DIRECTORY.rstrip("/\\") + separator + csv_name
    sql = sql.replace(f"/path/to/{csv_name}", target)
    if "/path/to/" in sql:
        fail("the CSV path was not filled in; the import script may not be the one this build shipped")
    return sql


def filled_check(m: dict) -> str:
    sql = (HERE / "check_loaded_digest.sql").read_text(encoding="utf-8")
    placeholder = f"(N'{GENERATED_NAME}', 0, 0, "
    if placeholder not in sql:
        fail("the check script has no place to put the expectations")
    sql = sql.replace(placeholder, f"(N'{GENERATED_NAME}', {m['csv']['rows']}, {m['csv']['digest']['total']}, ")
    return rename_tables(sql)


def connection_string() -> str:
    if ODBC_CONNECTION_STRING:
        return ODBC_CONNECTION_STRING
    parts = [r"Driver={ODBC Driver 18 for SQL Server}", f"Server={SERVER}", f"Database={DATABASE}",
             "Encrypt=yes", "TrustServerCertificate=yes"]
    user = os.environ.get("EPC_SQL_USER")
    if user:
        password = os.environ.get("EPC_SQL_PASSWORD")
        if not password:
            fail("EPC_SQL_USER is set but EPC_SQL_PASSWORD is not")
        parts += [f"UID={user}", f"PWD={password}"]
    else:
        parts.append("Trusted_Connection=yes")
    return ";".join(parts) + ";"


def run(sql: str, label: str) -> None:
    """Run one script, preferring pyodbc and falling back to sqlcmd."""
    try:
        import pyodbc
    except ImportError:
        pyodbc = None
    if pyodbc is not None:
        with pyodbc.connect(connection_string(), autocommit=True, timeout=0) as connection:
            cursor = connection.cursor()
            for batch in re.split(r"(?im)^\s*GO\s*$", sql):
                if batch.strip():
                    cursor.execute(batch)
                    while True:
                        if cursor.description:
                            for row in cursor.fetchall():
                                print("   " + " | ".join("" if v is None else str(v) for v in row))
                        if not cursor.nextset():
                            break
        return
    written = HERE / f"{label}.filled.sql"
    written.write_text(sql, encoding="utf-8")
    command = ["sqlcmd", "-S", SERVER, "-d", DATABASE, "-b", "-I", "-C", "-t", "0", "-i", str(written)]
    user = os.environ.get("EPC_SQL_USER")
    command += ["-U", user, "-P", os.environ["EPC_SQL_PASSWORD"]] if user else ["-E"]
    done = subprocess.run(command, capture_output=True, text=True)
    print(done.stdout.strip())
    if done.stderr.strip():
        print(done.stderr.strip(), file=sys.stderr)
    if done.returncode != 0:
        fail(f"sqlcmd returned {done.returncode} for {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-only", action="store_true", help="skip the import, run the checks")
    parser.add_argument("--print-sql", action="store_true", help="write the filled scripts beside this file and connect to nothing")
    args = parser.parse_args()

    check_settings()
    m = manifest()
    print(f"build {m['built_at'][:19]}Z, release {m['epc_release']}, schema {m['schema_version']}")
    print(f"target {SERVER} / {DATABASE}: {MAIN_TABLE}")

    if args.print_sql:
        for label, sql in (("import_csv", filled_import(m)), ("check_loaded_digest", filled_check(m))):
            path = HERE / f"{label}.filled.sql"
            path.write_text(sql, encoding="utf-8")
            print(f"  wrote {path}")
        print("nothing was connected to or loaded")
        return 0

    print("verifying the files that were transferred")
    verify_files(m)
    if not args.check_only:
        print("importing, which drops and recreates the table")
        run(filled_import(m), "import_csv")
    print("checking the loaded table against the build")
    run(filled_check(m), "check_loaded_digest")
    print("done. Every check above must say pass; the script raises an error if one does not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
