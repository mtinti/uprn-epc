# The history rewrite of 14 November 2026

On 14 November 2026 the history of this repository was rewritten, and the repository was created
again on GitHub under the same name. The server name, the database name and the connection options
of one site had been committed in the upload notebook, its generator and the harness of the notebook
probe. Every commit that held them now holds a placeholder in their place: `<SERVER>`, `<DATABASE>`
and `<CONNECTION OPTIONS>`. No other file and no other line changed, and no commit was added,
removed or reordered.

## What this changes for a reader

- **Commit hashes.** Every commit from the one that added the notebook onward has a new hash,
  and so do the tags `v0.1.0` and `v0.2.0`. Documents, reviews, build reports and commit messages
  written before 14 November 2026 cite the old hashes. The table below gives the new one for each.
- **Old notebooks.** The notebook of a commit before version 0.2.1 holds the placeholders and does
  not connect as committed. From version 0.2.1 the notebook is committed with an empty connection
  string, which the analyst fills in at step 1 (`README.md`).
- **The code archives on Zenodo.** The archives of versions 0.1.0 and 0.2.0 were withdrawn the
  same day. Their DOIs, and the DOI that stood for every release, 10.5281/zenodo.23817747, now lead to
  a notice. The code is archived again from version 0.2.1: 10.5281/zenodo.24226617 for every release,
  10.5281/zenodo.24226618 for 0.2.1.
- **Nothing else.** The source pins, the built table, its hashes and its digest are the same.

## Old and new hashes of the commits on `main`

Newest first, up to the last commit before the rewrite. A row whose two hashes are equal was not
touched. Later commits, from version 0.2.1, have only ever had one hash.

| Before | Now | Date | Commit |
| --- | --- | --- | --- |
| `d3d1ea4` | `04bbbda` | 2026-10-31 | Rebuild 2026Q2 with the decision log including the tie rule; CSV bytes and digest unchanged |
| `2cb50c9` | `b43d47c` | 2026-10-31 | Two amendments of one decision read as one policy on the column pages; tie-rule review and response |
| `0d61122` | `a184dea` | 2026-10-31 | Probe records: tie rule run on SQL Server, full table and notebook |
| `7853ae5` | `40ba5c4` | 2026-10-31 | Dated joins break a same-day tie: current certificate first, then the latest register lodgement |
| `fa55af5` | `fa5ecaa` | 2026-10-31 | Pooling mechanism probed again: a pooled session stays in manual-commit mode whatever the new handle declares |
| `7e4c38c` | `4ce9728` | 2026-10-31 | Review: provenance site implementation follow-up, no new findings |
| `7ad5913` | `bc3d9b0` | 2026-10-31 | One definition of the join indexes; every index membership on the column pages; the U+FFFD labels explained |
| `44407ce` | `41d819d` | 2026-10-31 | Rebuild 2026Q2 with the revised decision log; CSV bytes and digest unchanged |
| `9a206e1` | `c6d9bf1` | 2026-10-31 | pyproject: name the packages, so an editable install works beside the data and loader folders |
| `b5bc8a5` | `4f0523a` | 2026-10-31 | README: say three dwellings in ten lack a certificate, not most |
| `76590b8` | `1ba5212` | 2026-10-31 | Column provenance site: descriptions from the note, check catalogue, lineage, generator, Pages workflow |
| `2d0eaf0` | `9d5cdee` | 2026-10-31 | Provenance site plan revised after review: note aliases, decisions in force, check catalogue, zone lists |
| `b6d9cd7` | `d41ff5a` | 2026-10-31 | Plan: a column provenance site on GitHub Pages, after postcode-simd's |
| `b188ce2` | `31a50e6` | 2026-10-30 | README: DOI of version 0.2.0 |
| `72462cd` | `71d5236` | 2026-10-30 | v0.2.0: Version 0.2.0 |
| `f9addf5` | `34842d3` | 2026-10-30 | Load the three address lines: every column goes into the CSV and the table |
| `24be311` | `96d40fc` | 2026-10-30 | README: Zenodo DOI badge and version list for the archived code |
| `e77ff8b` | `a714b45` | 2026-10-30 | v0.1.0: Record the reserved Zenodo DOI of the restricted source archive |
| `a1ca4c9` | `62dc07c` | 2026-10-30 | Name the project uprn-epc, after its join key, like postcode-simd and datazone-ahah |
| `00cd277` | `0545aca` | 2026-10-30 | Probe exit tests use the test interpreter for the runner; round 3 review and response |
| `5e3214b` | `768f983` | 2026-10-30 | Dated joins choose the certificate by inspection date; probe exits nonzero on failure |
| `afe9ed5` | `9467a18` | 2026-10-30 | Notebook review: fix the step 6 selector and the pooled-connection hang; notebook probe |
| `7a94650` | `b04269d` | 2026-10-30 | Upload notebook for loading through pyodbc, with generator and tests |
| `f16bf95` | `f16bf95` | 2026-10-30 | Probe record: fourth run with the cohort key guards; round 3 response |
| `e9c3986` | `e9c3986` | 2026-10-30 | Review round 3: recovery wording, accepted files recoverable across both folders |
| `9579863` | `9579863` | 2026-10-30 | Follow-up review: recoverable promotion with rollback; NULL cohort key rejected |
| `6164a41` | `6164a41` | 2026-10-30 | Rebuild through the staging path: same hashes and digest |
| `2e2b529` | `2e2b529` | 2026-10-30 | Implementation review fixes: joins per cohort row, all-missing nullable column, staged outputs |
| `9b5797f` | `9b5797f` | 2026-10-30 | Container probe passed; rebuild with the final decision log; probe record |
| `6337eeb` | `6337eeb` | 2026-10-30 | Import reads the CSV as UTF-8 (CODEPAGE 65001); datetime2 precision in the structure check |
| `a4d0deb` | `a4d0deb` | 2026-10-30 | Build of release 2026Q2: manifest, build report, data dictionary |
| `00777e7` | `00777e7` | 2026-10-30 | README, tools folder, order of work |
| `4b0f16d` | `4b0f16d` | 2026-10-30 | EPC ingestion: plans, registry, reader, checks, pipeline, SQL generator, tests |
