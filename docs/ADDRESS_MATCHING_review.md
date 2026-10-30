# Matching CHI patient addresses to UPRNs for the Scottish EPC join

Review of reference products, algorithms, published experience and pitfalls. Written for a health
informatics team working inside a trusted research environment (TRE) with no internet access.
All sources were read on 2026-10-29. Claims that no source confirmed are marked **unverified**.

## 1. Summary and recommendation

The EPC side of the join is already solved. Each Scottish domestic EPC record carries an OSG UPRN
(`OSG_REFERENCE_NUMBER`), and a 2023 analysis of the Scottish extract found that over 99% of the
records that had a UPRN had a valid one (geo.fyi). The work is on the CHI side: free-text address
lines plus postcode, which need a UPRN from the One Scotland Gazetteer (OSG) or from a product that
carries the same UPRNs.

Try the routes in this order.

1. **Ask for a UPRN that already exists before matching anything.** Public Health Scotland (PHS)
   holds the CHI-UPRN Residential Linkage (CURL). PHS built it in 2020 by sending 3.2 million unique
   CHI address strings to the Improvement Service DataHub. 89.3% of 5.8 million registrations got a
   UPRN. A 2023 to 2024 extension aimed to seed the 31 million address history rows since 2000, with a
   95% target. CURL is released to approved projects through eDRIS and the National Safe Haven. If the
   project can request CURL, or the PHS address history file already carries a UPRN, join on CHI and
   address date and skip steps 2 to 4 for those rows. Whether CURL covers your cohort and dates is
   **unverified** and must be asked of PHS.
2. **Bring a reference product with address text into the TRE.** Pick one of: the full OSG extract
   from the Improvement Service, OS AddressBase Premium (Scotland subset, free to PSGA members), or
   the NRS Scottish Address Directory (PSGA members only). All three carry the OSG UPRN, the parent
   UPRN, lifecycle status and structured address fields. OS Open UPRN and ONSUD are free but carry no
   address text, so they cannot be matched against. They are still useful for coordinates and
   geographies after matching.
3. **Match deterministically first, with Scottish flat conventions standardised.** Block on
   postcode. Build matchkeys from standardised sub-building, building number, building name and
   street, in the order NRS used for Scotland's Census (groups A to E, then fuzzy). This is the method
   with the best published evidence on Scottish health addresses: 86% of 3.6 million unique NHS
   address strings linked to one Scottish Address Directory record, and 100% of a clerically reviewed
   sample of the exact-key links were correct. It needs no special software.
4. **Run a probabilistic or learned matcher on the residue, then review a stratified sample.**
   `uk_address_matcher` (Splink on DuckDB, pure pip install, MIT) or FLAP (Random Forest plus fuzzy
   alignment, trained on NHS Fife and Tayside CHI addresses, MIT) both run offline on a laptop. FLAP
   reported adjusted accuracy 0.992 on 3,876 CHI addresses. Accept matches above a threshold you set
   from your own review sample, not from the published figures.
5. **Treat the remainder as unmatched, and report it by type.** Expect care homes, student halls,
   flats with no sub-building text, rural named properties and wrong postcodes to dominate.

Reasons for the order. Route 1 reuses work PHS has already validated and avoids re-identification
risk from moving address text. Route 2 is the only way to match offline. Route 3 gives auditable,
explainable matches and catches 80 to 90% of records in published Scottish work. Route 4 adds a few
percent at a measurable cost in precision, so it comes after the exact keys and before any manual
work. Heavier tools (ONS Address Index on Elasticsearch, ASSIGN on a MUMPS database) are not worth
installing inside a TRE for one cohort.

## 2. Reference products

| Product | Owner | Carries address text? | UPRN | Key fields | Licence and route in | Notes |
|---|---|---|---|---|---|---|
| One Scotland Gazetteer (OSG) | Improvement Service, from the 32 council Corporate Address Gazetteers; BS7666 | Yes | OSG UPRN, the one on EPC records | UPRN, USRN, address lines, coordinates, classification, lifecycle status (field list on the public site is **unverified**: the pages returned 403 or 404) | Public sector only. data.gov.uk records name OSMA in one place and PSGA in another; Scotland moved from OSMA to PSGA on 19 May 2020. Contact gazhelp@improvementservice.org.uk or gazcustomers@improvementservice.org.uk. SOAP and REST API via osg.scot; bulk extract on request. Not sold commercially; commercial route is AddressBase | The Improvement Service allocates UPRN blocks in Scotland. Updated continually |
| OS AddressBase Premium | Ordnance Survey; Scottish records sourced from OSG via GeoPlace | Yes (LPI and Delivery Point Address) | Same UPRN as OSG for Scotland | UPRN (integer, max 12 digits), PARENT_UPRN, LOGICAL_STATUS (1 approved, 6 provisional, 8 historical), BLPU_STATE, MULTI_OCC_COUNT, COUNTRY (S for Scotland), SAO and PAO number, suffix and text, USRN, X/Y and lat/long, classification (RD residential) | Free to PSGA members through OS Data Hub. Data Exploration licence gives a three-month trial. Members may share with contractors | CSV, GeoPackage, GML. Six-weekly epochs. Whole lifecycle including provisional and historical records |
| OS AddressBase Core / Plus | Ordnance Survey | Yes, but one address per UPRN and fewer lifecycle records | Yes | Simplified single-line fields | PSGA | Core lacks parent-child and alternative addresses. Use Premium for flats (**inference from product family descriptions**) |
| NRS Scottish Address Directory (SAD) | National Records of Scotland | Yes | OSG UPRN, USRN, Royal Mail UDPRN | Organisation, property, building number, street, locality, town, postcode, plus NRS geographies | PSGA members only; contact NRS Geography Customer Services. Licence text **unverified** | Built from AddressBase Premium, PAF, OSG and the Scottish Postcode Directory. Used as the Census Address Register source |
| NRS Scottish Postcode Directory (SPD) | NRS | No | No | Postcode, geographies, centroids | Postcode index free; boundaries PSGA | Use for postcode validity and geography, not for UPRN |
| OS Open UPRN | Ordnance Survey | No | Yes | UPRN, X, Y, latitude, longitude only. All lifecycle states | Free, OS Data Hub, open identifiers released under OGL | Good for checking that a UPRN exists and for coordinates |
| OS Open Linked Identifiers | Ordnance Survey | No | Yes | UPRN to USRN, UPRN to TOID, street and road links | Free, OS Data Hub | Lets you attach a street (USRN) to a UPRN |
| ONS UPRN Directory (ONSUD) | ONS Geography | No | Yes | UPRN to statistical, health and administrative geographies, GB wide including Scotland | Listed as "No Licence Provided"; contains Royal Mail, OS and ONS rights | Six-weekly. Use for geography after matching |
| Scottish domestic EPC extract | Scottish Government, from the Scottish EPC Register (Energy Saving Trust) | Yes: ADDRESS1, ADDRESS2, POSTTOWN (your ADDRESS3), POSTCODE | `osg_reference_number` and a separate EPC `building_reference_number` | 104 attributes; geocoded through the Improvement Service Data Hub using OSG coordinates (stated for the Spatial Hub new-dwellings subset) | Non-address fields OGL v3; address fields under Royal Mail terms, with osg.scot named for address licensing | Quarterly. Free text addresses with inconsistent case and spelling, for example "DUNFERMLIME" 2,336 times |

Products that carry address text: OSG, AddressBase Premium, SAD, and the EPC extract itself.
Products with UPRN but no text: OS Open UPRN, OS Open Linked Identifiers, ONSUD.

## 3. Algorithms and tools

| Tool or method | What it does | Flats and sub-buildings | Published results | Needs installed | Fit for a TRE |
|---|---|---|---|---|---|
| Deterministic matchkeys (NRS Census method) | Standardise, then exact-match concatenated keys in passes: A and B (property plus postcode, or property, street and postcode), C and D (property, street and town without postcode), E (numbers and postcode only, with slash forms swapped), then fuzzy on house names within postcode | Explicit Scottish rules: `13-2` to `13/2`, `GROUND FLOOR RIGHT` to `G/R` then `0/2`, `Flat A, 32` to `32A`, `7/3` tried as both flat 7 of 3 and flat 3 of 7 | 86% of 3.6 million NHS address strings linked to one SAD record, 1% to two or more, 13% none. Reviewed links: groups A to D 98.7 to 100% correct, group E 94.1%, fuzzy 91.5% | SAS at NRS; trivially rewritten in SQL or Python | Best first pass. Fully auditable |
| OS "introduction to address matching" | Prepare AddressBase columns, clean input, constrain to postcode, exact pass, fuzzy pass, substitution pass. Match the parent first, then the secondary within the parent set | Primary then secondary matching | None published | Any database with full-text search (PostgreSQL tsvector shown) | Same family as above |
| ONS Address Index (AIMS) | CRF parser labels tokens; Elasticsearch per-field queries with synonyms, limited Levenshtein, dismax, TF-IDF fallback on concatenated address; confidence score is the higher of the scaled Elasticsearch ratio and a rule-based score with locality, building and unit levels | Unit-level rules; building-level matches can remain ambiguous between flats | On 200,000 labelled records: 97.5% top match, 1.13% in top five, 0.03% not found, 1.34% wrong. CRF whole-address accuracy over 98%. Resolved 96% automatically against 80 to 85% for a commercial tool on 11,000 addresses | Scala/Play API, Elasticsearch 7.17 index built from AddressBase Premium; repo README was not reachable (404) so build steps are **unverified** | Heavy. Reuse its design, not its stack |
| libpostal | C library. Parses to labels (house, house_number, unit, level, road, postcode, city and others) and expands abbreviations. Senzing model improves UK parsing by 4.3% on its test set | `unit` and `level` labels exist. No UK flat-specific documentation | None for UK matching | Build from source, 1.8 GB data (2.2 GB Senzing) fetched from S3 at build time; pypostal binding; MIT | Only if you can stage the data files. Regex rules cover Scottish flats better |
| Splink | Fellegi-Sunter probabilistic linkage with term-frequency adjustment and custom comparisons. DuckDB backend runs locally; Spark for scale | Whatever comparison columns you define | "A million records on a laptop in around a minute" | `pip install splink`, Python 3.9+, MIT | Good, offline, pure Python plus DuckDB |
| uk_address_matcher | Splink wrapper: cleans and tokenises, exact stages, then probabilistic, then re-scores by distinguishing and punishment tokens within a candidate group. Output has match weight and distinguishability | Shown matching "Flat A"; method not documented | 100,000 addresses in about 30 seconds; whole-UK preprocessing about 10 minutes. Accuracy figures not on the page | `pip install uk_address_matcher`, DuckDB, MIT. Input columns `unique_id`, `address_concat`, `postcode` | Good second pass. Author's 2026 IJPDS paper says accuracy is competitive with open tools |
| FLAP (flap_lite) | Regex parse of postcode, post town and thoroughfare; database augmentation that generates alternative forms (for example "5/1" as "Flat 1, 5"); tree blocking by postcode or post town and thoroughfare; Needleman-Wunsch plus Damerau-Levenshtein alignment; Random Forest on 52 features; score threshold default 0.3 | Alternative form generation; no further flat logic | NHS Fife and Tayside CHI, 771,588 addresses: raw accuracy 0.950, adjusted 0.992, precision 0.993, recall 0.983 on 3,876 reviewed. 4.18% of the sample could not be matched by hand. 6.94 addresses per second | Python, scikit-learn, scipy, SQLite; pretrained `.clf` shipped; needs AddressBase Premium to build the database; MIT. Written to avoid external services for safe havens | Good third pass or validator. Slow but offline |
| ASSIGN | 213-rule deterministic matcher: reformat to eleven then five fields (flat, building, number, street, postcode), postcode-area blocking, ranked rules from exact to Levenshtein, regex and field swaps | Flat field; qualifiers best, child, parent, sibling; floor-level forms like "2b" | Gold standards: 99.5% (Wales, 9,177) and 99.6% (Tower Hamlets, 9,475); PPV 0.996 and 0.998. 98.6% of 1.76 million north east London patients. Flat addresses starting with a letter caused misses | MUMPS hierarchical database plus SQL reference tables from AddressBase Premium; AGPL-3.0; about 38,000 records per minute | Hard to install. Reuse its rule ideas |
| Improvement Service DataHub | Scottish public sector matching service against OSG. Returns best UPRN and a quality category (EXCELLENT, GOOD, FAIR). Algorithm not published | Not published | CHI 2020: 89.3% matched; 78.8% EXCELLENT, 8.3% GOOD, 2.2% FAIR. Care homes 60% automatic | Hosted service; cannot run inside a TRE | Use through PHS or the Improvement Service, outside the TRE, on unique address strings only |
| OS Places API, OS Match and Cleanse API | Hosted matching against AddressBase with scores 1.0 exact, 0.8 to 0.9 good, 0.7 partial. Match and Cleanse withdrawn 31 March 2026 | Not documented | None | Internet | Not usable offline |
| Fuzzy string measures | Jaro-Winkler, Levenshtein, Damerau-Levenshtein, longest common substring. NRS used two scores (longest common run, and edit operations including jumps) within postcode | Apply to building names, never to numbers | NRS fuzzy pass: 91.5% clearly correct, 6.6% plausible alternatives (farms and cottages) | Any string library | Last automatic pass, restricted to one postcode, with review |

## 4. Published experience with match rates

| Study | Data | Reference | Method | Result | Failures and validation |
|---|---|---|---|---|---|
| Clark and Dibben 2022 (CURL) | 5,828,951 CHI registrations, 3,208,951 unique address strings, August 2020 | OSG via DataHub | Pre-formatting, DataHub, manual search for care homes | 89.3% got a UPRN (78.8% EXCELLENT, 8.3% GOOD, 2.2% FAIR) | Only 60% of 40,196 care-home-flagged records matched automatically; manual review gave 42,334 residents a UPRN. 1,724 pairs stratified by category and urban-rural reviewed; precision "estimated to be more than 95%" and "still to be verified". Frontiers 2023 notes CURL rules were not published and performance was not evaluated on labelled data |
| Clark 2024 (CURL Extensions) | 31 million CHI address history rows since 2000 | Not stated | "Alternative address-matching algorithms"; QA on precision and sensitivity across time and geography | Target 95%; achieved rate not published | ADR Scotland funded a 2023 rebuild with six-monthly refreshes; current status **unverified** |
| NRS Census 2022 methods paper (Health Activity 2016 development set) | 3,639,583 unique NHS address strings | Scottish Address Directory (2,804,101 strings) | Matchkey groups A to E then fuzzy, in SAS | 86.0% one link, 1.0% two or more, 13.0% none | Of 1,000 reviewed links 993 correct, 2 plausible, 5 wrong (4 from wrong postcodes in group E, 1 "Room 1" matched to building 1). Non-links in a 100 sample: 33 missing flat detail, 20 different flat conventions, 18 property absent or non-residential or named versus numbered, 11 student halls (SAD holds the building only), 10 wrong postcode, 8 quirks. 113,775 addresses had a missing or invalid postcode |
| Zhang et al. 2023 (FLAP) | 771,588 CHI addresses, NHS Fife and Tayside, April 2017 | OS UPRN database (AddressBase Premium) | Random Forest plus fuzzy alignment | Adjusted accuracy 0.992; raw 0.950 | 162 of 3,876 (4.18%) unmatchable by hand. Of 31 errors: 7 needed local knowledge (halls, room numbers read as building numbers), 6 partly wrong input aligned to another record, 4 wrong postcode plus wrong town or street. Blocking fails without a correct postcode or town and street. Two annotators, kappa 0.980 |
| Harper et al. 2021 (ASSIGN) | 1,757,018 GP patients, north east London | AddressBase Premium epoch 75 | 213 ranked rules | 98.6% of patients; gold standards 99.5% and 99.6% | Lower for recent movers (95.4%), Chinese ethnicity (95.5%), SystmOne practices (94.4%), ages 15 to 29 and 85 plus, missing postcode-based IMD (23.5%), a homeless practice, Tower Hamlets practices with more flats. False matches 0.38% and 0.17% on gold standards |
| Harper et al. 2019 (Discovery) | 879,286 GP patients, four east London boroughs | AddressBase Premium | 213 ranked rules | 99% assigned | Sensitivity 0.993, PPV 0.914 against an independent validated NHS address set. Less likely linked: men, ages 15 to 24 and 90 plus, Chinese ethnicity, least deprived quintile |
| ONS working paper 17 (AIMS) | Six test sets, about 200,000 labelled and 30,000 unlabelled | AddressBase | CRF plus Elasticsearch | 97.5% top match, 1.34% wrong, 0.03% not found | Parsing errors only recovered by fallback; several mediocre candidates can each look acceptable; business names often absent |
| UBDC 2026 (EPC to UPRN lookup, England and Wales) | DLUHC EPC records | AddressBase Plus | Not described on the page | 96% matched, against 93% in the government linkage | UBDC news item: address quality is the main obstacle; parent-child and retired UPRNs need agreed rules |
| DLUHC EPC release 2021 (England and Wales) | EPC back to 2008 | AddressBase | Address matching algorithm checked against OS and GeoPlace | "Up to 99%" | Assessor-assigned UPRNs from September 2020; new builds less complete |
| Improvement Service DataHub, West Lothian | National Entitlement Card holders over 60 | OSG | DataHub | 97% validated | News report; no method |
| UK Biobank | No published UPRN assignment found | | | | **No source found.** UK Biobank covers 22 assessment centres, of which Glasgow and Edinburgh are in Scotland, but no UPRN linkage paper surfaced |

Themes across studies. Exact-key passes are near perfect. Error concentrates in the numbers-only and
fuzzy passes and in wrong postcodes. Flats fail in two ways: the record lacks a sub-building
(building-level only), or the convention differs (`1F2`, `12/3`, `Flat 3`, `Flat C`) with no
universal mapping. Communal settings (care homes, student halls) are held at building level in the
gazetteer, and the patient record often holds a room or unit. Recent movers and young adults match
less well, which is also a bias in any health analysis.

## 5. Pitfalls for CHI to EPC

**CHI address format.** No public CHI address specification was found (**unverified**). PHS
describes CHI addresses as "unstructured free-text". The GP system vendor guidance for Scottish
Registration Links says long lines may be truncated, flat numbers go in the House Name field, a
second thoroughfare goes after the first in Number and Road separated by a comma, and if space runs
out the second thoroughfare moves to Locality or is dropped. Expect the flat identifier in any line,
truncated street names, and locality or town in the wrong line. Ask PHS for the CHI address layout
(line count, lengths, postcode field) before building parsers.

**EPC address fields.** Assessors type ADDRESS1 and ADDRESS2 and the post town. Case and spelling
vary (DUNFERMLIME; Perth and Inverness replaced by their shire). Scottish assessment software
requires a UPRN at lodgement. One vendor page says the Scottish UPRN is 10 digits against 12
elsewhere; a Spatial Hub dataset says OSG UPRNs are 8, 9 or 12 digits as defined by the council.
These statements conflict, so treat the length as variable and **unverified**. Over 99% of EPC
records with a UPRN had a valid one in the 2023 analysis, but the share with no UPRN was not stated.
Count it in your extract.

**UPRN as a key.** AddressBase stores UPRN as an integer of up to 12 digits. Published examples
show both padded (`000000199356`) and unpadded forms. Compare as integers, or as text after
stripping leading zeros and whitespace. Never compare a padded text to an unpadded text. Check for
scientific notation if the EPC CSV passed through a spreadsheet.

**Parent and child UPRNs.** A tenement close has a parent BLPU and one child per flat;
`PARENT_UPRN` and `MULTI_OCC_COUNT` describe the relationship. The EPC may be lodged against the
flat's child UPRN or, in error, against the parent. CHI may match only to the parent when the flat
text is missing. Store the matched UPRN, its parent, and the match level (unit or building). Join
EPC to CHI on the child first, then on parent where either side is at building level, and flag such
joins as building-level, because the EPC then describes a different dwelling.

**Flat conventions.** `1F2` means first floor, flat 2, counted from the door furthest from the
stair; postal `12/3` style gives position in the stair; some owners renumber plainly. NRS found 20
of 100 unmatched flats failed on convention alone and warns there is no universal mapping, even
within a street. Apply the NRS standardisation on both sides, try both slash orders, and never
convert `1F2` to `Flat 2` or `12/3` to `Flat 3` without a building-specific rule.

**Historic and provisional records.** OSG and AddressBase keep historical (status 8) and
provisional (status 6) records. A CHI address dated 2015 may need a UPRN that is now historical.
Keep all statuses in the reference and record the status of the match. New builds may have an EPC
lodged before the gazetteer record is approved (**unverified** for Scotland; DLUHC said new-build
UPRNs are less complete in England and Wales).

**Address dates.** CHI holds address start dates. Choose the CHI address in force at the EPC
inspection or lodgement date, or over the exposure window, and say which. A person has many
addresses and a dwelling has many EPCs. Decide the pairing rule before matching.

**Communal settings.** Care homes matched 60% automatically in CURL. Student halls appear as one
building in SAD. Match these at building level and flag them. The EPC for a care home is usually a
non-domestic certificate, so the join to the domestic extract will fail by design.

**Rural named properties and Gaelic spellings.** Fuzzy name matching within postcode gave 6.6%
plausible alternatives (Hillhead Farm versus Hillhead Cottage). Require manual review for fuzzy
matches on names, and keep `Mac` to `Mc` folding.

**Wrong postcodes.** Four of five wrong links in the NRS review came from wrong postcodes in the
health data. Validate postcodes against the SPD first. Only allow a postcode-free pass (groups C and
D) when street and town agree.

**Licences inside the TRE.** EPC address fields are under Royal Mail terms, OSG and AddressBase
under PSGA. Confirm the TRE operator is covered, and keep address text out of outputs.

## 6. Proposed matching pipeline

1. **Ask PHS for existing UPRNs.** Request CURL or the UPRN-seeded CHI address history for the
   cohort. Check: share of cohort address rows with a UPRN, by year and by health board. If above
   your target, use it and go to step 9 for the rows that lack one.
2. **Bring in the reference.** Obtain the OSG extract or AddressBase Premium (COUNTRY = S) under
   PSGA, plus the SPD postcode index and OS Open UPRN. Load into DuckDB or PostgreSQL. Check: every
   EPC `OSG_REFERENCE_NUMBER` exists in the reference as an integer; report the share missing and the
   split by LOGICAL_STATUS. Check: UPRN count per postcode, and MULTI_OCC_COUNT for parents.
3. **Profile both address sources.** Count CHI rows by number of non-empty lines, by presence of a
   digit, by flat tokens (`FLAT`, `/`, `F`, `1F2` pattern), by postcode validity against the SPD.
   Do the same for EPC ADDRESS1 and ADDRESS2. Check: list the 200 most common tokens on each side and
   build the abbreviation table from them.
4. **Standardise.** Apply the NRS minimal and full standardisations to CHI and to the reference LPI
   fields (SAO and PAO number, suffix and text, street, locality, town). Keep `-` and `/` in the
   minimal pass. Produce both versions. Check: a fixed test set of 50 hand-written Scottish
   addresses (tenement, 4-in-a-block, farm, care home, student hall) round-trips to the expected
   standard form.
5. **Deterministic passes with postcode blocking.** Run groups A and B (property and street with
   postcode), C and D (without postcode but with street and town), E (numbers only with postcode,
   both slash orders, `Flat A` suffixing), in that order, minimal then full standardisation, removing
   matched rows after each pass. Record the pass that matched and whether the match is unit or
   building level. Check: a row that links to two or more UPRNs in one pass is not accepted; count
   these. Check: review 200 links per pass; accept a pass only if its reviewed precision is at or
   above your threshold (NRS saw 98.7 to 100% for A to D and 94.1% for E).
6. **Probabilistic pass on the residue.** Run `uk_address_matcher` (or Splink directly) with
   `address_concat` and postcode, against the reference restricted to the same postcode or postcode
   sector. Keep match weight and distinguishability. Optionally score the same residue with FLAP and
   keep matches where both agree. Check: review 300 accepted matches stratified by weight band and
   urban-rural class; set the acceptance threshold where precision meets your target. Check: the
   share of residue matched at building level only.
7. **Resolve parent and child.** For every match record UPRN, PARENT_UPRN and level. Where CHI
   matched the parent and the parent has children, do not pick a child. Check: count CHI rows at
   building level in multi-occupancy parents; these cannot be joined to a flat-level EPC.
8. **Join to EPC.** Join on integer UPRN. Where no EPC has the child UPRN, try the parent and flag
   the join as building-level. Apply the date rule from section 5. Check: share of CHI address rows
   with any EPC, with an EPC in window, and with a flat-level EPC. Check: a sample of 100 joined pairs
   compared by eye on CHI text versus EPC ADDRESS1 and ADDRESS2 after standardisation; report
   disagreements.
9. **Report the unmatched by reason.** Classify unmatched CHI rows: invalid postcode, no digits and
   no name, flat convention conflict, communal establishment, property absent from reference,
   other. Use the NRS categories so results compare. Check: the unmatched share by age band, year
   of address, health board and urban-rural class, because selective loss biases the analysis.
10. **Freeze and document.** Store the reference epoch, standardisation tables, pass definitions,
    thresholds, review samples and precision per pass with the output. Repeat step 5 and 6 reviews
    whenever the reference epoch or the cohort changes.

## 7. Sources

All read on 2026-10-29.

- Clark D, Dibben C. Adding a Residential Dimension to the Scottish Population Spine: CHI-UPRN Residential Linkage (CURL). IJPDS 2022. https://ijpds.org/index.php/ijpds/article/view/1946 (abstract only; full text at PMC9644897 was behind a browser check)
- Clark D. CURL Extensions: Weaving a UPRN into Address Histories in the Scottish CHI. IJPDS 2024. https://ijpds.org/index.php/ijpds/article/view/2808
- SCADR. UPDATE: PHS receives funding to update CURL files. https://www.scadr.ac.uk/node/351 (search snippet; page returned 403)
- ADR UK. Developing an innovative residential linkage tool for Scotland. https://www.adruk.org/our-mission/our-impact/article/developing-an-innovative-residential-linkage-tool-for-scotland/
- Scottish Government Digital blog. Linking the people and places of Scotland, 2021. https://blogs.gov.scot/digital/2021/09/03/linking-the-people-and-places-of-scotland/
- NRS. Scotland's Census 2022: Census to CCS address linking (methods paper, PDF). https://www.scotlandscensus.gov.uk/media/53wcnopb/scotlands-census-2022-admin-data-census-to-ccs-address-linking-final.pdf
- Zhang H et al. FLAP: a framework for linking free-text addresses to the OS UPRN database. Frontiers in Digital Health 2023. https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2023.1186208/full
- flap_lite repository. https://github.com/huayu-zhang/flap_lite
- Harper G et al. Evaluation of the ASSIGN open-source deterministic address-matching algorithm. IJPDS 2021. https://ijpds.org/index.php/ijpds/article/view/1674
- ASSIGN repository. https://github.com/endeavourhealth-discovery/ASSIGN
- Harper G et al. Allocating UPRNs to GP-recorded patient addresses: representativeness and bias. IJPDS 2019. https://ijpds.org/index.php/ijpds/article/view/1282
- ONS working paper series no 17. Using data science for the address matching service. https://www.ons.gov.uk/methodology/methodologicalpublications/generalmethodology/onsworkingpaperseries/onsworkingpaperseriesno17usingdatasciencefortheaddressmatchingservice
- ONS address-index-api repository. https://github.com/ONSdigital/address-index-api (README fetch returned 404; stack details from search snippet)
- Linacre R. uk_address_matcher. https://github.com/RobinL/uk_address_matcher and IJPDS 2026 article https://ijpds.org/index.php/ijpds/article/view/3744 (search snippet)
- Splink. https://github.com/moj-analytical-services/splink
- libpostal. https://github.com/openvenues/libpostal
- OS. An introduction to address matching. https://docs.os.uk/more-than-maps/using-addressing/an-introduction-to-address-matching
- OS. AddressBase Premium product page. https://docs.os.uk/os-downloads/addressing-and-location/addressbase-premium
- OS. AddressBase Premium BLPU (Type 21) record. https://docs.os.uk/os-downloads/addressing-and-location/addressbase-premium/addressbase-premium-technical-specification/feature-types/blpu-type-21-record
- Ideal Postcodes. AddressBase Premium field reference (LPI SAO/PAO, status codes, country codes). https://docs.ideal-postcodes.co.uk/docs/data/addressbase-premium
- OS. OS Open UPRN overview. https://docs.os.uk/os-downloads/identifiers/os-open-uprn/os-open-uprn-overview
- OS. OS Open Linked Identifiers technical specification. https://docs.os.uk/os-downloads/identifiers/os-open-linked-identifiers/os-open-linked-identifiers-technical-specification
- OS. OS Match and Cleanse API (end of life 31 March 2026) and OS Places scoring. https://docs.os.uk/os-apis/accessing-os-apis/os-match-and-cleanse-api and https://docs.os.uk/os-apis/accessing-os-apis/os-places-api/datasets (search snippets)
- OS news. Scotland joins the Public Sector Geospatial Agreement, 2020. https://www.ordnancesurvey.co.uk/news/scotland-joins-the-public-sector-geospatial-agreement (search snippet)
- OS. Public Sector Geospatial Agreement. https://www.ordnancesurvey.co.uk/customers/public-sector/public-sector-geospatial-agreement
- data.gov.uk. One Scotland Gazetteer SOAP service record. https://www.data.gov.uk/dataset/afa13da8-be98-4743-895e-a05ad8ce5e3b/one-scotland-gazetteer-soap-service
- One Scotland Gazetteer portal. https://www.osg.scot/
- Wikipedia. One Scotland Gazetteer. https://en.wikipedia.org/wiki/One_Scotland_Gazetteer
- West Dunbartonshire Council. Council address database (UPRN block allocation by the Improvement Service). https://www.west-dunbarton.gov.uk/planning-building-standards/street-name-numbering/council-address-database/ (search snippet; page returned 404)
- Spatial Hub. NHS hospitals attribute info (UPRN 8, 9 or 12 digits). https://data.test.spatialhub.scot/sq/dataset/nhs_hospitals-is/resource/b810d206-45bd-4dff-bac7-110a50b4bd3b (search snippet)
- NRS. Scottish Address Directory and key data sources. https://nrscotland.gov.uk/statistics-and-data/geography/our-products/scottish-address-directory (search snippets; pages returned 403)
- NRS. Scottish Postcode Directory. https://spatialdata.gov.scot/geonetwork/srv/api/records/9fe3612b-ebf6-4ee7-a47e-bbe12168b3ff (search snippet)
- ONS UPRN Directory, September 2024. https://ckan.publishing.service.gov.uk/dataset/ons-uprn-directory-september-2024-epoch-112
- Wikipedia. Unique Property Reference Number. https://en.wikipedia.org/wiki/Unique_Property_Reference_Number
- Scottish Government. Domestic EPCs, dataset to Q1 2026. https://data.gov.scot/dataset/domestic_energy_performance_certificates___dataset_to_q1_2026
- Scottish EPC Register. Data extracts. https://dev.energycertificate.service.gov.scot/data-extracts
- geo.fyi. Scotland's Energy Performance Certificate data, 2023. https://geo.fyi/2023/04/12/scotlands-energy-performance-certificate-data/
- Spatial Hub. EPCs, new dwellings (geocoded via Improvement Service Data Hub). https://data.spatialhub.scot/dataset/domestic-energy-performance-certificates-historic-sap-new-dwellings (search snippet; page returned 403)
- DesignBuilder. EPC process in Scotland (UPRN required; "10 digits"). https://designbuilder.co.uk/helpv7.0/Content/ScottishEPCProcess.htm
- UBDC. Energy Performance Certificate to UPRN lookup, 2026. https://researchdata.gla.ac.uk/2211 and news item https://ubdc.ac.uk/news/key-solutions-to-unlock-the-power-of-location-data (search snippet)
- Open Data Communities. Energy Performance Certificates now include UPRN, 2021. https://news.opendatacommunities.org/energy-performance-certificates-now-include-uprn (search snippet)
- UKAuthority. Improvement Service rolls out Data Hub. https://ukauthority.com/articles/improvement-service-rolls-out-data-hub (search snippet)
- Cegedim Vision. Scotland and England differences for Registration Links (address entry rules). https://help.visionhealth.co.uk/DLM930/Registration_Links/Content/B_Getting_Started/Scotland_England_Differences_for_RegLinks.htm
- Midlothian Advertiser. Driven stair crazy by tenement numbering (1F2 convention). https://www.midlothianadvertiser.co.uk/news/opinion/columnists/driven-stair-crazy-by-tenement-numbering-helen-martin-3188988 (search snippet)
- PHS data dictionary, CHI number. https://publichealthscotland.scot/resources-and-tools/health-intelligence-and-data-management/national-data-catalogue/data-dictionary/search-the-data-dictionary/chi-number//html (no address fields)
