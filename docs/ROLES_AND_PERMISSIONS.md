# Modern Movie Crew — Roles & Permissions Matrix

## Role Capability Flags

Every `ProductionRole` defines explicit boolean flags governing action authorization:

| Capability Flag | Description | Default Roles |
|---|---|---|
| `can_assign_tasks` | Assign tasks or manage claims | Director, Production Supervisor |
| `can_approve_department_work` | Approve `PacketSection`s, `CharacterLook`s, `VoiceProfile`s, `PerformanceProfile`s, or issue `DepartmentReview`s for their department | Department Heads (e.g. Costume Designer, DP, Art Director, Sound Designer) |
| `can_accept_final_assets` | Accept a `SubmissionVersion` as canonical asset or alternate take | Director, Delegated Co-Director |
| `can_manage_credits` | Confirm, withhold, or reorder credit ledger entries | Producer, Credit Coordinator |

## Character Library Departmental Authorization Matrix

| Character Entity / Facet | Owning Department / Role | Action Authorized |
|---|---|---|
| `CharacterIdentityVersion` | Art Department Head / Director | Approve canonical character physical identity |
| `CharacterLook` | Costume Department Head | Approve wardrobe, hair, and makeup variation |
| `VoiceProfile` | Sound Department Head | Approve voice actor settings and audio samples |
| `PerformanceProfile` | Performance / Director | Approve acting guidelines and motion style |
| `CharacterSceneState` | Script Supervisor / Continuity | Approve scene-specific injury/dirt/wardrobe state |
| `CharacterRightsRecord` | Producer / Legal | Verify likeness rights, actor permissions, usage legalities |

## Strict Scope & Boundary Validation Rules

Every service function MUST perform 5-point boundary enforcement before executing mutations:

1. **Project Belonging**: Verify actor's `Membership` belongs to the target `Project`.
2. **Active Assignment**: Verify actor's `RoleAssignment` is currently active (`ends_at` is NULL or in future).
3. **Role Project Match**: Verify the `ProductionRole` belongs to the same `Project`.
4. **Department Matching**: Department packet approvals, character facet approvals (`CharacterLook`, `VoiceProfile`), and department reviews MUST match the section/asset's assigned `Department`.
5. **Director Boundary**: Final asset acceptance (`can_accept_final_assets`) MUST belong to the target project's directorship. Cross-project authorization is strictly prohibited and MUST raise `PermissionDenied`.
