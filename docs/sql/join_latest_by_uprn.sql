-- Join a cohort to its dwelling's current certificate by UPRN, without a date: the one
-- certificate with HISTORIC = False. A left join; one row per cohort row.
--
-- Cohort: #cohort (pseudo_id int, uprn nvarchar(20)).
--
-- Status per cohort row:
--   no_uprn                  the cohort UPRN is empty or not an integer
--   uprn_not_in_epc          no certificate for that UPRN in the release
--   no_current_certificate   certificates exist and every one is HISTORIC = True
--   ambiguous_latest         two or more HISTORIC = False certificates (22 UPRNs in 2026Q2)
--   matched                  one current certificate; its columns are returned

WITH cohort AS (
    SELECT c.pseudo_id, TRY_CONVERT(bigint, NULLIF(LTRIM(RTRIM(c.uprn)), N'')) AS uprn_int
    FROM #cohort AS c
),
current_certs AS (
    SELECT uprn_osg, COUNT(*) AS n,
           MIN(epc_release) AS epc_release, MIN(source_year) AS source_year, MIN(source_row) AS source_row
    FROM epc_domestic
    WHERE uprn_osg IS NOT NULL AND historic_flag = 0
    GROUP BY uprn_osg
),
known AS (
    SELECT DISTINCT uprn_osg FROM epc_domestic WHERE uprn_osg IS NOT NULL
)
SELECT c.pseudo_id,
       CASE WHEN c.uprn_int IS NULL THEN 'no_uprn'
            WHEN k.uprn_osg IS NULL THEN 'uprn_not_in_epc'
            WHEN cc.uprn_osg IS NULL THEN 'no_current_certificate'
            WHEN cc.n > 1 THEN 'ambiguous_latest'
            ELSE 'matched' END AS epc_status,
       e.lodgement_date_parsed AS epc_lodgement_date,
       e.CURRENT_ENERGY_RATING, e.current_energy_efficiency_int, e.POTENTIAL_ENERGY_RATING,
       e.total_floor_area_int, e.PROPERTY_TYPE, e.BUILT_FORM, e.CONSTRUCTION_AGE_BAND, e.TENURE,
       e.MAIN_FUEL, e.rrn
FROM cohort AS c
LEFT JOIN known AS k ON k.uprn_osg = c.uprn_int
LEFT JOIN current_certs AS cc ON cc.uprn_osg = c.uprn_int
LEFT JOIN epc_domestic AS e
       ON cc.n = 1 AND e.epc_release = cc.epc_release AND e.source_year = cc.source_year AND e.source_row = cc.source_row
ORDER BY c.pseudo_id;
