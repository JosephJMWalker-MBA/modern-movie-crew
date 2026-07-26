# Modern Movie Crew — Revised Development Roadmap & Milestones

## Milestone 0 — Scaffold & Guardrails
- Django project initialization with Python 3.13 / Django 5.2 LTS
- Custom `User` model (`accounts.User`)
- Environment configuration & settings (PostgreSQL / SQLite)
- Linting, formatting, base test suite setup
- Relative documentation links verification
- Storage abstraction layer (local media storage setup)
- Base audit log utilities

## Milestone 1 — One Complete Production Loop (With Minimal UI)
- **Domain Models**: Projects, Memberships, ProjectTermsVersions, MembershipAgreements, Departments, Roles, Acts, Sequences, Scenes, Tasks, PacketSections, Resources, TaskClaims (with expiration), Submissions, Immutable SubmissionVersions, SubmissionAttestations, DepartmentReviews, DirectorReviews, Append-Only CanonicalSelections, CreditEntries.
- **Service Layer**: 5-point permission and boundary check enforcement on all state transitions.
- **Minimal Functional UI**: Plain Django + HTMX views to test and prove the full human workflow end-to-end:
  - Log in → Create project → Add departments & crew → Create act/sequence/scene/task → Complete packet sections → Open task → Claim task → Upload V1 → Department review → Director requests revision → Upload V2 → Director accepts V2 → CanonicalSelection created → Credit recorded.
- **Full Automated Test Suite**: Testing all happy paths and domain edge cases.

## Milestone 2 — Community Production Room
- Invitation links, public/private/unlisted project visibility
- Open-call submissions and crew calls
- Spare-generation task queue
- Direct presigned S3 / R2 uploads & signed download URLs
- Dynamic HTMX Production Board (Act → Sequence → Scene → Task cards)
- Review Room UI & Notifications Inbox
- Public progress page

## Milestone 3 — Post-Production & Credits
- Final-cut asset usage records (`FinalCutUsage`)
- Credit verification by contributors
- Credit ordering and department grouping
- Project-defined credit policies, contribution reports, and external compensation exports
- Rolling-credit generator & NLE timeline exports (EDL/XML/CSV)

## Milestone 4 — Production Scale
- Task and script bulk imports
- Reusable department templates and project cloning
- Media proxy generation and video thumbnails
- Moderation and dispute resolution records
