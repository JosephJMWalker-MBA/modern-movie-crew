# Modern Movie Crew — Agent Operating Instructions

> **CRITICAL DOMAIN INVARIANT:**
> Modern Movie Crew is NOT a simple crowdsourced media generator. It is a distributed production operating system for generative filmmaking.
> The key engine is **the chain of accountable human decisions between an unfinished need and an accepted film asset**.

## Non-Negotiable Domain Rules

Every agent working on this codebase MUST enforce the following core principles:

1. **Strict Entity Separation & Hierarchy**:
   - Hierarchy: `Project` → `Act` → `Sequence` → `Scene` → `ProductionTask`.
   - **Character Library**: Project-scoped canonical source of truth (`Character`, `CharacterIdentityVersion`, `CharacterReferenceAsset`, `CharacterLook`, `VoiceProfile`, `PerformanceProfile`, `CharacterSceneState`, `CharacterTaskLink`, `CharacterRightsRecord`).
   - Tasks involving a character MUST reference an approved `CharacterIdentityVersion` and, when applicable, the correct `CharacterLook` and `CharacterSceneState`.
   - `ProductionTask` (What the movie needs)
   - `TaskClaim` (Contributor's reservation with expiration/release)
   - `Submission` (A contributor's attempt)
   - `SubmissionVersion` (An uploaded revision, immutable once uploaded)
   - `CanonicalSelection` (Append-only record of accepted version with active/retired tracking)
   - `CreditEntry` (Structured data record of verified contribution/responsibility)
   - **Uploading NEVER auto-completes a task.**
   - **Task completion requires explicit approval of a specific `SubmissionVersion` by an authorized role.**

2. **Departmental Ownership of Character Facets**:
   - Permanent identity: Art / Character Design.
   - Wardrobe & styling: Costume / Wardrobe Department (`CharacterLook`).
   - Voice & audio profile: Sound Department (`VoiceProfile`).
   - Performance & motion profile: Direction / Performance Department (`PerformanceProfile`).
   - Scene-specific state: Script Supervisor / Continuity (`CharacterSceneState`).
   - Rights & permissions: Producer / Legal (`CharacterRightsRecord`).

3. **Open Calls & Submissions**:
   - `ProductionTask` status: `DRAFT`, `READY`, `OPEN`, `SATISFIED`, `CLOSED`, `CANCELLED`.
   - `Submission` status: `DRAFT`, `IN_REVIEW`, `REVISION_REQUESTED`, `ACCEPTED`, `ALTERNATE`, `REJECTED`, `WITHDRAWN`.
   - Revision belongs strictly to the individual `Submission`, never globally to the task.

4. **Two-Layer Review & Departmental Authority**:
   - **Department Review**: Department roles review work (`APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`, `NOT_APPLICABLE`) and document responsibility.
   - **Director Decision**: Director/authorized lead makes final creative decision (`ACCEPT`, `ACCEPT_AS_ALTERNATE`, `REQUEST_REVISION`, `REJECT`).

5. **Immutable Revisions, History & Provenance**:
   - Revisions ALWAYS create a new `SubmissionVersion`. Never overwrite existing version records or stored files.
   - Every canonical selection change creates a new `CanonicalSelection` record.
   - `AuditEvent` records are append-only.
   - Rights attestations (`ProjectTermsVersion`, `MembershipAgreement`, `SubmissionAttestation`, `CharacterRightsRecord`) must be recorded and verified.

6. **Scoped Permissions & Boundary Checks**:
   - Services MUST verify actor membership belongs to the target project.
   - Department approvals MUST match the section/asset's department.
   - Cross-project or mismatched department actions MUST raise `PermissionDenied`.

## Documentation Index

Before making architectural modifications or adding new features, read the relevant specification:
- [Product Constitution](docs/PRODUCT_CONSTITUTION.md)
- [Domain Model](docs/DOMAIN_MODEL.md)
- [Workflow States](docs/WORKFLOW_STATES.md)
- [Roles & Permissions](docs/ROLES_AND_PERMISSIONS.md)
- [Credit System](docs/CREDIT_SYSTEM.md)
- [Architecture & Tech Stack](docs/ARCHITECTURE.md)
- [Development Milestones](docs/MILESTONES.md)
- [Acceptance Tests](docs/ACCEPTANCE_TESTS.md)
