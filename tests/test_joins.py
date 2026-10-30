"""The example join queries, run against a small table in DuckDB with the cases the plan names.

The queries are T-SQL for SQL Server. DuckDB runs them after five textual substitutions that
change spelling and nothing else: TRY_CONVERT(bigint, x) to TRY_CAST(x AS BIGINT), DATEDIFF(day,
a, b) to datediff('day', a, b), N'...' to '...', #cohort to cohort, and the two IF EXISTS ... THROW
guards removed (their presence is asserted; the container probe exercises them in T-SQL). The container probe
(loader/sqlserver_probe.sh) runs the T-SQL itself against SQL Server with the same cases."""

import datetime as dt
import re
from pathlib import Path

import duckdb
import pytest

SQL = Path(__file__).resolve().parent.parent / "docs" / "sql"
GUARD = re.compile(r"IF EXISTS \(SELECT 1 FROM #cohort WHERE cohort_row_id IS NULL\)\n\s*THROW 51000, '[^']*', 1;\n"
                   r"IF EXISTS \(SELECT 1 FROM #cohort GROUP BY cohort_row_id HAVING COUNT\(\*\) > 1\)\n\s*THROW 51000, '[^']*', 1;\n")


def duck(sql: str) -> str:
    assert GUARD.search(sql), "the query must stop on a NULL or repeated cohort_row_id"
    sql = GUARD.sub("", sql)
    sql = re.sub(r"TRY_CONVERT\(bigint, (.*?)\) AS uprn_int", r"TRY_CAST(\1 AS BIGINT) AS uprn_int", sql)
    sql = sql.replace("DATEDIFF(day, ", "datediff('day', ")
    sql = re.sub(r"\bN'", "'", sql)
    sql = sql.replace("#cohort", "cohort")
    return sql


COLUMNS = ["epc_release", "source_year", "source_row", "uprn_sepcr", "uprn_osg", "pc_norm", "inspection_date_parsed", "lodgement_date_parsed",
           "historic_flag", "rrn", "CURRENT_ENERGY_RATING", "current_energy_efficiency_int", "POTENTIAL_ENERGY_RATING",
           "total_floor_area_int", "PROPERTY_TYPE", "BUILT_FORM", "CONSTRUCTION_AGE_BAND", "TENURE", "MAIN_FUEL"]


def cert(row, year, uprn_sepcr, uprn_osg, pc, lodged, historic, rating="D", inspected=None):
    """A certificate; the inspection is on the lodgement day unless `inspected` says otherwise."""
    return ("2026Q2", year, row, uprn_sepcr, uprn_osg, pc, dt.date.fromisoformat(inspected or lodged), dt.date.fromisoformat(lodged), historic,
            f"{year}-{row:04d}-0000-0000-0001",
            rating, 65, "C", 85, "House", "Detached", "1950-1964", "Owner-occupied", "mains gas")


@pytest.fixture
def con():
    c = duckdb.connect()
    c.execute("CREATE TABLE epc_domestic (epc_release VARCHAR, source_year SMALLINT, source_row INTEGER, uprn_sepcr BIGINT, uprn_osg BIGINT, "
              "pc_norm VARCHAR, inspection_date_parsed DATE, lodgement_date_parsed DATE, historic_flag BOOLEAN, rrn VARCHAR, CURRENT_ENERGY_RATING VARCHAR, "
              "current_energy_efficiency_int INTEGER, POTENTIAL_ENERGY_RATING VARCHAR, total_floor_area_int INTEGER, PROPERTY_TYPE VARCHAR, "
              "BUILT_FORM VARCHAR, CONSTRUCTION_AGE_BAND VARCHAR, TENURE VARCHAR, MAIN_FUEL VARCHAR)")
    rows = [
        # UPRN 35000001: three certificates, 2010, 2015, 2020; only the last current. The 2020 one was
        # inspected twelve days before it was lodged.
        cert(1, 2010, 1000000001, 35000001, "FK101AA", "2010-06-01", True, "E"),
        cert(1, 2015, 1000000001, 35000001, "FK101AA", "2015-06-01", True, "D"),
        cert(1, 2020, 1000000001, 35000001, "FK101AA", "2020-06-01", False, "C", inspected="2020-05-20"),
        # UPRN 35000002: two certificates on the same day in 2012, then one in 2018.
        cert(2, 2012, 1000000002, 35000002, "FK101AA", "2012-03-03", True, "F"),
        cert(3, 2012, 1000000002, 35000002, "FK101AA", "2012-03-03", True, "E"),
        cert(2, 2018, 1000000002, 35000002, "FK101AA", "2018-01-01", False, "D"),
        # UPRN 35000003: two current certificates (the 22 of the release).
        cert(4, 2019, 1000000003, 35000003, "FK101AB", "2019-01-01", False, "B"),
        cert(5, 2019, 1000000003, 35000003, "FK101AB", "2019-02-01", False, "B"),
        # UPRN 35000004: only historic certificates; lodged before its inspection date, a publisher typo.
        cert(6, 2011, 1000000004, 35000004, "FK101AB", "2011-01-01", True, "G", inspected="2011-01-05"),
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


DATED = "CREATE TABLE cohort (cohort_row_id INTEGER, pseudo_id INTEGER, uprn VARCHAR, cohort_date DATE)"


def test_join_by_uprn_statuses_and_dates(con):
    rows = run(con, "join_by_uprn.sql", DATED, [
        (1, 101, "35000001", dt.date(2009, 1, 1)),       # before the first certificate
        (2, 102, "35000001", dt.date(2015, 6, 1)),       # on the day of the second
        (3, 103, "35000001", dt.date(2024, 1, 1)),       # after the third
        (4, 104, "000035000001", dt.date(2024, 1, 1)),   # padded: the same dwelling
        (5, 105, " 35000002 ", dt.date(2012, 6, 1)),     # two on the latest eligible day
        (6, 106, "35000002", dt.date(2019, 1, 1)),       # a later single certificate is eligible
        (7, 107, "99999999", dt.date(2024, 1, 1)),       # no certificate ever
        (8, 108, "", dt.date(2024, 1, 1)),
        (9, 109, None, dt.date(2024, 1, 1)),
        (10, 110, "ABC", dt.date(2024, 1, 1)),
        (11, 111, "35000003", dt.date(2024, 1, 1)),      # two current, different days: the later wins
        (12, 112, "35000001", dt.date(2020, 5, 25)),     # inspected before the date, lodged after it: the 2020 certificate
    ])
    assert len(rows) == 12
    by_id = {r[0]: r for r in rows}
    # Columns: 0 cohort_row_id, 1 pseudo_id, 2 cohort_date, 3 status, 4 inspection date, 5 lodgement date,
    # 6 age in days from the inspection, 7 lodged-before-inspection flag, 8 rating.
    status = {k: v[3] for k, v in by_id.items()}
    assert status == {1: "no_certificate_by_date", 2: "matched", 3: "matched", 4: "matched", 5: "ambiguous_as_of",
                      6: "matched", 7: "uprn_not_in_epc", 8: "no_uprn", 9: "no_uprn", 10: "no_uprn", 11: "matched", 12: "matched"}
    assert by_id[2][4] == dt.date(2015, 6, 1) and by_id[2][6] == 0 and by_id[2][8] == "D"
    assert by_id[3][4] == dt.date(2020, 5, 20) and by_id[3][5] == dt.date(2020, 6, 1) and by_id[3][8] == "C" and by_id[4][8] == "C"
    assert by_id[5][4] is None and by_id[5][5] is None and by_id[5][7] is None and by_id[5][8] is None
    assert by_id[6][4] == dt.date(2018, 1, 1) and by_id[6][6] == 365
    assert by_id[11][4] == dt.date(2019, 2, 1)
    assert by_id[12][4] == dt.date(2020, 5, 20) and by_id[12][6] == 5 and by_id[12][8] == "C"    # by lodgement it would have been the 2015 D
    assert all(by_id[k][7] == 0 for k in (2, 3, 4, 6, 11, 12)) and by_id[1][7] is None
    assert [r[1] for r in rows] == [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112]


def test_one_person_many_rows_each_row_gets_its_own_certificate(con):
    """A longitudinal cohort repeats a person at different dates and addresses. Each row must
    keep its own eligible set: the 2015 observation must not receive the 2020 certificate, and
    repeated rows must not read as ambiguity."""
    rows = run(con, "join_by_uprn.sql", DATED, [
        (1, 7, "35000001", dt.date(2015, 6, 1)),
        (2, 7, "35000001", dt.date(2024, 1, 1)),
        (3, 7, "35000001", dt.date(2024, 1, 1)),    # a duplicate observation
        (4, 7, "35000004", dt.date(2024, 1, 1)),    # the same person at another address
        (5, 7, "35000002", dt.date(2012, 6, 1)),    # a real same-day tie stays ambiguous
    ])
    by_id = {r[0]: r for r in rows}
    assert len(rows) == 5 and all(r[1] == 7 for r in rows)
    assert by_id[1][3] == "matched" and by_id[1][4] == dt.date(2015, 6, 1) and by_id[1][8] == "D"
    assert by_id[2][3] == "matched" and by_id[2][4] == dt.date(2020, 5, 20)
    assert by_id[3][3] == "matched" and by_id[3][4] == dt.date(2020, 5, 20)
    # The certificate lodged before its inspection: dated by the inspection, flagged.
    assert by_id[4][3] == "matched" and by_id[4][4] == dt.date(2011, 1, 5) and by_id[4][5] == dt.date(2011, 1, 1) and by_id[4][7] == 1 and by_id[4][8] == "G"
    assert by_id[5][3] == "ambiguous_as_of"


def test_join_latest_by_uprn_statuses(con):
    rows = run(con, "join_latest_by_uprn.sql", "CREATE TABLE cohort (cohort_row_id INTEGER, pseudo_id INTEGER, uprn VARCHAR)", [
        (1, 7, "35000001"), (2, 7, "35000003"), (3, 8, "35000004"), (4, 8, "99999999"), (5, 9, ""), (6, 9, "000035000002"),
    ])
    status = {r[0]: r[2] for r in rows}
    assert status == {1: "matched", 2: "ambiguous_latest", 3: "no_current_certificate", 4: "uprn_not_in_epc", 5: "no_uprn", 6: "matched"}
    rating = {r[0]: r[4] for r in rows}
    assert rating[1] == "C" and rating[6] == "D"
    assert len(rows) == 6 and [r[1] for r in rows] == [7, 7, 8, 8, 9, 9]


def test_join_by_postcode_one_row_per_dwelling(con):
    rows = run(con, "join_by_postcode.sql", "CREATE TABLE cohort (cohort_row_id INTEGER, pseudo_id INTEGER, postcode VARCHAR, cohort_date DATE)", [
        (1, 7, "fk10 1ab", dt.date(2024, 1, 1)),   # three dwellings: 35000003 (two current, later wins), 35000004 (historic only), no-UPRN dwelling
        (2, 7, "FK10 1AA", dt.date(2012, 3, 3)),   # the same person: 35000001 has 2010; 35000002 has the same-day pair
        (3, 8, "FK10 1AA", dt.date(2009, 1, 1)),   # dwellings exist, no certificate yet
        (4, 8, "ZZ1 1ZZ", dt.date(2024, 1, 1)),
        (5, 9, "", dt.date(2024, 1, 1)),
    ])
    one = [r for r in rows if r[0] == 1]
    assert [r[3] for r in one] == ["matched"] * 3
    assert sorted(r[4] for r in one) == [1000000003, 1000000004, 1000000005]
    dwelling = {r[4]: r for r in one}
    # Columns: 4 dwelling, 5 dwelling_status, 6 uprn_osg, 7 inspection date, 8 lodgement date, 9 age, 10 flag, 11 rating.
    assert dwelling[1000000003][5] == "matched" and dwelling[1000000003][7] == dt.date(2019, 2, 1)
    assert dwelling[1000000004][11] == "G" and dwelling[1000000004][10] == 1 and dwelling[1000000004][8] == dt.date(2011, 1, 1)
    assert dwelling[1000000005][6] is None and dwelling[1000000005][10] == 0
    two = {r[4]: r for r in rows if r[0] == 2}
    assert two[1000000001][5] == "matched" and two[1000000001][7] == dt.date(2010, 6, 1)
    assert two[1000000002][5] == "ambiguous_as_of" and two[1000000002][7] is None and two[1000000002][10] is None
    assert [r[3] for r in rows if r[0] == 3] == ["no_certificate_by_date"]
    assert [r[3] for r in rows if r[0] == 4] == ["postcode_not_in_epc"]
    assert [r[3] for r in rows if r[0] == 5] == ["no_postcode"]


def test_every_join_declares_the_cohort_key_not_null():
    for name in ("join_by_uprn.sql", "join_latest_by_uprn.sql", "join_by_postcode.sql"):
        sql = (SQL / name).read_text()
        assert "cohort_row_id int NOT NULL PRIMARY KEY" in sql, name
        assert GUARD.search(sql), name
