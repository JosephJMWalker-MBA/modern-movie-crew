# Modern Movie Crew — Credit Ledger Specification

## Structured Contribution & Character Stewardship Tracking

Traditional credits are static text lists compiled manually at the end of post-production.
In Modern Movie Crew, credits are **live, structured data recorded atomically** upon verified production actions—capturing who generated the asset, who designed the character identity, who styled the costume look, who managed the voice profile, and who made key creative decisions.

## Credit Entry Bases

1. `ROLE`: Credit for holding an active production role throughout a project phase.
2. `RESOURCE`: Credit for providing an approved foundational asset (e.g. turnaround sheet, color script).
3. `RESPONSIBILITY`: Credit earned for non-generation creative labor, including character identity creation (`CharacterIdentityVersion`), costume look design (`CharacterLook`), voice profile management (`VoiceProfile`), performance direction (`PerformanceProfile`), packet section design, or department review evaluations.
4. `ACCEPTED_WORK`: Credit earned when a `SubmissionVersion` is accepted as canonical or alternate take.
5. `FINAL_CUT`: Verified credit for assets included in the locked final cut.

## Source Object Links

Every `CreditEntry` explicitly references its underlying source record:
- `role_assignment` (FK to `RoleAssignment`)
- `character_identity_version` (FK to `CharacterIdentityVersion`)
- `character_look` (FK to `CharacterLook`)
- `voice_profile` (FK to `VoiceProfile`)
- `performance_profile` (FK to `PerformanceProfile`)
- `packet_section` (FK to `PacketSection`)
- `resource` (FK to `Resource`)
- `department_review` (FK to `DepartmentReview`)
- `submission_version` (FK to `SubmissionVersion`)
- `final_cut_usage` (FK to `FinalCutUsage`)

## Immutable Historical Snapshots

When a `CreditEntry` is created, the system snapshots:
- `credited_name` (e.g., "Imani Vance")
- `role_name` (e.g., "Character Designer" or "Costume Designer")
- `department_name` (e.g., "Art Department" or "Costume Department")

Subsequent user profile edits or role renamings do NOT alter past credit ledger records.
