# Column descriptions from the publication note, review of 31 October 2026

`epc_ingest/column_descriptions.yaml` was drafted by `tools/extract_note_dictionary.py` from the
pinned note (`publication_note.pdf`, SHA256 `c2f33696…`, pages 7 to 17) and reviewed entry by
entry against the PDF's extracted text. AI-assisted: the comparison was done by Claude Fable 5.1
with the author.

What was checked, for each of the 106 note entries: the machine name is the note's (two aliases,
`POST_TOWN` for `ADDRESS3` and the singular `3_YR_ENERGY_SAVING_POTENTIAL`); the description is
the note's text in full, from the end of the name to the next entry, with only the next entry's
group label and the page numbers removed; the group label is the note's, typed from the PDF; the
page is the one the name is printed on; the Scotland-only asterisk is recorded. The 20 element
rating columns (`*_ENERGY_EFF`, `*_ENV_EFF`) have no text of their own in the note and carry
their group's entry with `shared_entry`; nine groups say "As above", 27 columns in all, and
point at `WALL_DESCRIPTION`, which holds the format. `DATA_ZONE_2011` is not in the note and is described by the project.

Kept as printed, noted in the file: "total annual emissions reduction" for the current
emissions; the double O of `HEAT_LOSS_CORRIDOOR`; m² for a corridor length; "of and EPC".

Not covered: the extraction depends on pypdf's text order for this PDF; a new note needs the
labels retyped and the review repeated. My findings are closed.
