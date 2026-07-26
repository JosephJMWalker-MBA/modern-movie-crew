# Modern Movie Crew — Development Roadmap & Milestones

## Milestone 1: The Core Vertical Slice (P1)
**Goal:** Build and verify the end-to-end governance lifecycle in code.

1. **Authentication & Projects Foundation**:
   - Custom User model
   - Project creation and slug generation
   - Department and ProductionRole setup
   - Crew Membership and RoleAssignment with permissions matrix
2. **Production Organization**:
   - Scenes and ProductionTasks
   - PacketSection creation, assignment, and approval workflow
   - Resource attachments
3. **Creative Review & Provenance Loop**:
   - Contributor task claiming
   - Submission and immutable SubmissionVersion (V1) creation
   - Reviewer decision posting (ACCEPT, ALTERNATE, REVISION, REJECT)
   - Contributor V2 upload on revision request
   - Version acceptance -> CanonicalAsset setting
4. **Credit Ledger & Audit Trail**:
   - Atomic credit creation upon version acceptance
   - Append-only audit logging for every critical transition
   - Verification test suite proving all domain constraints hold

## Milestone 2: UI & Production Board (P2)
- HTMX dynamic production board (Act -> Sequence -> Scene -> Task cards)
- Review room UI with side-by-side version comparison
- Credit ledger dashboard and crew roster views
- Public project progress page & Spare-Gen queue

## Milestone 3: Advanced Features & Export (P3)
- Direct S3 presigned URL client-side upload handler
- Exportable credit rolls and EDL / NLE timeline packages
- Revenue participation and tokenized credit exchanges
