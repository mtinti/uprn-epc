# Column provenance site plan follow-up review — 31 October 2026

Scope: revised `docs/plans/Column_Provenance_Site_Plan.md` and the response to the original review. This is a design review, not validation of an implemented site.

## Outcome

All four P2 findings from [the original review](2026-10-31-column-provenance-site-plan-review.md) are addressed in the revised plan. No blocking findings in this focused follow-up.

| Original finding | Resolution |
| --- | --- |
| Publication note does not define every published field | Lines 114–129 specify an explicit alias map, project attribution for DATA_ZONE_2011, separate attribution metadata, page-reference constraints and named regression tests. |
| Current policies conflict with historical decisions | Lines 96–105 distinguish effective policy from history, record amendments and retained provisions, and test address export and inspection-date ranking. |
| Manifest names do not establish applicability, coverage or optional checks | Lines 85–95 introduce a catalogue with column applicability, coverage and enabling conditions, plus synthetic builds with and without archive verification and a negative applicability test. |
| Zone status columns lack lookup dependencies | Lines 73–79 enumerate all four outputs with vintage-specific lookup dependencies and require a membership-change test. |

These findings are closed at the design level. The corresponding implementation and tests still need review when they exist.

## Minor consistency cleanup

At lines 164–165, the generator's exclusive input list omits the newly introduced `check_catalogue.yaml` (and the published-column metadata used by lineage). Update this list to cover the metadata dependencies described in section 2, including indirect reads through lineage. This is a documentation consistency issue rather than a blocker.

## Validation and limits

Read the revised plan and review response against the original findings and previously inspected repository behavior. No implementation changes or test runs were needed for this documentation-only follow-up. This review does not independently resolve the publication-note quotation/licensing question or validate the future Pages deployment.
