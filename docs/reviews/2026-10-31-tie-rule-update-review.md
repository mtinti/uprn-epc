# Tie-rule update review — 31 October 2026

## Scope and outcome

Reviewed tie-rule commit `7853ae5` and probe-record commit `0d61122`: both dated SQL joins, notebook Step 7, decision metadata, lineage, tests, README and recorded SQL Server/notebook probe results.

One P2 finding in the provenance presentation. No query-selection defect found in the reviewed SQL.

## Finding

### [P2] Stop presenting the superseded ambiguity rule as still in force

Location: `epc_ingest/decisions.yaml:69–78`; rendered by `epc_ingest/provenance_site.py` in the column's “Why” section.

The new tie decision and `join-by-inspection-date` both amend `join-latest-lodged-with-ties`, but the latter's `keeps` still says “two or more certificates on the latest eligible day are ambiguous_as_of”. Both amendments remain in force. The renderer prints that old rule under “What still stands”, immediately beside the new tie-breaking decision.

Reproduced by generating the site and reading `columns/uprn_osg.md`: the page simultaneously labels the new decision current and asserts that the blanket ambiguity rule survives. This gives readers conflicting guidance about whether a same-day pair returns a certificate.

Represent the later amendment's effect on the earlier retained provisions, or render an explicit effective tie policy that replaces the stale “still stands” assertion while preserving historical text. Also propagate the effective policy to related dated-join pages: `lodgement_date_parsed` still cites the old amendments without the new tie decision. Add a rendered-page regression assertion that the current policy says only unresolved ties are ambiguous and does not present blanket ambiguity as current.

## SQL and test assessment

Both dated joins consistently rank by:
1. Latest inspection date on or before the cohort date.
2. Current certificate before superseded certificates.
3. Latest `created_at_parsed` within that group.

The postcode route partitions by cohort row and SEPCR dwelling. Counts at each ranking stage support the reported tie reason. Certificate values are joined back only when the final rank has one candidate, so a remaining tie returns no certificate values. Older tied inspection days do not affect a later eligible certificate. The undated join retains its separate existing rule.

Notebook Step 7 uses the same final ranking and returns the candidate count; it is a reduced demonstration and does not return the full query's `epc_tie_rule`.

Validation: **70 tests passed**. Existing fixtures exercise current-status precedence over a newer timestamp, latest-timestamp selection among superseded certificates, unresolved ties, later eligible certificates and both dated routes. Generated the provenance site to reproduce the finding.

The recorded SQL Server probe ran the revised T-SQL, but explicitly used a cohort without ties. Its successful run validates execution, not the tie branches themselves; those branches are covered by the DuckDB fixtures. No live SQL Server or full-data probe was rerun during this review.

## Build-provenance follow-up

The current decision log hashes to `af3cdc3827191f1fe4a1504b557af4b52f174b01c766fbe7de343fb0eac6237e`; the checked-in manifest still records `e7f39c7b6c3505b573dbaa892a70d2e6752778b2e3899c8c378a343048d85121`. Thus that build record predates this policy update. This does not establish any change or corruption in the data: the patch changes selection policy. Before presenting the artifact and new policy as one current build, perform the planned coordinated metadata rebuild or explicitly document the query-policy revision separately from the older data build. Do not merely overwrite the manifest hash.

No implementation files were changed during review.
