# Response to the follow-up review of 30 October 2026

Review: `2026-10-30-ingestion-plan-follow-up-review.md`. The one remaining finding and both
clarifications hold. Both plans were revised the same day.

| Item | Holds | Change |
| --- | --- | --- |
| P2: blanket "derived is nullable, NULL on parse failure" contradicts the NOT NULL declarations and the fail-fast rule | yes | Both plans now say: a derived column has the nullability declared in the schema; nullable ones (`rrn`, `uprn_osg`, `pc_norm`, the two data zone codes) are NULL only in their documented missing case; NOT NULL ones (dates, `historic_flag`, `uprn_sepcr`, ratings, floor area, decimals) stop the build on a value that does not parse. A non-integer cohort UPRN is the linkage status `no_uprn`, not a source failure. Generated SQL copies nullability from the schema. Tests added: malformed date and non-integer floor area stop the build; generated NULL/NOT NULL matches the schema field for field; empty OSG reference keeps empty text and gives `uprn_osg` NULL. |
| Ties counted only at the latest eligible date | yes | Section 7 says so, and the join test now expects `matched` again once a single later certificate is eligible after an older same-day pair. |
| Postcode fallback said "in force" and did not say per dwelling | yes | Rewritten: one row per dwelling in the postcode, each the latest certificate lodged on or before the date with the same tie rule. The dwelling is `uprn_sepcr`, present in every row and one to one with the Gazetteer UPRN where that exists, so dwellings without a Gazetteer UPRN still count once. |
