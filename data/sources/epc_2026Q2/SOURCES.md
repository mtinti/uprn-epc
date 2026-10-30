# Scottish domestic EPC extended historic dataset, release Q2 2026

Downloaded by Michele Tinti on 5 October 2026 from the Scottish Government's open data site,
https://data.gov.scot/dataset/domestic_energy_performance_certificates___extended_historic_dataset_to_q1_2026
(the catalogue slug still says Q1; the linked file is the Q2 2026 release; the same URL is
overwritten at every quarterly release). Publisher: Scottish Government, EPCenquiries@gov.scot.
Extracted from the Scottish EPC register on 1 September 2026; the publication note is dated
September 2026. Moved into this project on 30 October 2026 from `~/git_projects/epc_project/download/`.

Licence, from the publication note (page 2): Open Government Licence v3.0 for every field
except `ADDRESS1`, `ADDRESS2`, `ADDRESS3` (post town) and `POSTCODE`, which carry a Royal Mail
copyright notice that permits use for energy-efficiency purposes and requires the notice to
accompany any sharing. The build withholds the three address lines from the CSV and the
SQL table and the whole built table stays private (`docs/EPC_Plan.md`, section 5).

| File | SHA256 | Bytes | What it is |
| --- | --- | ---: | --- |
| `domestic_epc_extended_historic_Q2_2026.7z` | `708cc7510a0215ba7f9bf73ccc9604b1e818b04f355e06c6adb192611103c351` | 535,084,142 | The download: 19 annual CSV files and the publication note |
| `publication_note.pdf` | `c2f336967e5d9a6dd24fc8c842c81b23f9ae911f092778c1cef4426e332e982e` | 323,098 | The note, 17 pages, with the data dictionary (copy of the archive member `EPC Data - Q2 2026 Extract - EPD Extended Historic Data Publication Note - Domestic Buildings.pdf`) |
| `extracted/2008.csv` to `extracted/2026.csv` | in `epc_ingest/sources.yaml` | 7.6 GB in all | One file per year of `CREATED_AT`, extracted with bsdtar |
| `SHA256SUMS`, `download_metadata.json`, `archive_contents.txt`, `README.md` | | | The download session's own record |

Off-site copy: restricted Zenodo deposition 23784712 (draft, unpublished; files on request),
holding the archive, the note, `SHA256SUMS` and `download_metadata.json`, each MD5-verified
against this folder on 29 October 2026.

Checked on download and in the profile of 29 October 2026 (`docs/profile_2026-10-29.json`,
`docs/columns_2026-10-29.json`):

- 3,787,069 rows; 107 columns in every file, two header rows (machine names, then the
  publisher's labels), UTF-8 with a byte order mark, CRLF line endings. The label row holds
  U+FFFD where the publisher's file had a superscript 2 or a pound sign; no data row does.
- The note's dictionary lists 106 fields: it omits `DATA_ZONE_2011`, calls `ADDRESS3`
  `POST_TOWN`, and spells `3_YR_ENERGY_SAVING_POTENTIAL` without the S.
- `REPORT_REFERENCE_NUMBER` is empty in 340,010 rows (9%), mostly 2013 to 2016.
  `OSG_REFERENCE_NUMBER` (the Gazetteer UPRN) is empty in 178,537 rows (4.7%); its 8-digit
  values are real (`docs/uprn_check_2026-10-30.md`).
- Seven cells carry a trailing newline inside the quotes (six in `BUILDING_REFERENCE_NUMBER`,
  one in `ADDRESS1`); six `ADDRESS1` cells contain a double quote. The longest value is
  3,330 characters (`IMPROVEMENTS`).
