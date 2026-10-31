# Response to the column provenance site plan review, 31 October 2026

Review: `2026-10-31-column-provenance-site-plan-review.md`. Four P2 findings, each confirmed
against the note, the code and the manifest, and each now in the plan
(`docs/plans/Column_Provenance_Site_Plan.md`, revision of the same day).

## 1. Fields the note does not define

Confirmed from the extracted note text: no `DATA_ZONE_2011` entry; `POST_TOWN` for `ADDRESS3`;
`_YR_ENERGY_SAVING_POTENTIAL` singular. The plan's "defines every published field" was wrong;
`docs/EPC_Plan.md` had it right. The plan now has an explicit machine-name-to-note-entry map
with the two aliases, an attribution kind kept apart from the text (`note` or `project`), a page
reference required for `note` and forbidden for `project`, and a project-authored description
for `DATA_ZONE_2011` that says the note omits it. Tests name `DATA_ZONE_2011` and both aliases.

## 2. Decisions in force against history

Confirmed: `address-lines-loaded` revises one point of `recipe-public-data-private`, and
`join-by-inspection-date` changes the ranking date of `join-latest-lodged-with-ties` while its
tie rule stands. A list of ids would show `ADDRESS1` both withheld and loaded. The plan adds
`status`, `amends` and `keeps` to each decision entry, renders the policy in force before the
history, and tests the effective export policy of the address columns and the effective date of
the dated joins. The fields go in with the quoting fix, since both change `decisions_sha256`.

## 3. A check catalogue, not the manifest's names

Confirmed: `core/sources.verify` hashes the archive and the note only with `archive=True`, so the
committed manifest has 21 `source.*` checks and neither of those two; the source read-back
samples `SAMPLE_ROWS = 3` rows per file. The plan replaces "one the build emits (checked
against the manifest's names)" with `epc_ingest/check_catalogue.yaml`: per family, the name
pattern, what it tests, the columns it applies to, its coverage and its enabling condition.
Tests run the synthetic build with and without `--verify-archive` and match both ways; the
manifest is an example, not the authority; a real check attached to the wrong column fails.

## 4. The zone lists as inputs of the status columns

Confirmed in `reader.derive_datazone`: `code` against `unknown_code` is membership in the
vintage's list. The plan enumerates the four outputs from `columns.DATAZONE_COLUMNS`, attaches
the list to each status column and as the validation of each code column, and tests that a
membership change with constant source text flips the status.

## Not covered

This is a plan; nothing is built, so no test exists yet to leave gaps in. The note's licensing
for verbatim quotation is still an open question in the plan. My findings are closed.
