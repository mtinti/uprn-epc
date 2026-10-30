# Ingestion plan review — 2026-10-30

Scope: docs/EPC_Plan.md and docs/EPC_SQL_Plan.md, checked against the local profiles, UPRN check, and the AHAH SQL generator proposed for reuse.

Verdict: revise before implementation. Source pinning, preservation of published values, and explicit linkage statuses are sound choices, but the SQL contract and linkage rules contain blocking inconsistencies.

## Findings

### 1. [P1] Derived names collide with published names under case-insensitive SQL identifiers

Location: EPC_SQL_Plan.md:80–85; EPC_Plan.md section 4.

The table keeps INSPECTION_DATE, LODGEMENT_DATE, CREATED_AT, HISTORIC and numeric published columns, then adds inspection_date, lodgement_date, created_at, historic and numeric copies differing only by case. On a database with case-insensitive identifier collation these are duplicate column names, preventing staging and final table creation. Brackets and per-column data collations do not solve identifier collisions.

Use distinct derived names, such as inspection_date_parsed and historic_flag, consistently in both plans, schemas, digests and queries. Test table creation on the target database collation and reject duplicate case-folded schema names.

Evidence: [Microsoft database identifier rules](https://learn.microsoft.com/en-us/sql/relational-databases/databases/database-identifiers) specify that database collation governs column identifiers.

### 2. [P1] Reusing AHAH's loader loses published empty strings

Location: EPC_SQL_Plan.md:19–20, 33–34, 120–122.

AHAH's ahah_ingest/sql_check.py, _import_sql, explicitly assumes no text column can be blank and restores text with NULLIF([column], N''). EPC contains genuine published empty strings, including every ADDENDUM_TEXT cell and missing RRNs, UPRNs and zones. Copying that loader changes those values to SQL NULL, violating the exact-value contract and potentially breaking digest parity.

Specify separate treatment of raw text and nullable derived values: source blanks remain empty strings; missing derived values become NULL. Define the CSV/staging representation and restoration rules, rather than relying on implicit BULK INSERT handling. Test empty raw text beside derived NULL through source, Parquet, CSV, SQL and digest verification, including ADDENDUM_TEXT and a missing OSG reference.

Evidence: inspected /Users/mtinti/git_projects/AHAH/ahah_ingest/sql_check.py, _import_sql, including its explicit empty-cell assumption.

### 3. [P1] Keep a MAX operand in row-digest concatenation

Location: EPC_SQL_Plan.md:48–51.

The claim that individually bounded columns remove the need for CONVERT to MAX is incorrect for concatenation. A row can exceed the bounded concatenation result even if each cell fits its declared column. Removing the MAX conversion risks hashing a truncated row; casting the already concatenated result afterward does not restore lost content.

AHAH already promotes the first operand of each concatenation chunk to nvarchar(max). Explicitly retain that behavior. Add a valid synthetic row whose combined text exceeds 8,000 characters while each cell stays within its own limit, then mutate a trailing field and require the loaded digest to change.

Evidence: AHAH sql_check.py, _table_sql; [Microsoft CONCAT return-type and truncation rules](https://learn.microsoft.com/en-us/sql/t-sql/functions/concat-transact-sql). CONCAT_WS follows CONCAT conversion behavior. This is a defect in the proposed rationale, not a finding that the current AHAH generator truncates rows.

### 4. [P2] Remove the superseded text-UPRN matching rule

Location: EPC_Plan.md:277–278 and the two-property-numbers fact; compare its Open questions and EPC_SQL_Plan.md:76,139.

The operative join instructions still require comparison of published text and say padded UPRNs must not match. The resolved question, the 30 October UPRN check, and the SQL companion instead require integer comparison. An implementation following section 7 will silently miss valid padded cohort identifiers.

Make bigint comparison authoritative throughout both plans, preserve source text only as provenance, and define missing/invalid cohort identifier handling. Require a padded cohort identifier to match an unpadded EPC identifier in the actual join test, beyond the existing derived-column parsing test.

### 5. [P2] Resolve same-date ambiguity in the dated UPRN join

Location: EPC_Plan.md:260–265.

The dated query chooses the latest lodgement_date but defines ambiguity only for the undated HISTORIC=False route. Two different certificates for one UPRN can share the maximum eligible date. A max-date join then duplicates a cohort row, while TOP(1) with date-only ordering selects arbitrarily. Neither is the promised explicit choice.

Define the tie policy: report an ambiguous-as-of status with no certificate values, or use a documented finer ordering with residual ambiguity handling. Test two certificates on the same eligible day, a cohort before and after that day, and a property with historical certificates but no HISTORIC=False row. State whether the intended output is latest recorded certificate or a certificate valid at the date; the current selection alone does not establish expiry validity.

### 6. [P2] Reconcile incompatible text-width acceptance tests

Location: EPC_Plan.md section 4, section 6 and SQL Server tests; EPC_SQL_Plan.md:48–63,136–137.

The main plan requires MAX free text and successful loading of a 5,000-character cell; the SQL companion caps IMPROVEMENTS at 4,000 and requires a 4,001-character value to fail. Both cannot be the acceptance contract for the same production schema.

Select one authoritative schema policy and update both plans. If bounded widths are retained, distinguish production rejection tests from any generic MAX-capability probe. Keep the long combined-row digest test from finding 3: bounded individual cells do not bound the whole row.

## Validation and limits

Read both plans, docs/uprn_check_2026-10-30.md, local/profile_columns.py, and the relevant AHAH generator implementation. Consulted Microsoft documentation for SQL identifier and concatenation behavior. This was a design review: no ingestion implementation exists here to execute, no full source reprofiling was performed, and no SQL Server load was run. No plan or source data was changed.

Recommended order: settle names and null/empty semantics; preserve the digest MAX conversion; reconcile UPRN and width rules; define dated tie behavior; then run the synthetic end-to-end probe before the full ingestion.
