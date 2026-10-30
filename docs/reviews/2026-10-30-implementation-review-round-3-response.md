# Response to the implementation review, round 3, 30 October 2026

Review: `2026-10-30-implementation-review-round-3.md`. No new defect; two requests, both done.

- **Recovery wording.** The response, the test comment, the docstring of `pipeline.promote`
  and the error message now say that when a rollback fails the accepted files are split
  between `results/` and the `.previous` folder, nothing is deleted, and recovery must keep
  both. The test asserts that every accepted file is present across the two folders rather
  than wholly in one.
- **Probe record.** The container probe was rerun from a fresh container after the guard
  changes, and `docs/sql/SQLSERVER_PROBE_2026-10-30.md` now records the fourth run: import
  340 s, digest 25 s, every step passed, and a cohort with a NULL key and one with a repeated
  key each stopped the T-SQL with the guard's message.

The review's standing limits remain as stated: the Linux probe imports a UTF-16 copy rather
than the Windows UTF-8 path, the DuckDB tests strip the T-SQL guards after asserting them, and
the full build's peak memory is unmeasured.
