# Modern Movie Crew — Domain Model Specification

## Conceptual Hierarchy

```
Project
├── ProjectTermsVersion
├── Department
├── Membership
│   └── MembershipAgreement
├── ProductionRole
├── RoleAssignment
├── Resource (Production Documents, References)
├── Act
│   └── Sequence
│       └── Scene
│           └── ProductionTask
│               ├── PacketSection (Story, Performance, Wardrobe, Set, Camera, Continuity, Generation, Prompt)
│               ├── TaskResource (Approved Reference Attachments)
│               ├── TaskClaim (Contributor reservation, status: ACTIVE, SUBMITTED, EXPIRED, RELEASED)
│               ├── Submission (status: DRAFT, IN_REVIEW, REVISION_REQUESTED, ACCEPTED, ALTERNATE, REJECTED, WITHDRAWN)
│               │   └── SubmissionVersion (Uploaded File, Prompt, Seed, Tools, SubmissionAttestation)
│               │       ├── DepartmentReview (Advisory review by department role)
│               │       └── DirectorReview (Final decision by Director)
│               └── CanonicalSelection (Append-only record of canonical asset history)
├── CreditEntry (Historical credit snapshot pointing to RESPONSIBILITY/WORK source)
└── AuditEvent (Append-only log)
```

## Detailed Entity Models

### 1. Structural Hierarchy
- `Project`: Root film record (`name`, `slug`, `synopsis`, `status`).
- `Act`: Major story division (`act_number`, `title`).
- `Sequence`: Story sequence (`sequence_number`, `title`, `sequence_rules`).
- `Scene`: Scene record (`scene_number`, `title`, `description`).
- `ProductionTask`: Unit of work (`code`, `title`, `task_type`, `status`: `DRAFT`, `READY`, `OPEN`, `SATISFIED`, `CLOSED`, `CANCELLED`, `claim_mode`: `SINGLE` | `OPEN_CALL`).

### 2. Claims, Submissions & Immutability
- `TaskClaim`: Tracks contributor reservation (`task`, `membership`, `claimed_at`, `expires_at`, `status`: `ACTIVE`, `SUBMITTED`, `EXPIRED`, `RELEASED`).
- `Submission`: A contributor's attempt at a task (`task`, `contributor`, `status`).
- `SubmissionVersion`: Immutable file revision (`submission`, `version_number`, `storage_key`, `prompt_used`, `external_tool`, `seed`, `contributor_notes`).
- `SubmissionAttestation`: Rights confirmation (`version`, `confirmed_authority`, `external_tool`, `commercial_use_allowed`, `likeness_authorized`, `source_asset_disclosure`, `attested_at`).

### 3. Canonical Selection (Append-Only)
- `CanonicalSelection`:
  - `task` (FK to `ProductionTask`)
  - `submission_version` (FK to `SubmissionVersion`)
  - `selected_by` (FK to `Membership`)
  - `selected_at` (DateTimeField)
  - `supersedes` (Nullable FK to previous `CanonicalSelection`)
  - `retired_at` (Nullable DateTimeField)
  - `reason` (TextField)

### 4. Two-Layer Review Architecture
- `DepartmentReview`:
  - `version` (FK to `SubmissionVersion`)
  - `reviewer_assignment` (FK to `RoleAssignment`)
  - `decision`: `APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`, `NOT_APPLICABLE`
  - `notes` (TextField)
  - `created_at` (DateTimeField)
- `DirectorReview`:
  - `version` (FK to `SubmissionVersion`)
  - `reviewer` (FK to `Membership`)
  - `decision`: `ACCEPT`, `ACCEPT_AS_ALTERNATE`, `REQUEST_REVISION`, `REJECT`
  - `notes` (TextField)
  - `created_at` (DateTimeField)

### 5. Legal & Rights Attestation
- `ProjectTermsVersion`: `project`, `version_number`, `terms_text`, `license_policy`, `credit_policy`, `effective_date`.
- `MembershipAgreement`: `membership`, `terms_version`, `accepted_at`.

### 6. Credits & Audit Trail
- `CreditEntry`:
  - `project`, `contributor`
  - Historical snapshots: `credited_name`, `role_name`, `department_name`
  - `basis`: `ROLE`, `RESOURCE`, `ACCEPTED_WORK`, `FINAL_CUT`, `RESPONSIBILITY`
  - Source links: `role_assignment`, `packet_section`, `resource`, `department_review`, `submission_version`, `final_cut_usage`
  - `status`: `PENDING`, `ELIGIBLE`, `CONFIRMED`, `WITHHELD`
- `AuditEvent`: Append-only system log (`project`, `actor`, `event_type`, `object_type`, `object_id`, `metadata`, `created_at`).
