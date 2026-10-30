# Build report: epc_domestic, release 2026Q2, 2026-10-30T08:23:21Z

Schema `epc_domestic_v1`. 3,787,069 rows by 130 columns in the Parquet, 127 in the CSV (the three address lines withheld).
CSV `epc_domestic.csv.gz` SHA256 `3047e71eaa186e1f853c93953087cd8a1966898197f19d62f5db43c0fded264c`, digest total `-35655847973013680818794`.
Parquet SHA256 `23495db815c6e95c32ae5d2aa46e63488cf3fcaecf2daa2bbea10fdcdbd710a3`.

## Rows per year

| Year | Rows | HISTORIC True | HISTORIC False | Empty UPRN | Empty RRN | Digest total |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2008 | 9,055 | 7,475 | 1,580 | 10 | 375 | `-605292016027400250450` |
| 2009 | 203,831 | 159,631 | 44,200 | 5,360 | 7,208 | `1609481545741641798299` |
| 2010 | 126,784 | 94,783 | 32,001 | 2,759 | 4,724 | `1007469630019351218446` |
| 2011 | 125,877 | 92,122 | 33,755 | 2,263 | 4,637 | `1938960249245352794578` |
| 2012 | 130,932 | 89,715 | 41,217 | 2,578 | 6,207 | `-1091898152246186545307` |
| 2013 | 244,184 | 172,480 | 71,704 | 4,339 | 35,554 | `-1064087481219449826644` |
| 2014 | 353,444 | 232,205 | 121,239 | 7,515 | 93,604 | `-8283271092137779254132` |
| 2015 | 284,531 | 170,381 | 114,150 | 11,674 | 52,484 | `-4964734794451134719882` |
| 2016 | 251,337 | 134,740 | 116,597 | 12,584 | 32,729 | `-1312109079675265703740` |
| 2017 | 226,738 | 110,297 | 116,441 | 11,027 | 21,677 | `-2728585713637737731486` |
| 2018 | 223,222 | 101,301 | 121,921 | 13,129 | 13,876 | `-2861935135331355683732` |
| 2019 | 240,409 | 96,012 | 144,397 | 15,652 | 13,058 | `-4385402886374359446729` |
| 2020 | 184,580 | 67,644 | 116,936 | 12,267 | 9,099 | `-2207672410567681057296` |
| 2021 | 205,602 | 64,247 | 141,355 | 16,700 | 7,546 | `1859986810618167750061` |
| 2022 | 217,143 | 56,789 | 160,354 | 16,343 | 7,503 | `-3917835564494976643056` |
| 2023 | 222,206 | 48,613 | 173,593 | 14,862 | 8,083 | `-2285277918643436413669` |
| 2024 | 219,190 | 39,954 | 179,236 | 12,972 | 8,859 | `-3208893473212881030650` |
| 2025 | 207,994 | 23,429 | 184,565 | 11,168 | 8,420 | `-1524031268430388320049` |
| 2026 | 110,010 | 6,731 | 103,279 | 5,335 | 4,367 | `-1630719222188161753356` |

## What the release holds

| Fact | Value |
| --- | --- |
| Distinct Gazetteer UPRNs (`uprn_osg`) | 1,885,772 |
| Distinct register numbers (`uprn_sepcr`) | 2,021,459 |
| Rows with no Gazetteer UPRN | 178,537 |
| UPRNs by digit count | 8: 17,933, 9: 1,439,867, 10: 137,837, 11: 13,303, 12: 276,832 |
| UPRNs with exactly one `HISTORIC = False` certificate | 1,882,924 |
| UPRNs with two or more `HISTORIC = False` certificates (`ambiguous_latest`) | 22 |
| UPRNs whose certificates are all `HISTORIC = True` (`no_current_certificate`) | 2,826 |
| (UPRN, lodgement day) pairs with two or more certificates (`ambiguous_as_of` candidates) | 42,870 |
| Rows with an empty RRN | 340,010 |
| `datazone_2001_status` | code: 3,540,873, empty: 233,958, not_a_datazone: 12,238 |
| `datazone_2011_status` | code: 3,701,135, empty: 85,637, not_a_datazone: 297 |
| Distinct 2001 and 2011 data zone codes | 6,502 and 6,973 |
| Rows with an empty postcode | 10 |
| Distinct `pc_norm` | 143,782 |
| `pc_norm` not 5 to 7 characters | 0 |
| Rows with `TOTAL_FLOOR_AREA` 0 | 212,886 (range [0, 1498]) |
| Rows with a rating above 100 | current_energy_efficiency_int: 2,522, potential_energy_efficiency_int: 54,005, environment_impact_current_int: 3,171, environment_impact_potential_int: 38,652 |
| Rows lodged before inspection | 2,036 |
| Lodgement date range | 2002-02-03 to 2108-12-13; 3 rows outside 2008 to 2026 |
| Rows with empty `TYPE_OF_ASSESSMENT` | 7,490 |
| Rows with empty `ADDENDUM_TEXT` | 3,787,069 |
| Cells with an embedded newline | BUILDING_REFERENCE_NUMBER: 6, ADDRESS1: 1 |

## Longest text per column against its width

| Column | Longest | nvarchar |
| --- | ---: | ---: |
| `epc_release` | 6 | 8 |
| `HISTORIC` | 5 | 8 |
| `BUILDING_REFERENCE_NUMBER` | 11 | 32 |
| `OSG_REFERENCE_NUMBER` | 12 | 32 |
| `ADDRESS1` | 66 | 100 |
| `ADDRESS2` | 51 | 100 |
| `ADDRESS3` | 34 | 100 |
| `POSTCODE` | 8 | 32 |
| `INSPECTION_DATE` | 10 | 32 |
| `TYPE_OF_ASSESSMENT` | 24 | 32 |
| `LODGEMENT_DATE` | 10 | 32 |
| `ENERGY_CONSUMPTION_CURRENT` | 12 | 32 |
| `TOTAL_FLOOR_AREA` | 4 | 8 |
| `3_YR_ENERGY_COST_CURRENT` | 15 | 32 |
| `3_YR_ENERGY_SAVINGS_POTENTIAL` | 15 | 32 |
| `CURRENT_ENERGY_EFFICIENCY` | 5 | 8 |
| `CURRENT_ENERGY_RATING` | 1 | 8 |
| `POTENTIAL_ENERGY_EFFICIENCY` | 5 | 8 |
| `POTENTIAL_ENERGY_RATING` | 1 | 8 |
| `ENVIRONMENT_IMPACT_CURRENT` | 5 | 8 |
| `CURRENT_ENVIRONMENTAL_RATING` | 1 | 8 |
| `ENVIRONMENT_IMPACT_POTENTIAL` | 5 | 8 |
| `POTENTIAL_ENVIRONMENTAL_RATING` | 1 | 8 |
| `CO2_EMISS_CURR_PER_FLOOR_AREA` | 11 | 32 |
| `IMPROVEMENTS` | 3330 | 4000 |
| `WALL_DESCRIPTION` | 328 | 512 |
| `WALL_ENERGY_EFF` | 70 | 100 |
| `WALL_ENV_EFF` | 70 | 100 |
| `ROOF_DESCRIPTION` | 250 | 512 |
| `ROOF_ENERGY_EFF` | 70 | 100 |
| `ROOF_ENV_EFF` | 70 | 100 |
| `FLOOR_DESCRIPTION` | 256 | 512 |
| `FLOOR_ENERGY_EFF` | 34 | 100 |
| `FLOOR_ENV_EFF` | 34 | 100 |
| `WINDOWS_DESCRIPTION` | 44 | 100 |
| `WINDOWS_ENERGY_EFF` | 10 | 32 |
| `WINDOWS_ENV_EFF` | 10 | 32 |
| `MAINHEAT_DESCRIPTION` | 210 | 512 |
| `MAINHEAT_ENERGY_EFF` | 46 | 100 |
| `MAINHEAT_ENV_EFF` | 46 | 100 |
| `MAINHEATCONT_DESCRIPTION` | 216 | 512 |
| `MAINHEATC_ENERGY_EFF` | 46 | 100 |
| `MAINHEATC_ENV_EFF` | 46 | 100 |
| `SECONDHEAT_DESCRIPTION` | 88 | 100 |
| `SHEATING_ENERGY_EFF` | 10 | 32 |
| `SHEATING_ENV_EFF` | 10 | 32 |
| `HOTWATER_DESCRIPTION` | 182 | 512 |
| `HOT_WATER_ENERGY_EFF` | 22 | 32 |
| `HOT_WATER_ENV_EFF` | 22 | 32 |
| `LIGHTING_DESCRIPTION` | 90 | 100 |
| `LIGHTING_ENERGY_EFF` | 22 | 32 |
| `LIGHTING_ENV_EFF` | 22 | 32 |
| `AIR_TIGHTNESS_DESCRIPTION` | 51 | 100 |
| `AIR_TIGHTNESS_ENERGY_EFF` | 10 | 32 |
| `AIR_TIGHTNESS_ENV_EFF` | 10 | 32 |
| `CO2_EMISSIONS_CURRENT` | 10 | 32 |
| `CO2_EMISSIONS_POTENTIAL` | 10 | 32 |
| `HEATING_COST_CURRENT` | 15 | 32 |
| `HEATING_COST_POTENTIAL` | 14 | 32 |
| `HOT_WATER_COST_CURRENT` | 8 | 32 |
| `HOT_WATER_COST_POTENTIAL` | 8 | 32 |
| `LIGHTING_COST_CURRENT` | 9 | 32 |
| `LIGHTING_COST_POTENTIAL` | 9 | 32 |
| `ALTERNATIVE_IMPROVEMENTS` | 295 | 512 |
| `LZC_ENERGY_SOURCES` | 308 | 512 |
| `SPACE_HEATING_DEMAND` | 10 | 32 |
| `WATER_HEATING_DEMAND` | 8 | 32 |
| `IMPACT_LOFT_INSULATION` | 8 | 32 |
| `IMPACT_CAVITY_WALL_INSULATION` | 10 | 32 |
| `IMPACT_SOLID_WALL_INSULATION` | 8 | 32 |
| `ADDENDUM_TEXT` | 0 | 128 |
| `CONSTRUCTION_AGE_BAND` | 12 | 32 |
| `FLOOR_HEIGHT` | 10 | 32 |
| `DATA_ZONE` | 64 | 100 |
| `ENERGY_CONSUMPTION_POTENTIAL` | 11 | 32 |
| `EXTENSION_COUNT` | 1 | 8 |
| `FIXED_LIGHTING_OUTLETS_COUNT` | 4 | 8 |
| `LOW_ENERGY_FIXED_LIGHT_COUNT` | 4 | 8 |
| `LOW_ENERGY_LIGHTING` | 6 | 8 |
| `FLOOR_LEVEL` | 12 | 32 |
| `FLAT_TOP_STOREY` | 3 | 8 |
| `GLAZED_AREA` | 1 | 8 |
| `NUMBER_HABITABLE_ROOMS` | 2 | 8 |
| `HEAT_LOSS_CORRIDOOR` | 17 | 32 |
| `NUMBER_HEATED_ROOMS` | 2 | 8 |
| `LOCAL_AUTHORITY_LABEL` | 21 | 32 |
| `MAINS_GAS_FLAG` | 1 | 8 |
| `MAIN_HEATING_CATEGORY` | 46 | 100 |
| `MAIN_FUEL` | 69 | 100 |
| `MAIN_HEATING_CONTROLS` | 4 | 8 |
| `MECHANICAL_VENTILATION` | 30 | 32 |
| `ENERGY_TARIFF` | 16 | 32 |
| `MULTI_GLAZE_PROPORTION` | 3 | 8 |
| `GLAZED_TYPE` | 45 | 100 |
| `NUMBER_OPEN_FIREPLACES` | 3 | 8 |
| `PHOTO_SUPPLY` | 570 | 1000 |
| `SOLAR_WATER_HEATING_FLAG` | 5 | 8 |
| `TENURE` | 16 | 32 |
| `TRANSACTION_TYPE` | 25 | 32 |
| `UNHEATED_CORRIDOR_LENGTH` | 9 | 32 |
| `CONSTITUENCY` | 6 | 8 |
| `CONSTITUENCY_LABEL` | 53 | 100 |
| `WIND_TURBINE_COUNT` | 1 | 8 |
| `BUILT_FORM` | 20 | 32 |
| `PROPERTY_TYPE` | 10 | 32 |
| `DATA_ZONE_2011` | 75 | 100 |
| `CREATED_AT` | 19 | 32 |
| `REPORT_REFERENCE_NUMBER` | 24 | 32 |
| `rrn` | 24 | 24 |
| `pc_norm` | 7 | 8 |
| `datazone_2001` | 9 | 9 |
| `datazone_2001_status` | 14 | 16 |
| `datazone_2011` | 9 | 9 |
| `datazone_2011_status` | 14 | 16 |

## Checks

297 passed, 0 failed.

| Check | Result | Detail |
| --- | --- | --- |
| `source.epc_2026Q2/extracted/2008.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2009.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2010.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2011.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2012.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2013.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2014.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2015.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2016.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2017.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2018.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2019.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2020.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2021.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2022.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2023.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2024.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2025.csv` | pass | sha256 matches |
| `source.epc_2026Q2/extracted/2026.csv` | pass | sha256 matches |
| `source.datazones/SG_SIMD_2012.dbf` | pass | sha256 matches |
| `source.datazones/DataZone2011_lookup.csv` | pass | sha256 matches |
| `source.epc_2026Q2/domestic_epc_extended_historic_Q2_2026.7z` | pass | sha256 matches |
| `source.epc_2026Q2/publication_note.pdf` | pass | sha256 matches |
| `schema.matches_generator` | pass | output_schema.yaml is what python -m epc_ingest.columns writes |
| `datazones_2001.count` | pass | 6505 |
| `datazones_2001.distinct` | pass | 6505 |
| `datazones_2011.count` | pass | 6976 |
| `datazones_2011.distinct` | pass | 6976 |
| `2008.utf8` | pass | decoded as UTF-8 |
| `2008.header_names` | pass | 107 columns as pinned |
| `2008.header_labels` | pass | labels as pinned |
| `2008.row_width` | pass | 9055 rows of 107 fields |
| `2008.rows` | pass | 9055 |
| `2008.rrn_shape` | pass | 8680 present, all 9999-9999-9999-9999-9999 |
| `2008.rrn_unique_in_file` | pass | 0 |
| `2008.created_at_year` | pass | every CREATED_AT is in the file year |
| `2008.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2008.text_within_width` | pass | every text value fits its nvarchar width |
| `2008.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2009.utf8` | pass | decoded as UTF-8 |
| `2009.header_names` | pass | 107 columns as pinned |
| `2009.header_labels` | pass | labels as pinned |
| `2009.row_width` | pass | 203831 rows of 107 fields |
| `2009.rows` | pass | 203831 |
| `2009.rrn_shape` | pass | 196623 present, all 9999-9999-9999-9999-9999 |
| `2009.rrn_unique_in_file` | pass | 0 |
| `2009.created_at_year` | pass | every CREATED_AT is in the file year |
| `2009.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2009.text_within_width` | pass | every text value fits its nvarchar width |
| `2009.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2010.utf8` | pass | decoded as UTF-8 |
| `2010.header_names` | pass | 107 columns as pinned |
| `2010.header_labels` | pass | labels as pinned |
| `2010.row_width` | pass | 126784 rows of 107 fields |
| `2010.rows` | pass | 126784 |
| `2010.rrn_shape` | pass | 122060 present, all 9999-9999-9999-9999-9999 |
| `2010.rrn_unique_in_file` | pass | 0 |
| `2010.created_at_year` | pass | every CREATED_AT is in the file year |
| `2010.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2010.text_within_width` | pass | every text value fits its nvarchar width |
| `2010.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2011.utf8` | pass | decoded as UTF-8 |
| `2011.header_names` | pass | 107 columns as pinned |
| `2011.header_labels` | pass | labels as pinned |
| `2011.row_width` | pass | 125877 rows of 107 fields |
| `2011.rows` | pass | 125877 |
| `2011.rrn_shape` | pass | 121240 present, all 9999-9999-9999-9999-9999 |
| `2011.rrn_unique_in_file` | pass | 0 |
| `2011.created_at_year` | pass | every CREATED_AT is in the file year |
| `2011.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2011.text_within_width` | pass | every text value fits its nvarchar width |
| `2011.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2012.utf8` | pass | decoded as UTF-8 |
| `2012.header_names` | pass | 107 columns as pinned |
| `2012.header_labels` | pass | labels as pinned |
| `2012.row_width` | pass | 130932 rows of 107 fields |
| `2012.rows` | pass | 130932 |
| `2012.rrn_shape` | pass | 124725 present, all 9999-9999-9999-9999-9999 |
| `2012.rrn_unique_in_file` | pass | 0 |
| `2012.created_at_year` | pass | every CREATED_AT is in the file year |
| `2012.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2012.text_within_width` | pass | every text value fits its nvarchar width |
| `2012.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2013.utf8` | pass | decoded as UTF-8 |
| `2013.header_names` | pass | 107 columns as pinned |
| `2013.header_labels` | pass | labels as pinned |
| `2013.row_width` | pass | 244184 rows of 107 fields |
| `2013.rows` | pass | 244184 |
| `2013.rrn_shape` | pass | 208630 present, all 9999-9999-9999-9999-9999 |
| `2013.rrn_unique_in_file` | pass | 0 |
| `2013.created_at_year` | pass | every CREATED_AT is in the file year |
| `2013.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2013.text_within_width` | pass | every text value fits its nvarchar width |
| `2013.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2014.utf8` | pass | decoded as UTF-8 |
| `2014.header_names` | pass | 107 columns as pinned |
| `2014.header_labels` | pass | labels as pinned |
| `2014.row_width` | pass | 353444 rows of 107 fields |
| `2014.rows` | pass | 353444 |
| `2014.rrn_shape` | pass | 259840 present, all 9999-9999-9999-9999-9999 |
| `2014.rrn_unique_in_file` | pass | 0 |
| `2014.created_at_year` | pass | every CREATED_AT is in the file year |
| `2014.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2014.text_within_width` | pass | every text value fits its nvarchar width |
| `2014.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2015.utf8` | pass | decoded as UTF-8 |
| `2015.header_names` | pass | 107 columns as pinned |
| `2015.header_labels` | pass | labels as pinned |
| `2015.row_width` | pass | 284531 rows of 107 fields |
| `2015.rows` | pass | 284531 |
| `2015.rrn_shape` | pass | 232047 present, all 9999-9999-9999-9999-9999 |
| `2015.rrn_unique_in_file` | pass | 0 |
| `2015.created_at_year` | pass | every CREATED_AT is in the file year |
| `2015.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2015.text_within_width` | pass | every text value fits its nvarchar width |
| `2015.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2016.utf8` | pass | decoded as UTF-8 |
| `2016.header_names` | pass | 107 columns as pinned |
| `2016.header_labels` | pass | labels as pinned |
| `2016.row_width` | pass | 251337 rows of 107 fields |
| `2016.rows` | pass | 251337 |
| `2016.rrn_shape` | pass | 218608 present, all 9999-9999-9999-9999-9999 |
| `2016.rrn_unique_in_file` | pass | 0 |
| `2016.created_at_year` | pass | every CREATED_AT is in the file year |
| `2016.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2016.text_within_width` | pass | every text value fits its nvarchar width |
| `2016.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2017.utf8` | pass | decoded as UTF-8 |
| `2017.header_names` | pass | 107 columns as pinned |
| `2017.header_labels` | pass | labels as pinned |
| `2017.row_width` | pass | 226738 rows of 107 fields |
| `2017.rows` | pass | 226738 |
| `2017.rrn_shape` | pass | 205061 present, all 9999-9999-9999-9999-9999 |
| `2017.rrn_unique_in_file` | pass | 0 |
| `2017.created_at_year` | pass | every CREATED_AT is in the file year |
| `2017.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2017.text_within_width` | pass | every text value fits its nvarchar width |
| `2017.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2018.utf8` | pass | decoded as UTF-8 |
| `2018.header_names` | pass | 107 columns as pinned |
| `2018.header_labels` | pass | labels as pinned |
| `2018.row_width` | pass | 223222 rows of 107 fields |
| `2018.rows` | pass | 223222 |
| `2018.rrn_shape` | pass | 209346 present, all 9999-9999-9999-9999-9999 |
| `2018.rrn_unique_in_file` | pass | 0 |
| `2018.created_at_year` | pass | every CREATED_AT is in the file year |
| `2018.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2018.text_within_width` | pass | every text value fits its nvarchar width |
| `2018.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2019.utf8` | pass | decoded as UTF-8 |
| `2019.header_names` | pass | 107 columns as pinned |
| `2019.header_labels` | pass | labels as pinned |
| `2019.row_width` | pass | 240409 rows of 107 fields |
| `2019.rows` | pass | 240409 |
| `2019.rrn_shape` | pass | 227351 present, all 9999-9999-9999-9999-9999 |
| `2019.rrn_unique_in_file` | pass | 0 |
| `2019.created_at_year` | pass | every CREATED_AT is in the file year |
| `2019.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2019.text_within_width` | pass | every text value fits its nvarchar width |
| `2019.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2020.utf8` | pass | decoded as UTF-8 |
| `2020.header_names` | pass | 107 columns as pinned |
| `2020.header_labels` | pass | labels as pinned |
| `2020.row_width` | pass | 184580 rows of 107 fields |
| `2020.rows` | pass | 184580 |
| `2020.rrn_shape` | pass | 175481 present, all 9999-9999-9999-9999-9999 |
| `2020.rrn_unique_in_file` | pass | 0 |
| `2020.created_at_year` | pass | every CREATED_AT is in the file year |
| `2020.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2020.text_within_width` | pass | every text value fits its nvarchar width |
| `2020.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2021.utf8` | pass | decoded as UTF-8 |
| `2021.header_names` | pass | 107 columns as pinned |
| `2021.header_labels` | pass | labels as pinned |
| `2021.row_width` | pass | 205602 rows of 107 fields |
| `2021.rows` | pass | 205602 |
| `2021.rrn_shape` | pass | 198056 present, all 9999-9999-9999-9999-9999 |
| `2021.rrn_unique_in_file` | pass | 0 |
| `2021.created_at_year` | pass | every CREATED_AT is in the file year |
| `2021.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2021.text_within_width` | pass | every text value fits its nvarchar width |
| `2021.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2022.utf8` | pass | decoded as UTF-8 |
| `2022.header_names` | pass | 107 columns as pinned |
| `2022.header_labels` | pass | labels as pinned |
| `2022.row_width` | pass | 217143 rows of 107 fields |
| `2022.rows` | pass | 217143 |
| `2022.rrn_shape` | pass | 209640 present, all 9999-9999-9999-9999-9999 |
| `2022.rrn_unique_in_file` | pass | 0 |
| `2022.created_at_year` | pass | every CREATED_AT is in the file year |
| `2022.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2022.text_within_width` | pass | every text value fits its nvarchar width |
| `2022.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2023.utf8` | pass | decoded as UTF-8 |
| `2023.header_names` | pass | 107 columns as pinned |
| `2023.header_labels` | pass | labels as pinned |
| `2023.row_width` | pass | 222206 rows of 107 fields |
| `2023.rows` | pass | 222206 |
| `2023.rrn_shape` | pass | 214123 present, all 9999-9999-9999-9999-9999 |
| `2023.rrn_unique_in_file` | pass | 0 |
| `2023.created_at_year` | pass | every CREATED_AT is in the file year |
| `2023.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2023.text_within_width` | pass | every text value fits its nvarchar width |
| `2023.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2024.utf8` | pass | decoded as UTF-8 |
| `2024.header_names` | pass | 107 columns as pinned |
| `2024.header_labels` | pass | labels as pinned |
| `2024.row_width` | pass | 219190 rows of 107 fields |
| `2024.rows` | pass | 219190 |
| `2024.rrn_shape` | pass | 210331 present, all 9999-9999-9999-9999-9999 |
| `2024.rrn_unique_in_file` | pass | 0 |
| `2024.created_at_year` | pass | every CREATED_AT is in the file year |
| `2024.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2024.text_within_width` | pass | every text value fits its nvarchar width |
| `2024.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2025.utf8` | pass | decoded as UTF-8 |
| `2025.header_names` | pass | 107 columns as pinned |
| `2025.header_labels` | pass | labels as pinned |
| `2025.row_width` | pass | 207994 rows of 107 fields |
| `2025.rows` | pass | 207994 |
| `2025.rrn_shape` | pass | 199574 present, all 9999-9999-9999-9999-9999 |
| `2025.rrn_unique_in_file` | pass | 0 |
| `2025.created_at_year` | pass | every CREATED_AT is in the file year |
| `2025.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2025.text_within_width` | pass | every text value fits its nvarchar width |
| `2025.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `2026.utf8` | pass | decoded as UTF-8 |
| `2026.header_names` | pass | 107 columns as pinned |
| `2026.header_labels` | pass | labels as pinned |
| `2026.row_width` | pass | 110010 rows of 107 fields |
| `2026.rows` | pass | 110010 |
| `2026.rrn_shape` | pass | 105643 present, all 9999-9999-9999-9999-9999 |
| `2026.rrn_unique_in_file` | pass | 0 |
| `2026.created_at_year` | pass | every CREATED_AT is in the file year |
| `2026.derived_values_parse` | pass | every date, flag, integer and decimal the derived columns need parses |
| `2026.text_within_width` | pass | every text value fits its nvarchar width |
| `2026.decimal_round_trip` | pass | every decimal cell: file text, Decimal, 4-place text, Decimal |
| `readback.parquet.column_names` | pass | ['epc_release', 'source_year', 'source_row', 'HISTORIC', 'BUILDING_REFERENCE_NUMBER', 'OSG_REFERENCE_NUMBER', 'ADDRESS1', 'ADDRESS2', 'ADDRESS3', 'POSTCODE', 'I |
| `readback.parquet.column_types` | pass | ['string', 'int16', 'int32', 'string', 'string', 'string', 'string', 'string', 'string', 'string', 'string', 'string', 'string', 'string', 'string', 'string', ' |
| `readback.parquet.nullability` | pass | [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False |
| `readback.parquet.metadata.grain` | pass | One row per published certificate, superseded certificates included (HISTORIC = True). The 107 published columns are text exactly as published; the derived colu |
| `readback.parquet.metadata.schema_version` | pass | epc_domestic_v1 |
| `readback.parquet.metadata.key` | pass | ["epc_release", "source_year", "source_row"] |
| `readback.parquet.metadata.epc_release` | pass | 2026Q2 |
| `readback.parquet.metadata.decisions_sha256` | pass | b021470fe102b01d19bde8b2ea537cb1969ee63e65581c51d9a9436e91a68c3b |
| `readback.parquet.metadata.registry_sha256` | pass | bbce1df297307bc118b1d623bf0aada579d8070482f38f307d5f2cf0c69c3cdf |
| `readback.parquet.metadata.sources` | pass | [{"year": 2008, "file": "epc_2026Q2/extracted/2008.csv", "sha256": "ce393d3ab26847d9a642d8e7491203db88e526ea473bb74daeead19ca4865c2c"}, {"year": 2009, "file": " |
| `readback.parquet.rows` | pass | 3787069 |
| `readback.parquet.row_groups` | pass | 19 |
| `readback.parquet.2008.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2008.one_year_per_row_group` | pass | [2008] |
| `readback.parquet.2009.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2009.one_year_per_row_group` | pass | [2009] |
| `readback.parquet.2010.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2010.one_year_per_row_group` | pass | [2010] |
| `readback.parquet.2011.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2011.one_year_per_row_group` | pass | [2011] |
| `readback.parquet.2012.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2012.one_year_per_row_group` | pass | [2012] |
| `readback.parquet.2013.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2013.one_year_per_row_group` | pass | [2013] |
| `readback.parquet.2014.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2014.one_year_per_row_group` | pass | [2014] |
| `readback.parquet.2015.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2015.one_year_per_row_group` | pass | [2015] |
| `readback.parquet.2016.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2016.one_year_per_row_group` | pass | [2016] |
| `readback.parquet.2017.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2017.one_year_per_row_group` | pass | [2017] |
| `readback.parquet.2018.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2018.one_year_per_row_group` | pass | [2018] |
| `readback.parquet.2019.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2019.one_year_per_row_group` | pass | [2019] |
| `readback.parquet.2020.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2020.one_year_per_row_group` | pass | [2020] |
| `readback.parquet.2021.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2021.one_year_per_row_group` | pass | [2021] |
| `readback.parquet.2022.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2022.one_year_per_row_group` | pass | [2022] |
| `readback.parquet.2023.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2023.one_year_per_row_group` | pass | [2023] |
| `readback.parquet.2024.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2024.one_year_per_row_group` | pass | [2024] |
| `readback.parquet.2025.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2025.one_year_per_row_group` | pass | [2025] |
| `readback.parquet.2026.digest` | pass | the row group rendered again gives the digest recorded while writing |
| `readback.parquet.2026.one_year_per_row_group` | pass | [2026] |
| `readback.parquet.sampled_rows_equal_source` | pass | 57 rows (first, middle, last of each file), 6,099 published cells compared with the source text |
| `readback.csv.header` | pass | ['epc_release', 'source_year', 'source_row', 'HISTORIC', 'BUILDING_REFERENCE_NUMBER', 'OSG_REFERENCE_NUMBER', 'POSTCODE', 'INSPECTION_DATE', 'TYPE_OF_ASSESSMENT |
| `readback.csv.rows` | pass | 3787069 |
| `readback.csv.digest_total` | pass | the digest recomputed from the bytes on disk equals the one computed while writing |
| `table.rows` | pass | key unique |
| `table.rrn_unique` | pass | 3,447,059 present RRNs, none repeated across the release |
| `table.uprn_one_to_one` | pass | where both are present, each Gazetteer UPRN has one register number and the reverse |
| `table.datazone_2001_status.no_unknown_code` | pass | every well formed code is in the pinned list |
| `table.datazone_2011_status.no_unknown_code` | pass | every well formed code is in the pinned list |
| `table.required_nonnull` | pass | {} |

## One certificate cell for cell: 2026 row 1

The source text of the pinned file, which the Parquet holds unchanged (checked for the first, middle and last row of every file). The address lines and the postcode are not printed here.

| Column | Source text |
| --- | --- |
| `HISTORIC` | `False` |
| `BUILDING_REFERENCE_NUMBER` | `1000033490` |
| `OSG_REFERENCE_NUMBER` | `906338645` |
| `ADDRESS1` | `(withheld)` |
| `ADDRESS2` | `(withheld)` |
| `ADDRESS3` | `(withheld)` |
| `POSTCODE` | `(withheld)` |
| `INSPECTION_DATE` | `2026-03-24` |
| `TYPE_OF_ASSESSMENT` | `RdSAP, existing dwelling` |
| `LODGEMENT_DATE` | `2026-03-27` |
| `ENERGY_CONSUMPTION_CURRENT` | `242.00` |
| `TOTAL_FLOOR_AREA` | `46` |
| `3_YR_ENERGY_COST_CURRENT` | `2430.0000` |
| `3_YR_ENERGY_SAVINGS_POTENTIAL` | `630.0000` |
| `CURRENT_ENERGY_EFFICIENCY` | `70` |
| `CURRENT_ENERGY_RATING` | `C` |
| `POTENTIAL_ENERGY_EFFICIENCY` | `77` |
| `POTENTIAL_ENERGY_RATING` | `C` |
| `ENVIRONMENT_IMPACT_CURRENT` | `72` |
| `CURRENT_ENVIRONMENTAL_RATING` | `C` |
| `ENVIRONMENT_IMPACT_POTENTIAL` | `82` |
| `POTENTIAL_ENVIRONMENTAL_RATING` | `B` |
| `CO2_EMISS_CURR_PER_FLOOR_AREA` | `44.00` |
| `IMPROVEMENTS` | `Description: Floor insulation (suspended floor); Indicative Cost: £5,000 - £10,000; Typical Saving: 73; Energy Rating after improvement: C 77; Environmental Rating after improvement: B 82; Green Deal Eligible: N \| Description: Internal or external wall insulation; Indicative Cost: £7,500 - £11,000; Typical Saving: 138; Energy Rating after improvement: C 75; Environmental Rating after improvement: C 79; Green Deal Eligible: N \| ` |
| `WALL_DESCRIPTION` | `Sandstone, as built, no insulation (assumed) \| Solid brick, as built, no insulation (assumed) ` |
| `WALL_ENERGY_EFF` | `Poor \| Poor ` |
| `WALL_ENV_EFF` | `Poor \| Poor ` |
| `ROOF_DESCRIPTION` | `(another dwelling above) ` |
| `ROOF_ENERGY_EFF` | `N/A ` |
| `ROOF_ENV_EFF` | `N/A ` |
| `FLOOR_DESCRIPTION` | `Suspended, no insulation (assumed) ` |
| `FLOOR_ENERGY_EFF` | `N/A ` |
| `FLOOR_ENV_EFF` | `N/A ` |
| `WINDOWS_DESCRIPTION` | |
| `WINDOWS_ENERGY_EFF` | |
| `WINDOWS_ENV_EFF` | |
| `MAINHEAT_DESCRIPTION` | `Boiler and radiators, mains gas ` |
| `MAINHEAT_ENERGY_EFF` | `Good ` |
| `MAINHEAT_ENV_EFF` | `Good ` |
| `MAINHEATCONT_DESCRIPTION` | `Programmer, room thermostat and TRVs ` |
| `MAINHEATC_ENERGY_EFF` | `Good ` |
| `MAINHEATC_ENV_EFF` | `Good ` |
| `SECONDHEAT_DESCRIPTION` | `None ` |
| `SHEATING_ENERGY_EFF` | `N/A ` |
| `SHEATING_ENV_EFF` | `N/A ` |
| `HOTWATER_DESCRIPTION` | `From main system ` |
| `HOT_WATER_ENERGY_EFF` | `Good ` |
| `HOT_WATER_ENV_EFF` | `Good ` |
| `LIGHTING_DESCRIPTION` | `Good lighting efficiency ` |
| `LIGHTING_ENERGY_EFF` | `Good ` |
| `LIGHTING_ENV_EFF` | `Good ` |
| `AIR_TIGHTNESS_DESCRIPTION` | |
| `AIR_TIGHTNESS_ENERGY_EFF` | |
| `AIR_TIGHTNESS_ENV_EFF` | |
| `CO2_EMISSIONS_CURRENT` | `2.00` |
| `CO2_EMISSIONS_POTENTIAL` | `0.60` |
| `HEATING_COST_CURRENT` | `1896.0000` |
| `HEATING_COST_POTENTIAL` | `1266.0000` |
| `HOT_WATER_COST_CURRENT` | `417.00` |
| `HOT_WATER_COST_POTENTIAL` | `417.00` |
| `LIGHTING_COST_CURRENT` | `117.00` |
| `LIGHTING_COST_POTENTIAL` | `117.00` |
| `ALTERNATIVE_IMPROVEMENTS` | |
| `LZC_ENERGY_SOURCES` | |
| `SPACE_HEATING_DEMAND` | `6561.15` |
| `WATER_HEATING_DEMAND` | `1864.76` |
| `IMPACT_LOFT_INSULATION` | `0` |
| `IMPACT_CAVITY_WALL_INSULATION` | `0` |
| `IMPACT_SOLID_WALL_INSULATION` | `0` |
| `ADDENDUM_TEXT` | |
| `CONSTRUCTION_AGE_BAND` | `before 1919` |
| `FLOOR_HEIGHT` | |
| `DATA_ZONE` | `S01002243 (Bonnington and Pilrig)` |
| `ENERGY_CONSUMPTION_POTENTIAL` | `163.00` |
| `EXTENSION_COUNT` | `0` |
| `FIXED_LIGHTING_OUTLETS_COUNT` | `0` |
| `LOW_ENERGY_FIXED_LIGHT_COUNT` | `0` |
| `LOW_ENERGY_LIGHTING` | `0.00` |
| `FLOOR_LEVEL` | `ground floor` |
| `FLAT_TOP_STOREY` | `00` |
| `GLAZED_AREA` | `0` |
| `NUMBER_HABITABLE_ROOMS` | `2` |
| `HEAT_LOSS_CORRIDOOR` | `unheated corridor` |
| `NUMBER_HEATED_ROOMS` | `2` |
| `LOCAL_AUTHORITY_LABEL` | `Edinburgh City` |
| `MAINS_GAS_FLAG` | |
| `MAIN_HEATING_CATEGORY` | |
| `MAIN_FUEL` | |
| `MAIN_HEATING_CONTROLS` | |
| `MECHANICAL_VENTILATION` | `natural` |
| `ENERGY_TARIFF` | `Single` |
| `MULTI_GLAZE_PROPORTION` | `0` |
| `GLAZED_TYPE` | |
| `NUMBER_OPEN_FIREPLACES` | |
| `PHOTO_SUPPLY` | |
| `SOLAR_WATER_HEATING_FLAG` | `N` |
| `TENURE` | `owner-occupied` |
| `TRANSACTION_TYPE` | `marketed sale` |
| `UNHEATED_CORRIDOR_LENGTH` | `8.52` |
| `CONSTITUENCY` | `00QPMM` |
| `CONSTITUENCY_LABEL` | `Leith Walk` |
| `WIND_TURBINE_COUNT` | `0` |
| `BUILT_FORM` | |
| `PROPERTY_TYPE` | `Flat` |
| `DATA_ZONE_2011` | `S01008814 (Pilrig - 02)` |
| `CREATED_AT` | `27/03/2026 09:47:24` |
| `REPORT_REFERENCE_NUMBER` | `0000-2344-0322-7029-1763` |
