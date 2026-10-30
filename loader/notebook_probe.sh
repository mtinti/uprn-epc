#!/bin/sh
# Run the upload notebook, as generated, against a throwaway SQL Server 2022 container through
# pyodbc from a second container that stands in for an analyst's machine (Python, pyodbc, the
# Microsoft ODBC driver, a Jupyter kernel). A fixture release of 15 rows carries the awkward
# cells of the real extract and the cases the notebook review asked for; the harness runs the
# notebook's own cells under eleven scenarios. Usage: sh loader/notebook_probe.sh [scratch_dir]
# (needs docker and the project's Python environment). Results: <scratch_dir>/out/results.json
# and one executed notebook per scenario. Default scratch dir: results/.notebook_probe/.
set -eu
cd "$(dirname "$0")/.."
SCRATCH="${1:-results/.notebook_probe}"
PW='Epc_test_Pw0rd!'
C=epc_mssql
NET=epc_probe
IMG=epc-notebook-test:1
if ! docker ps --format '{{.Names}}' | grep -qx $C; then
  docker run --platform linux/amd64 -d --name $C -e ACCEPT_EULA=Y -e "MSSQL_SA_PASSWORD=$PW" -e MSSQL_PID=Developer \
    -e MSSQL_MEMORY_LIMIT_MB=6144 mcr.microsoft.com/mssql/server:2022-latest >/dev/null
fi
docker network inspect $NET >/dev/null 2>&1 || docker network create $NET >/dev/null
docker network inspect $NET --format '{{range .Containers}}{{.Name}} {{end}}' | grep -qw $C || docker network connect $NET $C
docker image inspect $IMG >/dev/null 2>&1 || docker build -t $IMG loader/notebook_probe
SQL="docker exec -i $C /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P $PW -C -b"
for i in $(seq 1 90); do $SQL -Q "SELECT 1" >/dev/null 2>&1 && break; sleep 2; done
echo "== fixture release and its notebook"
python3 loader/notebook_probe/build_fixture.py "$SCRATCH"
mkdir -p "$SCRATCH/out"
rm -f "$SCRATCH"/out/*.ipynb "$SCRATCH"/out/results.json
echo "== notebook scenarios"
docker run --rm --network $NET -e SA_PW="$PW" -e SERVER=$C \
  -v "$(cd "$(dirname "$0")/notebook_probe" && pwd)/harness.py:/work/harness.py:ro" \
  -v "$(cd "$SCRATCH/delivery" && pwd):/data/delivery:ro" -v "$(cd "$SCRATCH/out" && pwd):/out" \
  $IMG python -u harness.py 2>&1 | grep -v "UserWarning\|warnings.warn"
