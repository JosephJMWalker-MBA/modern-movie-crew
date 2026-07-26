# Modern Movie Crew — Domain Model Specification

## Conceptual Hierarchy

```
Project
├── Department
├── Membership
├── ProductionRole
├── RoleAssignment
├── ProductionDocument / Resource
├── Scene
│   └── ProductionTask
│       ├── PacketSection (Story, Performance, Wardrobe, Set, Camera, Continuity, Generation, Prompt)
│       ├── TaskResource (Approved Reference Attachments)
│       ├── Submission
│       │   └── SubmissionVersion (Uploaded File, Prompt, Seed, Tools)
│       │       └── Review (Decision: Accept, Alternate, Revision, Reject)
│       └── CanonicalAsset (Pointer to approved SubmissionVersion)
├── CreditEntry (Historical credit snapshot)
└── AuditEvent (Append-only log)
```

## Relational Entity Breakdown

### 1. Project & Membership Layer
- `Project`: Root record representing a film project. Has status (Development, Production, Post, Complete, Archived), synopsis, slug, owner.
- `Department`: Production departments (Direction, Writing, Art, Costume, Camera, Cast, Sound, Post, Generation).
- `Membership`: User's participation in a project with `credited_name` and `public_handle`.
- `ProductionRole`: Role defined within a department, with explicit permission flags:
  - `can_assign_tasks`
  - `can_approve_department_work`
  - `can_accept_final_assets`
  - `can_manage_credits`
- `RoleAssignment`: Links a `Membership` to a `ProductionRole` with optional department head status (`is_department_head`).

### 2. Scene & Production Task Layer
- `Scene`: Ordered segment of script (`scene_number`, title, description).
- `ProductionTask`: Individual unit of work (shot, audio bed, costume sheet, concept art).
  - Statuses: `DRAFT`, `PREPARING`, `OPEN`, `CLAIMED`, `IN_REVIEW`, `REVISION`, `APPROVED`, `CLOSED`.
  - Claim modes: `SINGLE` (one contributor) vs `OPEN_CALL` (multiple submissions allowed).
- `PacketSection`: Sub-brief for a task (Story, Performance, Wardrobe, Set, Camera, Continuity, Generation instructions, External Prompt).
  - Must be approved by assigned department roles before task is opened for contributor generation.
- `Resource` & `TaskResource`: Project assets (script, character reference, color script) linked to tasks with explicit purposes.

### 3. Submission & Review Layer
- `Submission`: A contributor's claim/attempt at a task.
- `SubmissionVersion`: Immutable version record (V1, V2, V3...) containing file key, prompt used, tool details, seed, notes.
- `Review`: Decision recorded by an authorized reviewer on a specific `SubmissionVersion`:
  - Decisions: `ACCEPT` (makes canonical), `ALTERNATE` (accepted as backup take), `REVISION` (requests new version), `REJECT` (declines submission).
- `CanonicalAsset`: The active approved `SubmissionVersion` associated with a `ProductionTask`.

### 4. Credit & Audit Ledger Layer
- `CreditEntry`: Immutable credit record snapshotting `credited_name`, `role_name`, and `department_name` derived from accepted work, production roles, or approved resources.
- `AuditEvent`: Append-only system audit log capturing all key decisions, state transitions, and file uploads.
