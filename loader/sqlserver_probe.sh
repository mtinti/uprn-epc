#!/bin/sh
# Run the generated import and check scripts against a throwaway SQL Server 2022 container,
# time the digest, then probe what the Python tests cannot: that SQL Server renders a date, a
# timestamp, a bit, a bigint and a decimal(19,4) exactly as Python did, that an empty published
# cell is the empty string and an empty derived cell is NULL, that the cells with an embedded
# newline and a double quote survived BULK INSERT, and that the three join queries return the
# statuses the DuckDB tests expect. Usage: sh loader/sqlserver_probe.sh [results_dir]
# (needs docker; starts the container if absent). Default results dir: results/.
set -eu
cd "$(dirname "$0")/.."
R="${1:-results}"
PW='Epc_test_Pw0rd!'
C=epc_mssql
if ! docker ps --format '{{.Names}}' | grep -qx $C; then
  docker run --platform linux/amd64 -d --name $C -e ACCEPT_EULA=Y -e "MSSQL_SA_PASSWORD=$PW" -e MSSQL_PID=Developer \
    -e MSSQL_MEMORY_LIMIT_MB=6144 mcr.microsoft.com/mssql/server:2022-latest >/dev/null
fi
SQL="docker exec -i $C /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P $PW -C -b -t 0"
for i in $(seq 1 90); do $SQL -Q "SELECT 1" >/dev/null 2>&1 && break; sleep 2; done
$SQL -Q "IF DB_ID('epc') IS NULL CREATE DATABASE epc"
ROWS=$(python3 -c "import json;print(json.load(open('$R/manifest.json'))['csv']['rows'])")
TOTAL=$(python3 -c "import json;print(json.load(open('$R/manifest.json'))['csv']['digest']['total'])")
W=$(mktemp -d)
# SQL Server on Linux does not support CODEPAGE, so the container cannot read the UTF-8 file
# as the generated script does on Windows. The probe converts the CSV to UTF-16LE with a byte
# order mark and imports it as widechar; everything else in the script is unchanged. The
# Windows load uses the generated script as it is.
gunzip -c "$R/epc_domestic.csv.gz" | { printf '\377\376'; iconv -f UTF-8 -t UTF-16LE; } > "$W/epc_domestic.csv"
sed -e "s#/path/to/epc_domestic.csv#/tmp/epc/epc_domestic.csv#" \
    -e "s#CODEPAGE = '65001'#DATAFILETYPE = 'widechar'#" \
    -e "s#ROWTERMINATOR = '0x0a'#ROWTERMINATOR = '\\\\n'#" docs/sql/import_csv.sql > "$W/import.sql"
grep -q "DATAFILETYPE = 'widechar'" "$W/import.sql" || { echo "the import script was not adapted for Linux"; exit 1; }
sed "s#(N'epc_domestic', 0, 0, 1)#(N'epc_domestic', $ROWS, $TOTAL, 1)#" docs/sql/check_loaded_digest.sql > "$W/check.sql"
docker exec $C mkdir -p /tmp/epc
docker cp "$W/epc_domestic.csv" $C:/tmp/epc/epc_domestic.csv
docker cp "$W/import.sql" $C:/tmp/epc/import.sql
docker cp "$W/check.sql" $C:/tmp/epc/check.sql
echo "== import ($ROWS rows)"
START=$(date +%s)
$SQL -d epc -i /tmp/epc/import.sql
echo "import took $(( $(date +%s) - START ))s"
echo "== check_loaded_digest (expected rows $ROWS, total $TOTAL)"
START=$(date +%s)
$SQL -d epc -i /tmp/epc/check.sql -W -s '|'
echo "check took $(( $(date +%s) - START ))s"

echo "== probe: SQL rendering of chosen cells against the CSV text"
gunzip -c "$R/epc_domestic.csv.gz" > "$W/epc_domestic_utf8.csv"
python3 - "$W/epc_domestic_utf8.csv" > "$W/probe_expected.txt" <<'PY'
import csv, sys
csv.field_size_limit(1 << 24)
cols = ("uprn_osg", "lodgement_date_parsed", "created_at_parsed", "historic_flag", "energy_consumption_current_num",
        "total_floor_area_int", "rrn", "pc_norm", "ADDENDUM_TEXT", "OSG_REFERENCE_NUMBER", "datazone_2001")
with open(sys.argv[1], newline="", encoding="utf-8") as fh:
    r = csv.DictReader(fh)
    picked = []
    for row in r:
        k = (row["source_year"], row["source_row"])
        # The first two rows of the first file, a row with an empty UPRN and a row with an empty RRN.
        if k in {("2008", "1"), ("2008", "2")} or (row["OSG_REFERENCE_NUMBER"] == "" and len([p for p in picked if p[1]["OSG_REFERENCE_NUMBER"] == ""]) < 1) \
           or (row["rrn"] == "" and len([p for p in picked if p[1]["rrn"] == ""]) < 1):
            picked.append((k, row))
        if len(picked) >= 4 and all(x in [p[0] for p in picked] for x in [("2008", "1"), ("2008", "2")]):
            break
for (y, n), row in sorted(picked):
    for col in cols:
        print(f"{y}|{n}|{col}|{row[col]}")
PY
KEYS=$(python3 -c "
import sys
print(' OR '.join(f\"(source_year={l.split('|')[0]} AND source_row={l.split('|')[1]})\" for l in sorted(set(open('$W/probe_expected.txt').read().splitlines()), key=lambda l: l.split('|')[:2]) if l.split('|')[2]=='rrn'))")
$SQL -d epc -W -h -1 -s '|' -Q "SET NOCOUNT ON; SELECT source_year, source_row, c.col, ISNULL(c.val, '') FROM epc_domestic CROSS APPLY (VALUES
 ('uprn_osg', CONVERT(varchar(20), uprn_osg)), ('lodgement_date_parsed', CONVERT(varchar(10), lodgement_date_parsed, 23)),
 ('created_at_parsed', CONVERT(varchar(19), created_at_parsed, 120)), ('historic_flag', CONVERT(varchar(1), historic_flag)),
 ('energy_consumption_current_num', CONVERT(varchar(40), energy_consumption_current_num)), ('total_floor_area_int', CONVERT(varchar(20), total_floor_area_int)),
 ('rrn', rrn), ('pc_norm', pc_norm), ('ADDENDUM_TEXT', ADDENDUM_TEXT), ('OSG_REFERENCE_NUMBER', OSG_REFERENCE_NUMBER), ('datazone_2001', datazone_2001)) c(col, val)
 WHERE $KEYS ORDER BY source_year, source_row, c.col" | sed 's/ *|/|/g; s/ *$//' | grep -v '^$' > "$W/probe_actual.txt" || true
sort "$W/probe_expected.txt" > "$W/e.txt"; sort "$W/probe_actual.txt" > "$W/a.txt"
if diff "$W/e.txt" "$W/a.txt"; then echo "rendering: SQL Server text equals the CSV text for $(wc -l < "$W/e.txt") cells"; else echo "rendering: DIFFERENCES"; exit 1; fi

echo "== probe: empty against NULL, newline and quote cells"
$SQL -d epc -W -h -1 -s '|' -Q "SET NOCOUNT ON;
SELECT 'addendum_empty_not_null', COUNT(*) FROM epc_domestic WHERE ADDENDUM_TEXT = N'' AND ADDENDUM_TEXT IS NOT NULL
UNION ALL SELECT 'addendum_null', COUNT(*) FROM epc_domestic WHERE ADDENDUM_TEXT IS NULL
UNION ALL SELECT 'osg_text_empty', COUNT(*) FROM epc_domestic WHERE OSG_REFERENCE_NUMBER = N'' AND OSG_REFERENCE_NUMBER IS NOT NULL
UNION ALL SELECT 'uprn_osg_null', COUNT(*) FROM epc_domestic WHERE uprn_osg IS NULL
UNION ALL SELECT 'rrn_null', COUNT(*) FROM epc_domestic WHERE rrn IS NULL
UNION ALL SELECT 'rrn_text_empty', COUNT(*) FROM epc_domestic WHERE REPORT_REFERENCE_NUMBER = N''
UNION ALL SELECT 'brn_with_newline', COUNT(*) FROM epc_domestic WHERE BUILDING_REFERENCE_NUMBER LIKE N'%' + NCHAR(10) + N'%'
UNION ALL SELECT 'uprn_sepcr_null', COUNT(*) FROM epc_domestic WHERE uprn_sepcr IS NULL
UNION ALL SELECT 'historic_true', COUNT(*) FROM epc_domestic WHERE historic_flag = 1 AND HISTORIC = N'True'
UNION ALL SELECT 'historic_mismatch', COUNT(*) FROM epc_domestic WHERE CASE WHEN historic_flag = 1 THEN N'True' ELSE N'False' END <> HISTORIC
UNION ALL SELECT 'total_floor_area_mismatch', COUNT(*) FROM epc_domestic WHERE CONVERT(int, TOTAL_FLOOR_AREA) <> total_floor_area_int;" | sed 's/ *|/|/g; s/ *$//' | grep -v '^$' | tee "$W/empty_null.txt"
python3 - "$W/empty_null.txt" "$R/manifest.json" <<'PY'
import json, sys
got = dict(l.split("|") for l in open(sys.argv[1]).read().splitlines())
obs = json.load(open(sys.argv[2]))["observations"]["table"]
rows = json.load(open(sys.argv[2]))["csv"]["rows"]
expected = {"addendum_empty_not_null": rows, "addendum_null": 0, "osg_text_empty": obs["uprn_osg_empty_rows"], "uprn_osg_null": obs["uprn_osg_empty_rows"],
            "rrn_null": obs["rrn_empty_rows"], "rrn_text_empty": obs["rrn_empty_rows"],
            "brn_with_newline": obs["cells_with_embedded_newline"].get("BUILDING_REFERENCE_NUMBER", 0), "uprn_sepcr_null": 0,
            "historic_mismatch": 0, "total_floor_area_mismatch": 0}
bad = {k: (got.get(k), v) for k, v in expected.items() if int(got.get(k, -1)) != v}
if bad:
    print("empty/NULL: DIFFERENCES", bad); sys.exit(1)
print("empty/NULL: every count equals the manifest")
PY

echo "== probe: the join statuses, asserted"
$SQL -d epc -W -h -1 -s '|' -Q "SET NOCOUNT ON;
CREATE TABLE #cohort (cohort_row_id int, pseudo_id int, uprn nvarchar(20), cohort_date date);
DECLARE @u bigint = (SELECT TOP (1) uprn_osg FROM epc_domestic WHERE uprn_osg IS NOT NULL AND historic_flag = 0 GROUP BY uprn_osg HAVING COUNT(*) = 1 ORDER BY uprn_osg);
DECLARE @d date = (SELECT MAX(lodgement_date_parsed) FROM epc_domestic WHERE uprn_osg = @u);
INSERT INTO #cohort VALUES (1, 1, CONVERT(nvarchar(20), @u), @d), (2, 1, RIGHT(REPLICATE(N'0', 12) + CONVERT(nvarchar(20), @u), 12), @d),
  (3, 1, CONVERT(nvarchar(20), @u), '2000-01-01'), (4, 2, N'1', '2030-01-01'), (5, 2, N'', '2030-01-01'), (6, 3, NULL, '2030-01-01'), (7, 3, N'x', '2030-01-01');
$(sed -n '/^IF EXISTS (SELECT 1 FROM #cohort/,$p' docs/sql/join_by_uprn.sql)
" | sed 's/ *|/|/g; s/ *$//' | grep -v '^$' | cut -d'|' -f1,4 > "$W/join_actual.txt"
printf '1|matched\n2|matched\n3|no_certificate_by_date\n4|uprn_not_in_epc\n5|no_uprn\n6|no_uprn\n7|no_uprn\n' > "$W/join_expected.txt"
if diff "$W/join_expected.txt" "$W/join_actual.txt"; then echo "join: 7 cohort rows returned once each with the expected status"; else echo "join: DIFFERENCES"; exit 1; fi
echo "== probe: the cohort key guards, asserted (a NULL key and a repeated key each stop the query)"
for CASE in "(1, 1, N'1', '2030-01-01'), (NULL, 1, N'1', '2030-01-01')" "(1, 1, N'1', '2030-01-01'), (1, 2, N'1', '2030-01-01')"; do
  OUT=$($SQL -d epc -W -h -1 -s '|' -Q "SET NOCOUNT ON;
CREATE TABLE #cohort (cohort_row_id int, pseudo_id int, uprn nvarchar(20), cohort_date date);
INSERT INTO #cohort VALUES $CASE;
$(sed -n '/^IF EXISTS (SELECT 1 FROM #cohort/,$p' docs/sql/join_by_uprn.sql)
" 2>&1 || true)
  echo "$OUT" | grep -q "cohort_row_id must" || { echo "guard: the query did not stop for $CASE"; echo "$OUT" | head -5; exit 1; }
done
echo "guards: both cases stopped with the expected message"
echo "== done; probe files in $W"
