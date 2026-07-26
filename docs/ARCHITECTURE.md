# Modern Movie Crew — Architecture Specification

## Technology Stack

- **Backend / Monolith**: Python 3.13 / Django 5.2 LTS
- **Database**: PostgreSQL (SQLite for local dev/testing)
- **Frontend Layer**: Django Templates + HTMX 2.x + Tailwind CSS (via CDN/CLI)
- **Storage Strategy**: Direct browser-to-object-storage (Amazon S3 / Cloudflare R2) via presigned POST/PUT URLs. Large media files never proxy through Django application servers.
- **Service Layer Pattern**: All state transitions (approval, task claims, role assignments, credit creation) execute inside `@transaction.atomic` service functions, NOT directly in Django view functions or form saves.

## Project Structure

```
modern_movie_crew/
├── manage.py
├── config/                  # Django project settings & URL routing
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/            # Custom User model & Auth
│   ├── core/                # Audit, Base models, Utilities
│   ├── projects/            # Projects, Departments, Roles, Memberships
│   ├── production/          # Scenes, Tasks, PacketSections, Resources
│   ├── submissions/         # Submissions, Versions, Reviews, CanonicalAssets
│   └── credits/             # Credit ledger & Export engine
├── services/                # Pure business logic services (atomic operations)
└── templates/               # Django HTML templates + HTMX components
```
