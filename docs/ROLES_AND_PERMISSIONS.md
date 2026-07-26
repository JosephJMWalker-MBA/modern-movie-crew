# Modern Movie Crew — Roles & Permissions Matrix

## Role Capability Flags

Every `ProductionRole` defines explicit boolean flags governing action authorization:

| Capability Flag | Description | Default Roles |
|---|---|---|
| `can_assign_tasks` | Assign tasks or manage claims | Director, Production Supervisor |
| `can_approve_department_work` | Approve `PacketSection`s or issue `DepartmentReview`s for their department | Department Heads (e.g. Costume Designer, DP, Art Director) |
| `can_accept_final_assets` | Accept a `SubmissionVersion` as canonical asset or alternate take | Director, Delegated Co-Director |
| `can_manage_credits` | Confirm, withhold, or reorder credit ledger entries | Producer, Credit Coordinator |

## Role Defaults & Boundaries

1. **Director**: Primary creative authority (`can_accept_final_assets = True`, `can_assign_tasks = True`).
2. **Co-Director / Delegated Director**: Optional delegated final approval (`can_accept_final_assets = True`).
3. **Department Head (Costume, Art, DP, Sound, VFX)**: Approves packet sections and submits department reviews (`can_approve_department_work = True`).
4. **Lead Editor / Editor**: Recommends inclusion or marks final-cut use (`can_accept_final_assets = False`).
5. **Script Supervisor / Continuity**: Records continuity findings and packet notes.
6. **Producer / Credit Coordinator**: Manages credit formatting and verification (`can_manage_credits = True`).

## Strict Scope & Boundary Validation Rules

Every service function MUST perform 5-point boundary enforcement before executing mutations:

1. **Project Belonging**: Verify actor's `Membership` belongs to the target `Project`.
2. **Active Assignment**: Verify actor's `RoleAssignment` is currently active (`ends_at` is NULL or in future).
3. **Role Project Match**: Verify the `ProductionRole` belongs to the same `Project`.
4. **Department Matching**: Department packet approvals and department reviews MUST match the section/task's assigned `Department`.
5. **Director Boundary**: Final asset acceptance (`can_accept_final_assets`) MUST belong to the target project's directorship. Cross-project authorization is strictly prohibited and MUST raise `PermissionDenied`.
