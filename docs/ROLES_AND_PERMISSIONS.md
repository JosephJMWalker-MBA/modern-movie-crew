# Modern Movie Crew — Roles & Permissions Matrix

## Role Capability Flags

Every `ProductionRole` in a project defines explicit boolean flags governing action authorization:

| Capability Flag | Description | Default Roles |
|---|---|---|
| `can_assign_tasks` | Assign tasks to crew members or approve task claims | Director, Production Supervisor |
| `can_approve_department_work` | Approve `PacketSection`s owned by their department | Department Heads (e.g. Costume Designer, DP) |
| `can_accept_final_assets` | Accept a `SubmissionVersion` as canonical or alternate | Director, Co-Director, Lead Editor |
| `can_manage_credits` | Confirm, withhold, or reorder credit ledger entries | Producer, Director, Script Supervisor |

## Department Hierarchy Example

- **Direction**: Director, Assistant Director, Script Supervisor
- **Costume**: Costume Designer, Wardrobe Supervisor
- **Art Department**: Production Designer, Concept Artist, Matte Painter
- **Camera & Lighting**: Director of Photography, Lighting Technician
- **Generation & VFX**: Generation Supervisor, Prompt Specialist, Model Operator
- **Sound & Music**: Sound Designer, Composer, Foley Artist, Audio Mixer
- **Post Production**: Lead Editor, Assistant Editor, Colorist
