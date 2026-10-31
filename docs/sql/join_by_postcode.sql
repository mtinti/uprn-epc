-- The fallback for a cohort row without a UPRN: every dwelling in the postcode, each with its
-- certificate of the latest inspection on or before the cohort date (see join_by_uprn.sql for
-- why the inspection date and not the lodgement date). A postcode has many dwellings, so
-- this returns many rows per cohort row, and the project decides how to summarise them. What
-- it gives is a property of the postcode's dwellings, not of the person's dwelling.
--
-- Cohort: #cohort (cohort_row_id int NOT NULL PRIMARY KEY, pseudo_id int, postcode nvarchar(10), cohort_date date).
-- cohort_row_id identifies the cohort row and must be unique and not NULL; a person (pseudo_id) can appear
-- many times, at different dates or postcodes, and each row gets its own dwellings. The
-- postcode is compared as pc_norm: upper case, spaces removed.
--
-- The dwelling is uprn_sepcr, the register's own number, present in every row and one to one
-- with the Gazetteer UPRN where that exists, so a dwelling without a Gazetteer UPRN still
-- counts once. The tie rule is the same as the UPRN route: among two or more certificates of
-- one dwelling inspected on the latest eligible day, the current one (HISTORIC = False), then
-- the one lodged on the register last; if still tied, dwelling_status = 'ambiguous_as_of' and no
-- values for that dwelling. epc_tie_candidates and epc_tie_rule say what happened.
--
-- Status per cohort row (repeated on each of its rows):
--   no_postcode              the cohort postcode is empty
--   postcode_not_in_epc      no certificate in the release has that pc_norm
--   no_certificate_by_date   dwellings exist, none has a certificate inspected on or before the date
--   matched                  one row per dwelling with an eligible certificate

IF EXISTS (SELECT 1 FROM #cohort WHERE cohort_row_id IS NULL)
    THROW 51000, 'cohort_row_id must not be NULL: a NULL key cannot be joined back to its result.', 1;
IF EXISTS (SELECT 1 FROM #cohort GROUP BY cohort_row_id HAVING COUNT(*) > 1)
    THROW 51000, 'cohort_row_id must be unique: one row per cohort observation.', 1;

WITH cohort AS (
    SELECT c.cohort_row_id, c.pseudo_id, c.cohort_date,
           NULLIF(UPPER(REPLACE(c.postcode, N' ', N'')), N'') AS pc_norm
    FROM #cohort AS c
),
eligible AS (
    SELECT c.cohort_row_id, e.uprn_sepcr, e.epc_release, e.source_year, e.source_row,
           RANK() OVER (PARTITION BY c.cohort_row_id, e.uprn_sepcr ORDER BY e.inspection_date_parsed DESC) AS rk_day,
           RANK() OVER (PARTITION BY c.cohort_row_id, e.uprn_sepcr ORDER BY e.inspection_date_parsed DESC,
                        CASE WHEN e.historic_flag = 0 THEN 0 ELSE 1 END) AS rk_current,
           RANK() OVER (PARTITION BY c.cohort_row_id, e.uprn_sepcr ORDER BY e.inspection_date_parsed DESC,
                        CASE WHEN e.historic_flag = 0 THEN 0 ELSE 1 END, e.created_at_parsed DESC) AS rk_final
    FROM cohort AS c
    JOIN epc_domestic AS e
      ON e.pc_norm = c.pc_norm
     AND e.inspection_date_parsed <= c.cohort_date
),
per_dwelling AS (
    SELECT cohort_row_id, uprn_sepcr,
           SUM(CASE WHEN rk_day = 1 THEN 1 ELSE 0 END) AS n_day,
           SUM(CASE WHEN rk_current = 1 THEN 1 ELSE 0 END) AS n_current,
           SUM(CASE WHEN rk_final = 1 THEN 1 ELSE 0 END) AS n,
           MIN(CASE WHEN rk_final = 1 THEN epc_release END) AS epc_release,
           MIN(CASE WHEN rk_final = 1 THEN source_year END) AS source_year,
           MIN(CASE WHEN rk_final = 1 THEN source_row END) AS source_row
    FROM eligible
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
       e.uprn_osg, e.inspection_date_parsed AS epc_inspection_date, e.lodgement_date_parsed AS epc_lodgement_date,
       DATEDIFF(day, e.inspection_date_parsed, c.cohort_date) AS epc_age_days,
       CASE WHEN e.lodgement_date_parsed < e.inspection_date_parsed THEN 1
            WHEN e.inspection_date_parsed IS NOT NULL THEN 0 END AS epc_lodged_before_inspection,
       e.CURRENT_ENERGY_RATING, e.current_energy_efficiency_int, e.total_floor_area_int,
       e.PROPERTY_TYPE, e.BUILT_FORM, e.CONSTRUCTION_AGE_BAND, e.TENURE,
       d.n_day AS epc_tie_candidates,
       CASE WHEN d.n_day IS NULL OR d.n_day = 1 THEN NULL
            WHEN d.n > 1 THEN 'unresolved'
            WHEN d.n_current = 1 THEN 'current'
            ELSE 'latest_lodged' END AS epc_tie_rule
FROM cohort AS c
LEFT JOIN known AS k ON k.pc_norm = c.pc_norm
LEFT JOIN per_dwelling AS d ON d.cohort_row_id = c.cohort_row_id
LEFT JOIN epc_domestic AS e
       ON d.n = 1 AND e.epc_release = d.epc_release AND e.source_year = d.source_year AND e.source_row = d.source_row
ORDER BY c.cohort_row_id, d.uprn_sepcr;
