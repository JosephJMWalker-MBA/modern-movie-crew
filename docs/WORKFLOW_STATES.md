# Modern Movie Crew — Workflow & State Transition Rules

## Task Lifecycle State Machine

```
[DRAFT] -> (All required PacketSections Approved) -> [OPEN]
                                                       |
                                               (Contributor claims/submits)
                                                       v
                                                 [IN_REVIEW]
                                                /           \
                                (Director accepts)         (Director requests revision)
                                      v                             v
                                 [APPROVED]                   [REVISION]
                            (CanonicalAsset set)              (New SubmissionVersion required)
```

### State Transitions & Rules

1. **Draft to Open (`DRAFT` -> `OPEN`)**:
   - Condition: All required `PacketSection`s associated with the `ProductionTask` must have `status == APPROVED`.
   - Result: Task becomes visible on project production board and available for generation claims.

2. **Open to Claimed/In Review (`OPEN` -> `CLAIMED` / `IN_REVIEW`)**:
   - A contributor claims the task or uploads `SubmissionVersion` V1.
   - Task status transitions to `IN_REVIEW`.

3. **In Review to Revision Requested (`IN_REVIEW` -> `REVISION`)**:
   - Reviewer posts a `Review` with `decision == REVISION`.
   - `Submission` status becomes `REVISION`.
   - Contributor is notified and prompted to upload `SubmissionVersion` V2.
   - Previous versions remain unchanged and immutable.

4. **In Review to Approved (`IN_REVIEW` -> `APPROVED`)**:
   - Reviewer with `can_accept_final_assets == True` posts a `Review` with `decision == ACCEPT`.
   - `Submission` status becomes `ACCEPTED`.
   - `ProductionTask` status becomes `APPROVED`.
   - `CanonicalAsset` is created or updated to point to the approved `SubmissionVersion`.
   - An eligible `CreditEntry` is generated atomically in the credit ledger.
   - An `AuditEvent` is appended.

5. **Alternate Takes (`ACCEPT` as Alternate)**:
   - Reviewer selects `decision == ALTERNATE`.
   - `Submission` status becomes `ALTERNATE`.
   - `ProductionTask` remains `OPEN` or `APPROVED` depending on whether a primary canonical asset exists.
   - Credit entry is recorded for the alternate contribution.
