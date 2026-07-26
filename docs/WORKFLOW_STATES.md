# Modern Movie Crew — Workflow & State Transition Rules

## Task Lifecycle & State Machine

### Task Status Flow
```
[DRAFT] -> (All required PacketSections Approved) -> [READY] / [OPEN]
                                                         |
                                            (Task SATISFIED / CLOSED upon acceptance)
```
- `DRAFT`: Task packet sections being compiled.
- `READY`: Packet sections approved, ready to open claims/calls.
- `OPEN`: Accepting claims and submissions.
- `SATISFIED`: Primary canonical asset accepted (open call may remain OPEN or move to SATISFIED).
- `CLOSED`: Task complete and locked.
- `CANCELLED`: Task withdrawn.

### Claim Status Flow (`TaskClaim`)
- `ACTIVE`: Contributor currently holds reservation on single-contributor task (with expiration timer).
- `SUBMITTED`: Claim fulfilled by a submission.
- `EXPIRED`: Claim timed out without upload; task becomes OPEN again.
- `RELEASED`: Contributor voluntarily gave up claim.

### Submission Status Flow (`Submission`)
```
[DRAFT] -> [IN_REVIEW] -> (Dept Review + Director Review)
                             /                |               \
                (Revision Requested)      (Accepted)      (Rejected)
                         |                    |               |
               [REVISION_REQUESTED]       [ACCEPTED]      [REJECTED]
             (Uploads new version V2)   (Appends CanonicalSelection)
```
- `DRAFT`: Contributor preparing version.
- `IN_REVIEW`: Submitted, undergoing department review & director evaluation.
- `REVISION_REQUESTED`: Director requested revision on this specific submission version.
- `ACCEPTED`: Selected as primary canonical asset.
- `ALTERNATE`: Accepted as an alternate take.
- `REJECTED`: Submission declined.
- `WITHDRAWN`: Contributor withdrew submission.

### Two-Layer Review Execution Rules

1. **Department Review Layer**:
   - Department roles review `SubmissionVersion` for technical and departmental fidelity.
   - Posts `DepartmentReview` with `decision` in (`APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`, `NOT_APPLICABLE`).
   - Advises director and documents departmental responsibility (creating a `CreditEntry` under `RESPONSIBILITY`).

2. **Director Decision Layer**:
   - Authorized Director evaluates submission version and department feedback.
   - Posts `DirectorReview` with `decision`:
     - `ACCEPT`: Promotes version to canonical asset. Appends `CanonicalSelection` record (retiring previous active selection if any). Sets `Submission` status to `ACCEPTED` and `ProductionTask` to `SATISFIED`. Generates atomic `CreditEntry` and `AuditEvent`.
     - `ACCEPT_AS_ALTERNATE`: Sets status to `ALTERNATE`. Records credit.
     - `REQUEST_REVISION`: Sets status to `REVISION_REQUESTED`. Prompts contributor for `SubmissionVersion` V2. Task remains OPEN.
     - `REJECT`: Sets status to `REJECTED`.
