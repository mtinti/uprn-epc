# Response to the ingestion plan review of 30 October 2026

Review: `2026-10-30-ingestion-plan-review.md`. Each finding was checked against the plan text
and, where cited, against `~/git_projects/AHAH/ahah_ingest/sql_check.py`. All six hold. Both
plans were revised the same day. What changed:

| # | Finding | Holds | Change |
| --- | --- | --- | --- |
| 1 | Derived names collide with published names under case-insensitive identifiers | yes | Every typed copy now carries a kind suffix: `_parsed` (dates), `_flag` (bit), `_int`, `_num`. New-word names (`rrn`, `uprn_osg`, `pc_norm`, `datazone_2011`) stay. The schema check folds names to lower case and fails on a duplicate. Index definitions and the example query use the new names. |
| 2 | AHAH's loader turns every empty text cell into NULL | yes, `sql_check.py` lines 163 to 175 and its comment | Rule written into both plans: published columns `NOT NULL`, empty string as published, restored with `ISNULL(…, N'')`; derived columns nullable, restored with `NULLIF(…, N'')`. Digest renders the two differently. AHAH's generator is changed, not copied. Tests added for `ADDENDUM_TEXT` and an empty `OSG_REFERENCE_NUMBER`. |
| 3 | Bounded cells do not bound the concatenated row | yes | The `nvarchar(max)` conversion of each chunk's first operand is kept, and the SQL plan now says why. Test added: a row of in-width cells over 8,000 characters together, whose last cell changes the loaded digest. |
| 4 | Text-UPRN matching rule survived the UPRN check | yes, in the facts list and in section 7 | Both passages rewritten: the bigint `uprn_osg` is the only column a join compares; the published text is provenance. Test added: a cohort UPRN `000035000001` matches in the join itself. |
| 5 | Dated join has no tie policy and does not say what it selects | yes | Section 7 now selects the latest certificate lodged on or before the date, returns its age in days, leaves expiry to the project, and gives a same-day tie `ambiguous_as_of` with no values. Added `no_current_certificate` for the 2,826 UPRNs whose certificates are all historic (1,885,772 distinct UPRNs less 1,882,946 with a `HISTORIC = False` row). Tests added for the tie and the all-historic case. |
| 6 | Main plan wants `nvarchar(max)` and a 5,000-character test; SQL plan caps at 4,000 | yes | Bounded widths are authoritative. Section 4 no longer names `max` columns; the 5,000-character test is replaced by the over-8,000 combined row of finding 3; the 4,001-character rejection stays as the production rule. |

Not changed: the recommended order of work in the review is already the order of the plan's
step 4 (reader, derived columns, checks, tests on a synthetic file) and step 6 (container probe
before the real load).
