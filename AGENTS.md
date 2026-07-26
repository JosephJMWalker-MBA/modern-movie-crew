# Modern Movie Crew — Agent Operating Instructions

> **CRITICAL DOMAIN INVARIANT:**
> Modern Movie Crew is NOT a simple crowdsourced media generator. It is a distributed production operating system for generative filmmaking.
> The key engine is **the chain of accountable human decisions between an unfinished need and an accepted film asset**.

## Non-Negotiable Domain Rules

Every agent working on this codebase MUST enforce the following core principles:

1. **Strict Entity Separation**:
   - `ProductionTask` (What the movie needs)
   - `Submission` (A contributor's attempt)
   - `SubmissionVersion` (An uploaded revision, immutable once uploaded)
   - `CanonicalAsset` (The specific `SubmissionVersion` accepted for production)
   - `CreditEntry` (Structured data record of verified contribution/responsibility)
   - **Uploading NEVER auto-completes a task.**
   - **Task completion requires explicit approval of a specific `SubmissionVersion` by an authorized role.**

2. **Immutable Revisions & Auditability**:
   - Revisions ALWAYS create a new `SubmissionVersion`. Never overwrite existing version records or stored files.
   - `AuditEvent` records are append-only.
   - Reviews reference an exact `SubmissionVersion`.

3. **Role-Based Governance**:
   - Tasks require an approved `ProductionPacket` before generation claims are opened.
   - Department work and packet sections are owned and approved by authorized roles (`can_approve_department_work`).
   - Final assets are accepted only by authorized roles (`can_accept_final_assets`).

4. **Preserve History & Provenance**:
   - Credit entries capture historical snapshot fields (`credited_name`, `role_name`, `department_name`) so profile edits do not alter past project credits.
   - Alternate asset acceptance does NOT overwrite canonical assets.
   - Prompts, parameters, tool metadata, and source reference links must be recorded for every submission version.

## Documentation Index

Before making architectural modifications or adding new features, read the relevant specification:
- [Product Constitution](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/PRODUCT_CONSTITUTION.md)
- [Domain Model](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/DOMAIN_MODEL.md)
- [Workflow States](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/WORKFLOW_STATES.md)
- [Roles & Permissions](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/ROLES_AND_PERMISSIONS.md)
- [Credit System](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/CREDIT_SYSTEM.md)
- [Architecture & Tech Stack](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/ARCHITECTURE.md)
- [Development Milestones](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/MILESTONES.md)
- [Acceptance Tests](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/ACCEPTANCE_TESTS.md)
