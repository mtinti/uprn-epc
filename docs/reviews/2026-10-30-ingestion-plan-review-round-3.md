# Ingestion plan review, round 3 — 2026-10-30

Scope: latest edits to EPC_Plan.md and EPC_SQL_Plan.md, and the follow-up review response.

Verdict: the previous P2 finding is substantively resolved, and both join clarifications are addressed. No new blocking finding in this focused review. One stale summary phrase remains.

## Verified resolutions

- Both plans now defer derived-column nullability to the schema, restrict NULL to documented missing cases, and retain build failure for malformed required values. Tests cover malformed dates, non-integer floor area, empty OSG references and generated SQL nullability.
- Dated ties are explicitly restricted to the latest eligible day. The test now returns matched once a unique later certificate becomes eligible.
- The postcode fallback now selects the latest eligible certificate per dwelling, uses uprn_sepcr to include dwellings without Gazetteer UPRNs, and applies the same tie rule.

## [P3] Remove the stale numeric NULL rule from the summary table

Location: EPC_Plan.md:172.

The row for current_energy_efficiency_int, total_floor_area_int and other typed copies still says “NULL where empty.” These required numeric copies are explicitly NOT NULL in the SQL plan and the revised main-plan section 4.

Replace that phrase with “nullability and missing-value handling follow EPC_SQL_Plan.md; invalid or missing required values stop the build.” The detailed contract already resolves the behavior; this is a remaining summary inconsistency, not a reason to reopen the design.

## Validation limits

This was a focused document review against the previous finding and clarifications, not a fresh full audit. No ingestion or SQL execution was tested. Implementation should still be validated by the planned synthetic round trip and container probe. Earlier reviews and responses are preserved; no plans were edited.

## Response, 30 October 2026

The P3 holds. The summary row in `EPC_Plan.md` section 3 now defers nullability to
`EPC_SQL_Plan.md` and says a required value that is missing or does not parse stops the build.
No other change. Implementation starts from here.
