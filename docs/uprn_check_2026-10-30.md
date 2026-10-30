# Check: are the short UPRNs in the EPC extract real?

Date: 30 October 2026. Scripts: `tools/uprn_extract.py`, `tools/uprn_check_os_open_uprn.py`.

## Question

`OSG_REFERENCE_NUMBER` holds UPRNs of 8 to 12 digits. A UPRN is an integer of up to 12 digits.
Could the 8-digit values be 12-digit values that lost leading zeros on the way out of a spreadsheet?

## Reference

OS Open UPRN, September 2026 release (extraction date 14 August 2026), Ordnance Survey, Open
Government Licence. One row per UPRN in Great Britain with grid coordinates; no address text.
Downloaded from https://api.os.uk/downloads/v1/products/OpenUPRN/downloads?area=GB&format=CSV
(zip 619,271,161 bytes). Not pinned; this was a one-off check.

## Result

Of the 1,885,772 distinct UPRNs in the extract:

| length | distinct in EPC | found in OS Open UPRN | main councils |
| --- | ---: | ---: | --- |
| 8 | 17,933 | 17,933 (100.00%) | Clackmannanshire |
| 9 | 1,439,867 | 1,439,320 (99.96%) | Edinburgh, Fife, North Lanarkshire |
| 10 | 137,837 | 137,808 (99.98%) | Aberdeen City, Dundee City |
| 11 | 13,303 | 13,302 (99.99%) | Shetland, Edinburgh |
| 12 | 276,832 | 276,554 (99.90%) | Glasgow City, West Lothian |

The 8-digit matches all fall inside eastings 283,678 to 301,567 and northings 689,042 to 702,499,
the grid square that holds Alloa and the rest of Clackmannanshire.

## Reading

The UPRN length follows the council, not the year or the file. That is how UPRNs are issued:
each custodian has its own number range. The values are real UPRNs as printed. Nothing was lost.

The 0.04% to 0.10% not found are UPRNs that OS no longer lists, which happens when a property is
demolished, merged or re-referenced. They are a fact about the register, not an error in the
extract, and the build does not fail on them.

## Rule for users

Compare UPRNs as integers. A cohort file that pads UPRNs to 12 digits with zeros joins correctly
once both sides are cast to bigint, and fails silently if compared as text.
