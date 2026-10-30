-- Join a cohort to its dwelling's certificate by UPRN: the certificate with the latest
-- inspection on or before the cohort date. A left join, so no cohort row disappears; one output
-- row per cohort row; the choice of certificate is explicit, never a default.
--
-- The inspection date is when the assessor saw the dwelling, so it is the date that says what
-- the home was like; the lodgement date is the administrative date of the certificate, the same
-- day or soon after (median 1 day, 90th percentile 18 days, 7% over a month). Both are returned:
-- the ten-year validity runs from lodgement. In 2,036 rows the lodgement date is before the
-- inspection date, a typo in one or the other; epc_lodged_before_inspection flags them.
--
-- Cohort: #cohort (cohort_row_id int NOT NULL PRIMARY KEY, pseudo_id int, uprn nvarchar(20), cohort_date date).
-- cohort_row_id identifies the cohort row and must be unique and not NULL: a person (pseudo_id) can appear
-- many times, at different dates or addresses, and each row gets its own certificate. The
-- query stops if cohort_row_id repeats. The UPRN may be padded with zeros or carry spaces: it
-- is compared as a bigint, never as text.
--
-- Status per cohort row:
--   no_uprn                  the cohort UPRN is empty or not an integer
--   uprn_not_in_epc          no certificate for that UPRN in the release (most dwellings)
--   no_certificate_by_date   certificates exist, none inspected on or before the date
--   ambiguous_as_of          two or more certificates inspected on the latest eligible day
--   matched                  one certificate; its columns and its age in days are returned
-- The query does not decide whether the certificate has expired (ten years from lodgement);
-- epc_age_days lets the project apply that rule or another.

IF EXISTS (SELECT 1 FROM #cohort WHERE cohort_row_id IS NULL)
    THROW 51000, 'cohort_row_id must not be NULL: a NULL key cannot be joined back to its result.', 1;
IF EXISTS (SELECT 1 FROM #cohort GROUP BY cohort_row_id HAVING COUNT(*) > 1)
    THROW 51000, 'cohort_row_id must be unique: one row per cohort observation.', 1;

WITH cohort AS (
    SELECT c.cohort_row_id, c.pseudo_id, c.cohort_date,
           TRY_CONVERT(bigint, NULLIF(LTRIM(RTRIM(c.uprn)), N'')) AS uprn_int
    FROM #cohort AS c
),
eligible AS (
    SELECT c.cohort_row_id, e.epc_release, e.source_year, e.source_row, e.inspection_date_parsed,
           RANK() OVER (PARTITION BY c.cohort_row_id ORDER BY e.inspection_date_parsed DESC) AS rk
    FROM cohort AS c
    JOIN epc_domestic AS e
      ON e.uprn_osg = c.uprn_int
     AND e.inspection_date_parsed <= c.cohort_date
),
latest AS (
    -- One row per cohort row: how many certificates share the latest eligible day, and the
    -- key of the one certificate when there is exactly one.
    SELECT cohort_row_id, COUNT(*) AS n, MIN(inspection_date_parsed) AS inspection_date_parsed,
           MIN(epc_release) AS epc_release, MIN(source_year) AS source_year, MIN(source_row) AS source_row
    FROM eligible
    WHERE rk = 1
    GROUP BY cohort_row_id
),
known AS (
    SELECT DISTINCT uprn_osg FROM epc_domestic WHERE uprn_osg IS NOT NULL
)
SELECT c.cohort_row_id, c.pseudo_id, c.cohort_date,
       CASE WHEN c.uprn_int IS NULL THEN 'no_uprn'
            WHEN k.uprn_osg IS NULL THEN 'uprn_not_in_epc'
            WHEN l.cohort_row_id IS NULL THEN 'no_certificate_by_date'
            WHEN l.n > 1 THEN 'ambiguous_as_of'
            ELSE 'matched' END AS epc_status,
       e.inspection_date_parsed AS epc_inspection_date, e.lodgement_date_parsed AS epc_lodgement_date,
       DATEDIFF(day, e.inspection_date_parsed, c.cohort_date) AS epc_age_days,
       CASE WHEN e.lodgement_date_parsed < e.inspection_date_parsed THEN 1
            WHEN e.inspection_date_parsed IS NOT NULL THEN 0 END AS epc_lodged_before_inspection,
       e.CURRENT_ENERGY_RATING, e.current_energy_efficiency_int, e.POTENTIAL_ENERGY_RATING,
       e.total_floor_area_int, e.PROPERTY_TYPE, e.BUILT_FORM, e.CONSTRUCTION_AGE_BAND, e.TENURE,
       e.MAIN_FUEL, e.historic_flag, e.rrn
FROM cohort AS c
LEFT JOIN known AS k ON k.uprn_osg = c.uprn_int
LEFT JOIN latest AS l ON l.cohort_row_id = c.cohort_row_id
LEFT JOIN epc_domestic AS e
       ON l.n = 1 AND e.epc_release = l.epc_release AND e.source_year = l.source_year AND e.source_row = l.source_row
ORDER BY c.cohort_row_id;
