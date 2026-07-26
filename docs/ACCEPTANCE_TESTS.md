# Modern Movie Crew — Acceptance Test Matrix (Milestone 1)

## Automated Domain Verification Tests

### 1. Task Readiness & Packet Approval
- [ ] `test_task_cannot_open_without_approved_packet_sections`: A task with unapproved required packet sections MUST NOT transition to `OPEN`.
- [ ] `test_department_head_approves_packet_section`: Only role assignments with `can_approve_department_work == True` can approve a packet section.

### 2. Task Claim & Submission Revisions
- [ ] `test_task_claim_and_v1_submission`: Contributor claims open task and submits `SubmissionVersion` V1.
- [ ] `test_submission_versions_are_immutable`: Uploading a new revision creates V2 without modifying V1 metadata or storage key.

### 3. Review & Canonical Promotion
- [ ] `test_only_authorized_role_can_accept_asset`: User without `can_accept_final_assets` attempting to accept a submission raises `PermissionDenied`.
- [ ] `test_accept_version_promotes_canonical_asset`: Accepting V2 updates `CanonicalAsset` pointer to V2 and sets task status to `APPROVED`.
- [ ] `test_accept_creates_atomic_credit_and_audit`: Accepting V2 creates an eligible `CreditEntry` and an append-only `AuditEvent`.

### 4. Rejected Submission Rules
- [ ] `test_cannot_accept_rejected_submission`: Attempting to accept a rejected submission raises `ValidationError`.
