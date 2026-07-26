# Modern Movie Crew — Credit Ledger Specification

## Structured Contribution Data

Traditional movie credits are static text lists compiled manually at the end of post-production.
In Modern Movie Crew, credits are **live, structured data recorded atomically** upon key milestones.

## Credit Entry Bases

1. `ROLE`: Credit for holding a specific production role throughout the project lifecycle.
2. `RESOURCE`: Credit for providing an approved foundational asset (e.g., character design sheet, color script, voice dataset).
3. `ACCEPTED_WORK`: Credit earned when a `SubmissionVersion` is accepted as canonical or alternate.
4. `FINAL_CUT`: Verified credit for footage/audio included in the locked final cut of the film.

## Credit Entry Structure

Each `CreditEntry` captures:
- `contributor`: Pointer to `Membership`
- `credited_name`: Historical snapshot of name at the time of credit creation
- `department_name`: Snapshot of department name
- `role_name`: Snapshot of role title
- `basis`: `ROLE`, `RESOURCE`, `ACCEPTED_WORK`, or `FINAL_CUT`
- `status`: `PENDING`, `ELIGIBLE`, `CONFIRMED`, `WITHHELD`
- `contribution_summary`: Narrative description of the exact work done
- `appears_in_screen_credits`: Boolean flag for final credit roll inclusion
- `final_order`: Position in department credit list
