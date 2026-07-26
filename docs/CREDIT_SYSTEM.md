# Modern Movie Crew — Credit Ledger Specification

## Structured Contribution & Decision Tracking

Traditional credits are static text lists compiled manually at the end of post-production.
In Modern Movie Crew, credits are **live, structured data recorded atomically** upon verified production actions—capturing both who generated the asset and who made the key creative decisions that enabled it.

## Credit Entry Bases

1. `ROLE`: Credit for holding an active production role throughout a project phase.
2. `RESOURCE`: Credit for providing an approved foundational asset (e.g. character sheet, color script, voice dataset).
3. `RESPONSIBILITY`: Credit earned for non-generation creative labor, including packet section design, prompt wording approval, or department review evaluations.
4. `ACCEPTED_WORK`: Credit earned when a `SubmissionVersion` is accepted as canonical or alternate take.
5. `FINAL_CUT`: Verified credit for assets included in the locked final cut.

## Source Object Links

Every `CreditEntry` explicitly references its underlying source record:
- `role_assignment` (FK to `RoleAssignment`)
- `packet_section` (FK to `PacketSection`)
- `resource` (FK to `Resource`)
- `department_review` (FK to `DepartmentReview`)
- `submission_version` (FK to `SubmissionVersion`)
- `final_cut_usage` (FK to `FinalCutUsage`)

## Immutable Historical Snapshots

When a `CreditEntry` is created, the system snapshots:
- `credited_name` (e.g., "Imani Vance")
- `role_name` (e.g., "Costume Designer")
- `department_name` (e.g., "Costume Department")

Subsequent user profile edits or role renamings do NOT alter past credit ledger records.
