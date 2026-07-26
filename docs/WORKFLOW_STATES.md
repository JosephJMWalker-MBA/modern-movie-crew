# Modern Movie Crew — Workflow & State Transition Rules

## Task & Character Lifecycle State Machines

### Character Identity & Facet Approval Flows
1. **Character Identity Version**:
   - `DRAFT`: Character design sheet being created by Art Dept.
   - `APPROVED`: Approved by Art Department Head & Director. Tasks referencing this character can now be created.
   - `SUPERSEDED`: Replaced by a newer `CharacterIdentityVersion`.
2. **Character Facets (`CharacterLook`, `VoiceProfile`, `PerformanceProfile`)**:
   - `DRAFT` → `APPROVED` by their respective department head (Costume, Sound, Performance).
3. **Character Scene State**:
   - Authored by Script Supervisor / Continuity for specific scenes. Must be attached via `CharacterTaskLink` to any task involving that character in that scene.

### Task Readiness Requirement with Characters
A `ProductionTask` involving a character CANNOT transition to `READY` or `OPEN` unless:
1. All required `PacketSection`s are `APPROVED`.
2. Linked `CharacterTaskLink` references an `APPROVED` `CharacterIdentityVersion`.
3. If applicable, linked `CharacterLook` and `CharacterSceneState` are `APPROVED`.

### Task Status Flow
```
[DRAFT] -> (Packet & Character Links Approved) -> [READY] / [OPEN]
                                                       |
                                          (Task SATISFIED upon acceptance)
```
- `DRAFT`: Task packet sections and character links being compiled.
- `READY`: Packet and character links approved, ready to open claims/calls.
- `OPEN`: Accepting claims and submissions.
- `SATISFIED`: Primary canonical asset accepted.
- `CLOSED`: Task complete and locked.
- `CANCELLED`: Task withdrawn.

### Submission & Review Workflow
1. **Department Review Layer**:
   - Costume Dept reviews `SubmissionVersion` against `CharacterLook` & `CharacterSceneState`.
   - Sound Dept reviews against `VoiceProfile`.
   - Script Supervisor reviews against `CharacterSceneState`.
   - Department reviews issue: `APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`, `NOT_APPLICABLE`.
2. **Director Decision Layer**:
   - Director evaluates submission and department feedback.
   - Posts `DirectorReview`: `ACCEPT`, `ACCEPT_AS_ALTERNATE`, `REQUEST_REVISION`, `REJECT`.
   - `ACCEPT` promotes version to canonical asset, appends `CanonicalSelection`, and generates atomic `CreditEntry` records for submitter and department contributors.
