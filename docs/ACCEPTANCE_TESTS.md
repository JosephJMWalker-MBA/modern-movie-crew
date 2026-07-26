# Modern Movie Crew — Acceptance Test Matrix (Milestone 1)

## Complete Domain Verification Test Suite

### 1. Character Library & Facet Governance
- [ ] `test_character_task_requires_approved_identity_version`: Task involving a character CANNOT transition to `READY` or `OPEN` without referencing an `APPROVED` `CharacterIdentityVersion`.
- [ ] `test_character_facets_owned_by_respective_departments`: Costume Head approves `CharacterLook`; Sound Head approves `VoiceProfile`; Art Head approves `CharacterIdentityVersion`. Other departments cannot cross-approve.
- [ ] `test_character_scene_state_attached_to_task`: Linking a character task attaches the specific `CharacterSceneState` for that scene.

### 2. Task Readiness & Packet Approval
- [ ] `test_task_cannot_open_without_approved_packet_sections`: Task with unapproved required packet sections MUST NOT transition to `READY` or `OPEN`.
- [ ] `test_department_head_approves_packet_section`: Only role assignments with `can_approve_department_work == True` can approve a packet section.
- [ ] `test_department_head_cannot_approve_other_department_section`: Costume Head cannot approve an Art Department packet section.

### 3. Permissions & Scope Boundaries
- [ ] `test_cross_project_role_cannot_approve`: User holding approval role in Project A CANNOT approve tasks, packets, or characters in Project B.
- [ ] `test_only_authorized_role_can_accept_asset`: User without `can_accept_final_assets` in target project attempting to accept raises `PermissionDenied`.

### 4. Claims & Open Calls
- [ ] `test_task_claim_and_v1_submission`: Contributor claims open task and submits `SubmissionVersion` V1.
- [ ] `test_claim_expires_without_deleting_history`: Expired claim transitions status to `EXPIRED` without deleting claim record; task returns to `OPEN`.
- [ ] `test_open_call_accepts_multiple_active_submissions`: Open call task allows multiple contributors to submit active submissions simultaneously.
- [ ] `test_revision_changes_submission_not_entire_open_call_task`: Requesting revision on Submission A changes Submission A status to `REVISION_REQUESTED`, leaving task `OPEN` for other submissions.

### 5. Revisions & Immutability
- [ ] `test_submission_versions_are_immutable`: Uploading V2 creates a new `SubmissionVersion` without modifying V1 metadata or file path.
- [ ] `test_accepted_version_cannot_be_edited_or_deleted`: An accepted `SubmissionVersion` rejects edit or delete attempts.
- [ ] `test_audit_event_cannot_be_updated_or_deleted`: Calling `save()` on an existing `AuditEvent` or attempting deletion raises `RuntimeError`.

### 6. Canonical Selection History
- [ ] `test_accept_version_promotes_canonical_selection`: Accepting V2 appends a `CanonicalSelection` pointing to V2.
- [ ] `test_alternate_does_not_replace_canonical`: Accepting Submission B as alternate records decision without replacing `CanonicalSelection`.
- [ ] `test_canonical_replacement_preserves_selection_history`: Replacing active canonical asset appends a new `CanonicalSelection` and sets `retired_at` on previous selection.
- [ ] `test_concurrent_accepts_do_not_create_two_active_canonicals`: Transaction locks prevent race conditions resulting in multiple unretired canonical selections.

### 7. Two-Layer Review & Credit Provenance
- [ ] `test_department_review_advises_and_records_responsibility`: Department review creates `DepartmentReview` and records a `RESPONSIBILITY` credit entry.
- [ ] `test_packet_section_work_creates_traceable_credit_source`: Packet section approval records credit linking directly to `PacketSection`.
- [ ] `test_character_stewardship_creates_traceable_credit`: Approving a `CharacterIdentityVersion` or `CharacterLook` records a credit linking directly to the character entity.
- [ ] `test_accept_creates_atomic_credit_and_audit`: Director acceptance atomically creates an eligible `CreditEntry` and `AuditEvent`.
- [ ] `test_failed_accept_rolls_back_credit_and_audit`: Exception during asset acceptance rolls back credit and audit entries cleanly.
- [ ] `test_duplicate_accept_does_not_duplicate_credit`: Re-submitting acceptance on already accepted version does not generate duplicate credits.
- [ ] `test_credit_snapshot_survives_profile_name_change`: Changing `Membership.credited_name` does NOT alter past `CreditEntry` snapshot fields.

### 8. Rights Attestations & Requirements
- [ ] `test_submission_requires_current_project_terms_acceptance`: Submitting a version requires member to have accepted current `ProjectTermsVersion`.
- [ ] `test_cannot_accept_rejected_submission`: Attempting to accept a rejected submission raises `ValidationError`.
- [ ] `test_final_cut_credit_requires_asset_usage_record`: `FINAL_CUT` credit requires valid `FinalCutUsage` record.
