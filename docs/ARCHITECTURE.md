# Modern Movie Crew — Architecture Specification

## Technology Stack

- **Backend / Monolith**: Python 3.13 / Django 5.2 LTS
- **Database**: PostgreSQL (SQLite for local development/testing)
- **Frontend Layer**: Django Templates + HTMX 2.x + Tailwind CSS
- **Storage Strategy**:
  - **Milestone 1**: Django storage abstraction with local filesystem storage, upload size/type validation, file metadata records.
  - **Milestone 2**: Presigned S3/R2 direct uploads, signed download URLs, private bucket policies.
- **Service Layer Pattern**: All domain logic and state transitions execute inside `@transaction.atomic` service functions enforcing 5-point scope checks.

## Project Structure

```
modern_movie_crew/
├── manage.py
├── config/                  # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/            # Custom User model & Auth
│   ├── core/                # Audit, Base models, Utilities
│   ├── projects/            # Projects, Terms, Departments, Roles, Memberships
│   ├── production/          # Acts, Sequences, Scenes, Tasks, PacketSections, Resources, TaskClaims
│   ├── submissions/         # Submissions, Versions, Attestations, Dept/Director Reviews, CanonicalSelections
│   └── credits/             # Credit ledger & Export engine
├── services/                # Pure business logic services (atomic operations)
└── templates/               # Django HTML templates + HTMX components
```
