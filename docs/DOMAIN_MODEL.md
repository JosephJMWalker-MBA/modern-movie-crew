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
├── Character (Project-Scoped Character Entity)
│   ├── CharacterIdentityVersion (Immutable facial & structural identity)
│   ├── CharacterReferenceAsset (Turnaround sheets, model configs, reference frames)
│   ├── CharacterLook (Wardrobe, hair, makeup owned by Costume Dept)
│   ├── VoiceProfile (Voice actor, ElevenLabs/audio settings owned by Sound Dept)
│   ├── PerformanceProfile (Acting style & body language owned by Performance Dept)
│   ├── CharacterSceneState (Scene-specific injuries, dirt, emotional state owned by Script Supervisor)
│   └── CharacterRightsRecord (Likeness licensing, actor permissions, usage rights owned by Producer/Legal)
├── Resource (Production Documents, References)
├── Act
│   └── Sequence
│       └── Scene
│           └── ProductionTask
│               ├── CharacterTaskLink (Task link to CharacterIdentityVersion + Look + SceneState)
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

### 2. Character Library Entities (Canonical Source of Truth)
- `Character`: Root character record (`project`, `name`, `tagline`, `description`, `created_at`).
- `CharacterIdentityVersion`: Immutable canonical version of physical/structural identity (`character`, `version_number`, `facial_structure_notes`, `body_type`, `canonical_reference_image`, `approved_by`, `status`: `DRAFT`, `APPROVED`, `SUPERSEDED`).
- `CharacterReferenceAsset`: Reference media for identity (`character_identity_version`, `asset_type`: `TURNAROUND`, `MODEL_CONFIG`, `KEYFRAME`, `STORAGE_KEY`).
- `CharacterLook`: Wardrobe, hair, and makeup variation (`character`, `name`, `department`: Costume Dept, `wardrobe_description`, `costume_reference_images`, `status`: `DRAFT`, `APPROVED`).
- `VoiceProfile`: Audio and voice profile (`character`, `name`, `department`: Sound Dept, `voice_actor_name`, `model_settings`, `sample_audio_key`, `status`: `DRAFT`, `APPROVED`).
- `PerformanceProfile`: Acting guidelines & motion style (`character`, `name`, `department`: Performance/Direction Dept, `emotional_range`, `movement_notes`, `mocap_reference_key`, `status`: `DRAFT`, `APPROVED`).
- `CharacterSceneState`: Scene-specific physical condition (`character`, `scene`, `department`: Script Supervisor/Continuity, `injury_notes`, `dirt_blood_level`, `wardrobe_damage`, `emotional_state`, `status`: `APPROVED`).
- `CharacterTaskLink`: Association linking a `ProductionTask` to required character elements (`task`, `character`, `character_identity_version`, `character_look`, `character_scene_state`, `voice_profile`, `performance_profile`).
- `CharacterRightsRecord`: Likeness & actor legal permissions (`character`, `licensor_name`, `actor_membership`, `likeness_authorized`, `voice_authorized`, `model_training_allowed`, `commercial_use_allowed`, `effective_date`, `expiration_date`, `document_key`).

### 3. Claims, Submissions & Immutability
- `TaskClaim`: Tracks contributor reservation (`task`, `membership`, `claimed_at`, `expires_at`, `status`: `ACTIVE`, `SUBMITTED`, `EXPIRED`, `RELEASED`).
- `Submission`: A contributor's attempt at a task (`task`, `contributor`, `status`).
- `SubmissionVersion`: Immutable file revision (`submission`, `version_number`, `storage_key`, `prompt_used`, `external_tool`, `seed`, `contributor_notes`).
- `SubmissionAttestation`: Rights confirmation (`version`, `confirmed_authority`, `external_tool`, `commercial_use_allowed`, `likeness_authorized`, `source_asset_disclosure`, `attested_at`).

### 4. Canonical Selection (Append-Only)
- `CanonicalSelection`: `task`, `submission_version`, `selected_by`, `selected_at`, `supersedes`, `retired_at`, `reason`.

### 5. Two-Layer Review Architecture
- `DepartmentReview`: `version`, `reviewer_assignment`, `decision`: (`APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`, `NOT_APPLICABLE`), `notes`, `created_at`.
- `DirectorReview`: `version`, `reviewer`, `decision`: (`ACCEPT`, `ACCEPT_AS_ALTERNATE`, `REQUEST_REVISION`, `REJECT`), `notes`, `created_at`.

### 6. Legal & Rights Attestation
- `ProjectTermsVersion`: `project`, `version_number`, `terms_text`, `license_policy`, `credit_policy`, `effective_date`.
- `MembershipAgreement`: `membership`, `terms_version`, `accepted_at`.

### 7. Credits & Audit Trail
- `CreditEntry`:
  - `project`, `contributor`
  - Historical snapshots: `credited_name`, `role_name`, `department_name`
  - `basis`: `ROLE`, `RESOURCE`, `RESPONSIBILITY`, `ACCEPTED_WORK`, `FINAL_CUT`
  - Source links: `role_assignment`, `packet_section`, `resource`, `character_identity_version`, `character_look`, `voice_profile`, `department_review`, `submission_version`, `final_cut_usage`
  - `status`: `PENDING`, `ELIGIBLE`, `CONFIRMED`, `WITHHELD`
- `AuditEvent`: Append-only system log (`project`, `actor`, `event_type`, `object_type`, `object_id`, `metadata`, `created_at`).
