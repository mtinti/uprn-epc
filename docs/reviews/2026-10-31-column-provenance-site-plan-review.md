# Column provenance site plan review — 2026-10-31

Scope: docs/plans/Column_Provenance_Site_Plan.md, checked against the current schema, published-column metadata, source registry, reader/check implementation, decision log, manifest, existing EPC plan and the local SIMD Pages implementation proposed for reuse.

Verdict: the metadata-only approach is appropriate, but revise the provenance contract before implementation. Four P2 issues need explicit treatment.

## 1. [P2] Allow an honestly attributed description for fields absent from the note

Plan locations: lines 30–33 and 87–94.

The plan says the note defines every published field and requires each published description to be extracted from it with a hash and page. The existing EPC plan explicitly records that the note lists only 106 fields and omits DATA_ZONE_2011 (docs/EPC_Plan.md:39). It also records the ADDRESS3/POST_TOWN naming difference and the singular/plural difference in the energy-savings field.

Consequently, the proposed mandatory coverage check cannot be satisfied faithfully for all 107 published columns by the stated extraction rule. Copying the 2001 zone definition onto the 2011 field would misattribute an interpretation as a publisher definition.

Add an explicit machine-name-to-note-entry mapping with the known aliases, and allow an entry such as “not defined in this publication note; project-authored description based on the published header and pinned 2011 lookup.” Store attribution kind separately from text; page references should be required only where a matching note entry actually exists. Test DATA_ZONE_2011 and both aliases explicitly, rather than merely checking that text is non-empty.

## 2. [P2] Distinguish current decisions from superseded decisions

Plan locations: lines 51–56 and 78.

The proposed decision relationship is only a list of existing ids. The decision log contains conflicting historical and current policies:

- recipe-public-data-private says the three address lines are withheld; address-lines-loaded revises that point.
- join-latest-lodged-with-ties selects by lodgement date; join-by-inspection-date changes the date used by dated joins and indexes.

An existing-id check cannot establish which decision currently governs a column. Publishing both as undifferentiated reasons can tell a reader that ADDRESS1 is simultaneously included and excluded, or give two different temporal meanings to inspection_date_parsed/lodgement_date_parsed.

Add explicit supersession/amendment metadata and render current policy separately from decision history. Preserve unaffected parts of partially revised decisions: address-lines-loaded does not discard the privacy policy, and the inspection-date change does not discard ambiguity handling.

Acceptance tests should assert the effective export policy for the address columns and the effective date-selection policy for the dated joins, as well as the existence of historical links.

## 3. [P2] Define check applicability and conditional execution, not just manifest-name membership

Plan locations: lines 74–77 and 112–118.

The current 295-check manifest is an execution record, not a complete check catalogue. It contains source hashes for 19 CSVs and the two zone lists but no archive/note hash checks. core/sources.py:65–74 emits those two only when --verify-archive is enabled.

Using this one manifest as the definition of every check the build emits either rejects valid conditional checks or silently omits them. Likewise a family such as table.* or readback.* does not identify which columns it protects or its coverage: RRN uniqueness is specific to rrn, and readback.parquet.sampled_rows_equal_source compares three rows per file, not every raw cell in every row.

Add a structured definition for each check family with applicable columns, parameters, coverage and enabling condition. Validate emitted names against that catalogue in both ordinary and archive-verifying synthetic builds; use the checked-in manifest as an additional compatibility example, not the sole authority. The site can remain definitions-only while stating that archive verification is opt-in and that source-cell read-back is sampled.

A test should fail when a valid check id is attached to an unrelated column, not only when an unknown name appears.

## 4. [P2] Include reference-list dependencies for both data-zone status columns

Plan location: lines 65–69.

The plan explicitly adds pinned lookup inputs for “the two data zone columns,” but the schema has four derived fields for those two source fields: datazone_2001, datazone_2001_status, datazone_2011 and datazone_2011_status.

The reference list directly determines each status: reader.derive_datazone returns code or unknown_code by testing membership in zones (reader.py:31–36). A lineage record derived solely from the status field's schema source would point only to DATA_ZONE or DATA_ZONE_2011 and omit a real dependency.

Explicitly attach the vintage-specific list to each status column, as well as documenting its validation relationship to the code column. Use columns.DATAZONE_COLUMNS to enumerate all four outputs. Test that changing membership with identical source text changes the status and that each status page links to the correct pinned list.

## Confirmed foundations

- Schema contains 130 fields; the current manifest contains 295 checks.
- All published labels are currently distinct, although the machine name should remain the identity used in mappings and URLs.
- The plan correctly identifies the YAML parsing defect: safe_load fails at decisions.yaml line 17 on the unquoted colon.
- The manifest and build report are explicitly exempted from results/* in .gitignore; the concern in finding 3 is incomplete semantic coverage, not their absence from a clean checkout.
- The current export contract and decision log support including all columns in the private CSV/SQL output.
- The local sibling workflow/script exists under /Users/mtinti/git_projects/SIMD and implements the branch previews and Pages-build wait described by the plan.

## Validation and limits

Read the plan and relevant local metadata/code; inspected the current manifest, counted fields/checks, checked publisher-label uniqueness and reproduced the decisions.yaml parse error. No site implementation exists to build or exercise, so no site tests or deployment were run.

The PDF omission/alias finding is supported by the repository's existing source analysis in EPC_Plan.md; this review did not re-extract or visually re-audit the PDF. It does not independently adjudicate the note's licensing. No plan, source data or application code was changed. Earlier reviews are preserved.
