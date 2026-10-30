# Follow-up ingestion plan review — 2026-10-30

Scope: revised EPC_Plan.md, EPC_SQL_Plan.md, and 2026-10-30-ingestion-plan-review-response.md, compared with the original six findings.

Verdict: all six original issues have been addressed at the design level. One P2 contract inconsistency remains in the new null-handling wording. Implementation and the planned SQL probe remain unvalidated.

## Remaining finding

### [P2] Preserve per-column nullability and fail-fast parsing

Locations: EPC_SQL_Plan.md:43–48; EPC_Plan.md:215–219; the response document's finding 2.

The added rule says a derived column is nullable and becomes NULL when its source is empty or does not parse. This contradicts the SQL derived-column table, which declares the parsed dates, historic_flag, uprn_sepcr and several numeric copies NOT NULL. It also contradicts the ingestion plan's explicit failure on invalid dates/flags and the SQL plan's failure on numeric parse errors.

An implementation following the new blanket rule could silently accept malformed dates or numbers, or generate a different schema from the declared contract.

Change the wording to: published columns preserve empty strings; derived columns use the nullability and missing-value policy declared for each field. Only documented missing or malformed-code cases produce NULL; unexpected parse failures stop the build. Retain NOT NULL for required derived values and statuses. Distinguish invalid cohort UPRNs (a linkage status) from invalid source values (the ingestion contract).

Acceptance: an empty source OSG reference preserves raw empty text and produces uprn_osg NULL; a malformed required date or numeric value fails; generated SQL nullability matches the schema.

## Original findings

| Finding | Follow-up |
| --- | --- |
| Case-only column collisions | Resolved in plan: kind suffixes, updated indexes and schema duplicate-name check. |
| Published blanks converted to NULL | Preservation rule and round-trip tests added. Remaining nullability wording issue is described above. |
| Row digest truncation | Resolved in plan: MAX promotion retained per concatenation chunk; combined-row and trailing-field mutation tests added. |
| Conflicting UPRN comparison rules | Resolved: integer comparison throughout the operative join instructions and an actual padded-cohort join test. |
| Dated certificate ties | Resolved in principle: ambiguous_as_of and no_current_certificate specified, with tests and explicit latest-lodged semantics. |
| Conflicting text widths | Resolved: bounded production widths and 4,001-character rejection; long combined-row test replaces the incompatible oversized-cell test. |

## Small clarifications

For dated ties, specify that ambiguity is counted only among certificates at the maximum eligible lodgement date. Include a test with two older same-day certificates followed by a unique later certificate: after the later date the result should be matched.

The postcode fallback still says “in force.” Align it with the revised latest-lodged semantics and state that selection occurs per dwelling, including the handling of missing Gazetteer UPRNs, rather than per postcode as a whole.

## Validation limits

This follow-up inspected the revised documents and review response. No ingestion implementation is present, and no SQL Server load or full source reprofiling was run. The previous review and response are preserved; the plans were not edited.
