# Response to the tie-rule update review, 31 October 2026

Review: `2026-10-31-tie-rule-update-review.md`. One P2, confirmed and fixed; the build-provenance
follow-up acted on with a rebuild.

## P2: two amendments of one decision read as one policy

Confirmed on the generated `columns/uprn_osg.md`: `join-by-inspection-date`'s `keeps` restated the
blanket tie rule, and the page printed it under "What still stands" beside the new tie decision.

Fixes:

- `decisions.yaml`: `join-by-inspection-date`'s `keeps` now says the tie rule stood unchanged at
  that date and was revised on 31 October 2026 by `tie-prefers-current-then-latest-lodged`. The
  decision text itself is untouched; `keeps` is the project's annotation.
- `provenance_site.py`: when two in-force decisions amend the same earlier one, the earlier
  amendment's sentence reads "What still stood then" and ends "Revised again by `<later>`, which
  governs where the two differ"; only the latest amendment of a target says "What still stands".
- `lineage.py`: `lodgement_date_parsed` cites the tie decision, as the other dated-join columns do.
- Test `test_the_dated_join_pages_state_one_tie_policy`: on the pages of `uprn_osg`,
  `lodgement_date_parsed`, `inspection_date_parsed` and `historic_flag`, the tie decision is in
  force, every "What still stands" sentence belongs to the latest amendment, and every "What still
  stood then" sentence names the later decision.

## Build provenance

Confirmed: the manifest's `decisions_sha256` was the hash before the tie decision was added. The
release is being rebuilt with the final decision log so that the Parquet metadata, the manifest
and the policy are one record; the CSV bytes and digest do not change, as with the previous
rebuild of this kind. The manifest, notebook and dictionary follow to OneDrive.

## Not covered

The SQL Server probe's cohort has no tie, so the tie branches are proven in DuckDB only; a
cohort row with a same-day pair could be added to `loader/sqlserver_probe.sh` by choosing one
of the 49,705 UPRNs at runtime. Not done in this round. My findings are closed.
