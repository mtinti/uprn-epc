-- From a matched certificate onward to SIMD and AHAH. A sketch to adapt: it names the tables
-- of the two sibling products, which must be loaded in the same database.
--
-- SIMD: postcode-simd's link_as_of.sql maps a postcode and a date to the data zone and SIMD
-- release in force on that date. Use the certificate's pc_norm and lodgement date, so the
-- deprivation is that of the dwelling's area when the certificate was lodged.
--
-- AHAH: datazone-ahah's ahah_datazone, version 4, is on the 2011 data zones. The certificate
-- carries its own datazone_2011, assigned by the register from the address at lodgement. It
-- can differ from the data zone postcode-simd derives from the postcode for the same date:
-- the register's came from the address, postcode-simd's from the postcode's grid reference or
-- output area centroid. The query returns both so the difference is visible.

WITH matched AS (
    -- The result of join_by_uprn.sql, kept as a temporary table or a CTE: one row per cohort
    -- row with epc_status = 'matched' and the certificate's key.
    SELECT m.cohort_row_id, m.pseudo_id, m.cohort_date, e.pc_norm, e.lodgement_date_parsed, e.datazone_2011, e.datazone_2011_status
    FROM #matched AS m
    JOIN epc_domestic AS e
      ON e.epc_release = m.epc_release AND e.source_year = m.source_year AND e.source_row = m.source_row
)
SELECT m.cohort_row_id, m.pseudo_id, m.cohort_date,
       m.datazone_2011 AS epc_datazone_2011, m.datazone_2011_status,
       s.DataZone2011Code AS simd_datazone_2011, s.simd_release, s.simd_rank, s.simd_decile,
       CASE WHEN m.datazone_2011 IS NULL OR s.DataZone2011Code IS NULL THEN 'one_side_missing'
            WHEN m.datazone_2011 = s.DataZone2011Code THEN 'same'
            ELSE 'differ' END AS datazone_agreement,
       a.ahah, a.ahah_rnk, a.ahah_pct, a.domain_h, a.domain_g, a.domain_e, a.domain_r,
       CASE WHEN m.datazone_2011 IS NULL THEN 'no_datazone' WHEN a.datazone_code IS NULL THEN 'not_a_datazone' ELSE 'matched' END AS ahah_status
FROM matched AS m
-- postcode-simd: replace with the link_as_of pattern of that project (docs/sql/spd/link_as_of.sql),
-- which takes (pc_norm, date) and returns the postcode row in force on that date.
LEFT JOIN simd_link_as_of AS s ON s.pc_norm = m.pc_norm AND m.lodgement_date_parsed BETWEEN s.valid_from AND s.valid_to
LEFT JOIN ahah_datazone AS a ON a.datazone_code = m.datazone_2011 AND a.ahah_version = N'4'
ORDER BY m.cohort_row_id;
