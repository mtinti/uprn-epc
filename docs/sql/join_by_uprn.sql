-- Join a cohort to its dwelling's certificate by UPRN: the latest certificate lodged on or
-- before the cohort date. A left join, so no cohort row disappears; one row per cohort row;
-- the choice of certificate is explicit, never a default.
--
-- Cohort: #cohort (pseudo_id int, uprn nvarchar(20), cohort_date date). The UPRN may be padded
-- with zeros or carry spaces: it is compared as a bigint, never as text.
--
-- Status per cohort row:
--   no_uprn                  the cohort UPRN is empty or not an integer
--   uprn_not_in_epc          no certificate for that UPRN in the release (most dwellings)
--   no_certificate_by_date   certificates exist, none lodged on or before the date
--   ambiguous_as_of          two or more certificates lodged on the latest eligible day
--   matched                  one certificate; its columns and its age in days are returned
-- The query does not decide whether the certificate has expired (ten years from lodgement);
-- epc_age_days lets the project apply that rule or another.

WITH cohort AS (
    SELECT c.pseudo_id, c.cohort_date,
           TRY_CONVERT(bigint, NULLIF(LTRIM(RTRIM(c.uprn)), N'')) AS uprn_int
    FROM #cohort AS c
),
eligible AS (
    SELECT c.pseudo_id, e.epc_release, e.source_year, e.source_row, e.lodgement_date_parsed,
           RANK() OVER (PARTITION BY c.pseudo_id ORDER BY e.lodgement_date_parsed DESC) AS rk
    FROM cohort AS c
    JOIN epc_domestic AS e
      ON e.uprn_osg = c.uprn_int
     AND e.lodgement_date_parsed <= c.cohort_date
),
latest AS (
    -- One row per cohort row: how many certificates share the latest eligible day, and the
    -- key of the one certificate when there is exactly one.
    SELECT pseudo_id, COUNT(*) AS n, MIN(lodgement_date_parsed) AS lodgement_date_parsed,
           MIN(epc_release) AS epc_release, MIN(source_year) AS source_year, MIN(source_row) AS source_row
    FROM eligible
    WHERE rk = 1
    GROUP BY pseudo_id
),
known AS (
    SELECT DISTINCT uprn_osg FROM epc_domestic WHERE uprn_osg IS NOT NULL
)
SELECT c.pseudo_id, c.cohort_date,
       CASE WHEN c.uprn_int IS NULL THEN 'no_uprn'
            WHEN k.uprn_osg IS NULL THEN 'uprn_not_in_epc'
            WHEN l.pseudo_id IS NULL THEN 'no_certificate_by_date'
            WHEN l.n > 1 THEN 'ambiguous_as_of'
            ELSE 'matched' END AS epc_status,
       e.lodgement_date_parsed AS epc_lodgement_date,
       DATEDIFF(day, e.lodgement_date_parsed, c.cohort_date) AS epc_age_days,
       e.CURRENT_ENERGY_RATING, e.current_energy_efficiency_int, e.POTENTIAL_ENERGY_RATING,
       e.total_floor_area_int, e.PROPERTY_TYPE, e.BUILT_FORM, e.CONSTRUCTION_AGE_BAND, e.TENURE,
       e.MAIN_FUEL, e.historic_flag, e.rrn
FROM cohort AS c
LEFT JOIN known AS k ON k.uprn_osg = c.uprn_int
LEFT JOIN latest AS l ON l.pseudo_id = c.pseudo_id
LEFT JOIN epc_domestic AS e
       ON l.n = 1 AND e.epc_release = l.epc_release AND e.source_year = l.source_year AND e.source_row = l.source_row
ORDER BY c.pseudo_id;
