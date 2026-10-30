-- The fallback for a cohort row without a UPRN: every dwelling in the postcode, each with its
-- latest certificate lodged on or before the cohort date. A postcode has many dwellings, so
-- this returns many rows per cohort row, and the project decides how to summarise them. What
-- it gives is a property of the postcode's dwellings, not of the person's dwelling.
--
-- Cohort: #cohort (cohort_row_id int, pseudo_id int, postcode nvarchar(10), cohort_date date).
-- cohort_row_id identifies the cohort row and must be unique; a person (pseudo_id) can appear
-- many times, at different dates or postcodes, and each row gets its own dwellings. The
-- postcode is compared as pc_norm: upper case, spaces removed.
--
-- The dwelling is uprn_sepcr, the register's own number, present in every row and one to one
-- with the Gazetteer UPRN where that exists, so a dwelling without a Gazetteer UPRN still
-- counts once. The tie rule is the same as the UPRN route: two or more certificates of one
-- dwelling lodged on the latest eligible day give dwelling_status = 'ambiguous_as_of' and no
-- values for that dwelling.
--
-- Status per cohort row (repeated on each of its rows):
--   no_postcode              the cohort postcode is empty
--   postcode_not_in_epc      no certificate in the release has that pc_norm
--   no_certificate_by_date   dwellings exist, none has a certificate lodged on or before the date
--   matched                  one row per dwelling with an eligible certificate

IF EXISTS (SELECT 1 FROM #cohort GROUP BY cohort_row_id HAVING COUNT(*) > 1)
    THROW 51000, 'cohort_row_id must be unique: one row per cohort observation.', 1;

WITH cohort AS (
    SELECT c.cohort_row_id, c.pseudo_id, c.cohort_date,
           NULLIF(UPPER(REPLACE(c.postcode, N' ', N'')), N'') AS pc_norm
    FROM #cohort AS c
),
eligible AS (
    SELECT c.cohort_row_id, e.uprn_sepcr, e.epc_release, e.source_year, e.source_row, e.lodgement_date_parsed,
           RANK() OVER (PARTITION BY c.cohort_row_id, e.uprn_sepcr ORDER BY e.lodgement_date_parsed DESC) AS rk
    FROM cohort AS c
    JOIN epc_domestic AS e
      ON e.pc_norm = c.pc_norm
     AND e.lodgement_date_parsed <= c.cohort_date
),
per_dwelling AS (
    SELECT cohort_row_id, uprn_sepcr, COUNT(*) AS n, MIN(lodgement_date_parsed) AS lodgement_date_parsed,
           MIN(epc_release) AS epc_release, MIN(source_year) AS source_year, MIN(source_row) AS source_row
    FROM eligible
    WHERE rk = 1
    GROUP BY cohort_row_id, uprn_sepcr
),
known AS (
    SELECT DISTINCT pc_norm FROM epc_domestic WHERE pc_norm IS NOT NULL
)
SELECT c.cohort_row_id, c.pseudo_id, c.cohort_date,
       CASE WHEN c.pc_norm IS NULL THEN 'no_postcode'
            WHEN k.pc_norm IS NULL THEN 'postcode_not_in_epc'
            WHEN d.cohort_row_id IS NULL THEN 'no_certificate_by_date'
            ELSE 'matched' END AS epc_status,
       d.uprn_sepcr AS dwelling,
       CASE WHEN d.n > 1 THEN 'ambiguous_as_of' WHEN d.n = 1 THEN 'matched' END AS dwelling_status,
       e.uprn_osg, e.lodgement_date_parsed AS epc_lodgement_date,
       DATEDIFF(day, e.lodgement_date_parsed, c.cohort_date) AS epc_age_days,
       e.CURRENT_ENERGY_RATING, e.current_energy_efficiency_int, e.total_floor_area_int,
       e.PROPERTY_TYPE, e.BUILT_FORM, e.CONSTRUCTION_AGE_BAND, e.TENURE
FROM cohort AS c
LEFT JOIN known AS k ON k.pc_norm = c.pc_norm
LEFT JOIN per_dwelling AS d ON d.cohort_row_id = c.cohort_row_id
LEFT JOIN epc_domestic AS e
       ON d.n = 1 AND e.epc_release = d.epc_release AND e.source_year = d.source_year AND e.source_row = d.source_row
ORDER BY c.cohort_row_id, d.uprn_sepcr;
