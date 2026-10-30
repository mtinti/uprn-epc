# Scottish data zone reference lists

Two lists, each copied on 30 October 2026 from the sibling project that already pins it, with
the same URL and hash, so the three projects agree on what a valid zone is. The build reads
only the code column of each, to give every parsed data zone a status and to fail on a well
formed code that is in neither list.

| File | SHA256 | Zones | Vintage | Pinned in | Source |
| --- | --- | ---: | --- | --- | --- |
| `SG_SIMD_2012.dbf` | `4dc58c30c7d023e4e39739e9d2e56fa9f4153a41ef4eeacbe9ba95d60e319095` | 6,505 | 2001 | postcode-simd, `simd_ingest/sources.yaml`, `sg_simd_2012` | https://maps.gov.scot/ATOM/shapefiles/SG_SIMD_2012.zip (member `SG_SIMD_2012.dbf`), mirrored at https://zenodo.org/records/23119743. Scottish Government, Open Government Licence, stated in the shapefile's own metadata. |
| `DataZone2011_lookup.csv` | `688416b875733f62d5ceede1ac2b73c9db021e816ea8a9c6c58da0f105b601b6` | 6,976 | 2011 | datazone-ahah, `ahah_ingest/sources.yaml`, `datazone_lists` | https://data.gov.scot/dataset/2011_data_zone_lookup. Scottish Government, Open Government Licence v3.0. The file is cp1252, not UTF-8. |

The SIMD 2012 boundary table is the attribute table of a shapefile: one row per 2001 data
zone, code in column `DataZone`, read with the standard-library DBF reader in
`epc_ingest/core/dbf.py`. datazone-ahah has no 2001 list because its data start at the 2011
geography; the extract carries no 2022 zone, so no 2022 list is pinned here.
