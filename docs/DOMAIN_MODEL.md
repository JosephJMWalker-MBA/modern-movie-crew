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
├── ScriptDocument (Project Script Master)
│   └── ScriptVersion (Immutable Script Revision)
│       ├── ScriptSegment (Acts, Scenes, Action, Dialogue, Headings)
│       ├── ScriptCharacterSuggestion (AI-assisted discovery candidate)
│       │   └── ScriptCharacterMention (Traceable link to ScriptSegment)
│       └── CoveragePlan (Editorial Shot Planning Layer)
│           ├── CoveragePlanSegmentLink (Traceable link to ScriptSegment range)
│           ├── EditorialWarningWaiver (Director waiver for completeness warnings)
│           └── ShotDefinition (Master, OTS, Close-up, Reaction, Insert, B-roll, Sound)
│               └── ShotTaskLink (Traceable link to ProductionTask)
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
│               ├── TaskScriptLink (Traceable link to ScriptVersion and ScriptSegment range)
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
├── AuditEvent (Append-only log)
└── UserFeedback (In-App Contextual Feedback & Triage Record)
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

### 3. Script Import, Character Discovery & Shot Coverage Planning Workspace
- `ScriptDocument`: Primary script master for a project (`project`, `title`, `description`, `created_by`, `created_at`).
- `ScriptVersion`: Immutable versioned script import (`script_document`, `version_number`, `raw_text`, `parsed_at`, `created_by`, `created_at`).
- `ScriptSegment`: Parsed text segment (`script_version`, `segment_number`, `segment_type`: `SCENE_HEADING`, `ACTION`, `DIALOGUE`, `PARENTHETICAL`, `TRANSITION`, `PARAGRAPH`, `text_content`, `scene`, `character`).
- `ScriptCharacterSuggestion`: Deterministic character candidate derived from script text (`script_version`, `name`, `raw_name`, `status`: `SUGGESTED`, `CONFIRMED`, `MERGED`, `REJECTED`, `confirmed_character`, `occurrence_count`).
- `ScriptCharacterMention`: Traceable link from a suggestion or canonical character to an exact `ScriptSegment` (`suggestion`, `segment`, `character`).
- `CoveragePlan`: Governed shot coverage plan for a script passage (`project`, `script_version`, `title`, `editorial_strategy`, `status`: `DRAFT`, `APPROVED`, `STALE`, `RETIRED`, `created_by`, `approved_by`).
- `CoveragePlanSegmentLink`: Link connecting a `CoveragePlan` to its source `ScriptSegment` range (`coverage_plan`, `start_segment`, `end_segment`, `text_snapshot`).
- `ShotDefinition`: Individual camera shot definition within a coverage plan (`coverage_plan`, `shot_code`, `title`, `shot_category`: `MASTER`, `WIDE`, `MEDIUM`, `CLOSE_UP`, `EXTREME_CLOSE_UP`, `OVER_THE_SHOULDER`, `TWO_SHOT`, `REACTION`, `INSERT`, `CUTAWAY`, `ESTABLISHING`, `TRANSITION`, `B_ROLL`, `PICKUP`, `ALTERNATE_TAKE`, `EFFECTS_PLATE`, `CLEAN_PLATE`, `framing_notes`, `camera_movement`, `duration_target_seconds`, `sequence_order`, `is_required`, `status`, `character`, `created_by`).
- `ShotTaskLink`: Traceable link connecting a `ShotDefinition` to a `ProductionTask` (`shot`, `task`, `created_at`).
- `EditorialWarningWaiver`: Audit record of Director waiving an editorial completeness warning with rationale (`project`, `coverage_plan`, `warning_code`, `reason`, `waived_by`, `created_at`).
- `TaskScriptLink`: Immutable traceability link linking a `ProductionTask` to its source script range (`task`, `script_version`, `start_segment`, `end_segment`, `segment_text_snapshot`, `created_at`).

### 4. Claims, Submissions & Immutability
- `TaskClaim`: Tracks contributor reservation (`task`, `membership`, `claimed_at`, `expires_at`, `status`: `ACTIVE`, `SUBMITTED`, `EXPIRED`, `RELEASED`).
- `Submission`: A contributor's attempt at a task (`task`, `contributor`, `status`).
- `SubmissionVersion`: Immutable file revision (`submission`, `version_number`, `storage_key`, `prompt_used`, `external_tool`, `seed`, `contributor_notes`).
- `SubmissionAttestation`: Rights confirmation (`version`, `confirmed_authority`, `external_tool`, `commercial_use_allowed`, `likeness_authorized`, `source_asset_disclosure`, `attested_at`).

### 5. Canonical Selection (Append-Only)
- `CanonicalSelection`: `task`, `submission_version`, `selected_by`, `selected_at`, `supersedes`, `retired_at`, `reason`.

### 6. Two-Layer Review Architecture
- `DepartmentReview`: `version`, `reviewer_assignment`, `decision`: (`APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`, `NOT_APPLICABLE`), `notes`, `created_at`.
- `DirectorReview`: `version`, `reviewer`, `decision`: (`ACCEPT`, `ACCEPT_AS_ALTERNATE`, `REQUEST_REVISION`, `REJECT`), `notes`, `created_at`.

### 7. Legal & Rights Attestation
- `ProjectTermsVersion`: `project`, `version_number`, `terms_text`, `license_policy`, `credit_policy`, `effective_date`.
- `MembershipAgreement`: `membership`, `terms_version`, `accepted_at`.

### 8. Credits & Audit Trail
- `CreditEntry`:
  - `project`, `contributor`
  - Historical snapshots: `credited_name`, `role_name`, `department_name`
  - `basis`: `ROLE`, `RESOURCE`, `RESPONSIBILITY`, `ACCEPTED_WORK`, `FINAL_CUT`
  - Source links: `role_assignment`, `packet_section`, `resource`, `character_identity_version`, `character_look`, `voice_profile`, `department_review`, `submission_version`, `final_cut_usage`
  - `status`: `PENDING`, `ELIGIBLE`, `CONFIRMED`, `WITHHELD`
- `AuditEvent`: Append-only system log (`project`, `actor`, `event_type`, `object_type`, `object_id`, `metadata`, `created_at`).

### 9. Contextual User Feedback & Development Intake
- `UserFeedback`:
  - `submitted_by`, `project` (nullable)
  - `category`: `BUG`, `MISSING_CAPABILITY`, `WORKFLOW_IMPROVEMENT`, `CONFUSING_INTERFACE`, `PERFORMANCE`, `ACCESSIBILITY`, `FEATURE_REQUEST`, `OTHER`
  - `title`, `what_user_was_doing`, `actual_result`, `ideal_result` (*What would you ideally want to happen here?*)
  - `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
  - `page_url`, `page_name`, `context_type`, `context_identifier`, `context_snapshot` (allowlisted metadata dict)
  - `status`: `NEW`, `TRIAGED`, `PLANNED`, `IN_PROGRESS`, `RESOLVED`, `DECLINED`, `DUPLICATE`
  - `duplicate_of`, `github_issue_number`, `github_issue_url`, `internal_notes`
  - `created_at`, `updated_at`
