"""The example join queries, run against a small table in DuckDB with the cases the plan names.

The queries are T-SQL for SQL Server. DuckDB runs them after four textual substitutions that
change spelling and nothing else: TRY_CONVERT(bigint, x) to TRY_CAST(x AS BIGINT), DATEDIFF(day,
a, b) to datediff('day', a, b), N'...' to '...', and #cohort to cohort. The container probe
(loader/sqlserver_probe.sh) runs the T-SQL itself against SQL Server with the same cases."""

import datetime as dt
import re
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

SQL = Path(__file__).resolve().parent.parent / "docs" / "sql"


def duck(sql: str) -> str:
    sql = re.sub(r"TRY_CONVERT\(bigint, (.*?)\) AS uprn_int", r"TRY_CAST(\1 AS BIGINT) AS uprn_int", sql)
    sql = sql.replace("DATEDIFF(day, ", "datediff('day', ")
    sql = re.sub(r"\bN'", "'", sql)
    sql = sql.replace("#cohort", "cohort")
    return sql


COLUMNS = ["epc_release", "source_year", "source_row", "uprn_sepcr", "uprn_osg", "pc_norm", "lodgement_date_parsed",
           "historic_flag", "rrn", "CURRENT_ENERGY_RATING", "current_energy_efficiency_int", "POTENTIAL_ENERGY_RATING",
           "total_floor_area_int", "PROPERTY_TYPE", "BUILT_FORM", "CONSTRUCTION_AGE_BAND", "TENURE", "MAIN_FUEL"]


def cert(row, year, uprn_sepcr, uprn_osg, pc, lodged, historic, rating="D"):
    return ("2026Q2", year, row, uprn_sepcr, uprn_osg, pc, dt.date.fromisoformat(lodged), historic, f"{year}-{row:04d}-0000-0000-0001",
            rating, 65, "C", 85, "House", "Detached", "1950-1964", "Owner-occupied", "mains gas")


@pytest.fixture
def con():
    c = duckdb.connect()
    c.execute("CREATE TABLE epc_domestic (epc_release VARCHAR, source_year SMALLINT, source_row INTEGER, uprn_sepcr BIGINT, uprn_osg BIGINT, "
              "pc_norm VARCHAR, lodgement_date_parsed DATE, historic_flag BOOLEAN, rrn VARCHAR, CURRENT_ENERGY_RATING VARCHAR, "
              "current_energy_efficiency_int INTEGER, POTENTIAL_ENERGY_RATING VARCHAR, total_floor_area_int INTEGER, PROPERTY_TYPE VARCHAR, "
              "BUILT_FORM VARCHAR, CONSTRUCTION_AGE_BAND VARCHAR, TENURE VARCHAR, MAIN_FUEL VARCHAR)")
    rows = [
        # UPRN 35000001: three certificates, 2010, 2015, 2020; only the last current.
        cert(1, 2010, 1000000001, 35000001, "FK101AA", "2010-06-01", True, "E"),
        cert(1, 2015, 1000000001, 35000001, "FK101AA", "2015-06-01", True, "D"),
        cert(1, 2020, 1000000001, 35000001, "FK101AA", "2020-06-01", False, "C"),
        # UPRN 35000002: two certificates on the same day in 2012, then one in 2018.
        cert(2, 2012, 1000000002, 35000002, "FK101AA", "2012-03-03", True, "F"),
        cert(3, 2012, 1000000002, 35000002, "FK101AA", "2012-03-03", True, "E"),
        cert(2, 2018, 1000000002, 35000002, "FK101AA", "2018-01-01", False, "D"),
        # UPRN 35000003: two current certificates (the 22 of the release).
        cert(4, 2019, 1000000003, 35000003, "FK101AB", "2019-01-01", False, "B"),
        cert(5, 2019, 1000000003, 35000003, "FK101AB", "2019-02-01", False, "B"),
        # UPRN 35000004: only historic certificates.
        cert(6, 2011, 1000000004, 35000004, "FK101AB", "2011-01-01", True, "G"),
        # A dwelling with no Gazetteer UPRN, in FK10 1AB.
        cert(7, 2016, 1000000005, None, "FK101AB", "2016-05-05", False, "D"),
    ]
    c.executemany("INSERT INTO epc_domestic VALUES (" + ",".join("?" * len(COLUMNS)) + ")", rows)
    return c


def run(con, name, cohort_ddl, cohort_rows):
    con.execute("DROP TABLE IF EXISTS cohort")
    con.execute(cohort_ddl)
    con.executemany(f"INSERT INTO cohort VALUES ({','.join('?' * len(cohort_rows[0]))})", cohort_rows)
    return con.execute(duck((SQL / name).read_text())).fetchall()


def test_join_by_uprn_statuses_and_dates(con):
    rows = run(con, "join_by_uprn.sql", "CREATE TABLE cohort (pseudo_id INTEGER, uprn VARCHAR, cohort_date DATE)", [
        (1, "35000001", dt.date(2009, 1, 1)),       # before the first certificate
        (2, "35000001", dt.date(2015, 6, 1)),       # on the day of the second
        (3, "35000001", dt.date(2024, 1, 1)),       # after the third
        (4, "000035000001", dt.date(2024, 1, 1)),   # padded: the same dwelling
        (5, " 35000002 ", dt.date(2012, 6, 1)),     # two on the latest eligible day
        (6, "35000002", dt.date(2019, 1, 1)),       # a later single certificate is eligible
        (7, "99999999", dt.date(2024, 1, 1)),       # no certificate ever
        (8, "", dt.date(2024, 1, 1)),
        (9, None, dt.date(2024, 1, 1)),
        (10, "ABC", dt.date(2024, 1, 1)),
        (11, "35000003", dt.date(2024, 1, 1)),      # two current, different days: the later wins
    ])
    assert len(rows) == 11
    by_id = {r[0]: r for r in rows}
    status = {k: v[2] for k, v in by_id.items()}
    assert status == {1: "no_certificate_by_date", 2: "matched", 3: "matched", 4: "matched", 5: "ambiguous_as_of",
                      6: "matched", 7: "uprn_not_in_epc", 8: "no_uprn", 9: "no_uprn", 10: "no_uprn", 11: "matched"}
    assert by_id[2][3] == dt.date(2015, 6, 1) and by_id[2][4] == 0 and by_id[2][5] == "D"
    assert by_id[3][3] == dt.date(2020, 6, 1) and by_id[3][5] == "C" and by_id[4][5] == "C"
    assert by_id[5][3] is None and by_id[5][5] is None
    assert by_id[6][3] == dt.date(2018, 1, 1) and by_id[6][4] == 365
    assert by_id[11][3] == dt.date(2019, 2, 1)


def test_join_latest_by_uprn_statuses(con):
    rows = run(con, "join_latest_by_uprn.sql", "CREATE TABLE cohort (pseudo_id INTEGER, uprn VARCHAR)", [
        (1, "35000001"), (2, "35000003"), (3, "35000004"), (4, "99999999"), (5, ""), (6, "000035000002"),
    ])
    status = {r[0]: r[1] for r in rows}
    assert status == {1: "matched", 2: "ambiguous_latest", 3: "no_current_certificate", 4: "uprn_not_in_epc", 5: "no_uprn", 6: "matched"}
    assert {r[0]: r[3] for r in rows}[1] == "C" and {r[0]: r[3] for r in rows}[6] == "D"
    assert len(rows) == 6


def test_join_by_postcode_one_row_per_dwelling(con):
    rows = run(con, "join_by_postcode.sql", "CREATE TABLE cohort (pseudo_id INTEGER, postcode VARCHAR, cohort_date DATE)", [
        (1, "fk10 1ab", dt.date(2024, 1, 1)),   # three dwellings: 35000003 (two current, later wins), 35000004 (historic only), no-UPRN dwelling
        (2, "FK10 1AA", dt.date(2012, 3, 3)),   # 35000001 has 2010; 35000002 has the same-day pair
        (3, "FK10 1AA", dt.date(2009, 1, 1)),   # dwellings exist, no certificate yet
        (4, "ZZ1 1ZZ", dt.date(2024, 1, 1)),
        (5, "", dt.date(2024, 1, 1)),
    ])
    one = [r for r in rows if r[0] == 1]
    assert [r[2] for r in one] == ["matched"] * 3
    assert sorted(r[3] for r in one) == [1000000003, 1000000004, 1000000005]
    dwelling = {r[3]: r for r in one}
    assert dwelling[1000000003][4] == "matched" and dwelling[1000000003][6] == dt.date(2019, 2, 1)
    assert dwelling[1000000004][8] == "G" and dwelling[1000000005][5] is None
    two = {r[3]: r for r in rows if r[0] == 2}
    assert two[1000000001][4] == "matched" and two[1000000001][6] == dt.date(2010, 6, 1)
    assert two[1000000002][4] == "ambiguous_as_of" and two[1000000002][6] is None
    assert [r[2] for r in rows if r[0] == 3] == ["no_certificate_by_date"]
    assert [r[2] for r in rows if r[0] == 4] == ["postcode_not_in_epc"]
    assert [r[2] for r in rows if r[0] == 5] == ["no_postcode"]
