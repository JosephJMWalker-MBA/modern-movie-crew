# Modern Movie Crew (MMC)

> **A distributed production operating system for generative filmmaking.**

Modern Movie Crew converts scripts into governed, assignable production graphs. Contributors pool creative labor, AI tool expertise, performance, set design, sound, and editorial judgment to produce canonically governed motion pictures.

---

## 🎬 Governing Principle
*"Many members performing distinct functions, yet contributing to one body."* (1 Corinthians 12)

Modern Movie Crew is external-tool agnostic and workflow-first. Generative assets are produced externally by contributors using their own accounts and preferred models (Sora, Runway, Veo, Kling, Suno, ElevenLabs). MMC provides the relational governance, packet specs, version control, review rooms, and credit ledger that turn isolated clips into a cohesive film.

---

## 🛠️ Stack & Architecture
- **Framework**: Python 3.13 / Django 5.2 LTS
- **Database**: PostgreSQL (SQLite for local development)
- **Frontend**: Django Templates + HTMX 2.x + Tailwind CSS
- **Storage Strategy**: Local storage abstraction for Milestone 1; presigned S3/R2 direct uploads for Milestone 2.

---

## 📚 Core Specifications
- [AGENTS.md](AGENTS.md) — Mandatory operational constraints for AI coding agents.
- [Product Constitution](docs/PRODUCT_CONSTITUTION.md) — Product vision, pillars, and scope boundaries.
- [Domain Model](docs/DOMAIN_MODEL.md) — Relational schema and entity rules.
- [Workflow & State Machine](docs/WORKFLOW_STATES.md) — Task, claim, submission, and review state transitions.
- [Roles & Permissions Matrix](docs/ROLES_AND_PERMISSIONS.md) — Permissions matrix and 5-point boundary validation.
- [Credit Ledger System](docs/CREDIT_SYSTEM.md) — Provenance tracking & credit rules.
- [Architecture & Tech Stack](docs/ARCHITECTURE.md) — Monolithic Django layout.
- [Milestones & Roadmap](docs/MILESTONES.md) — 5-phase implementation roadmap.
- [Acceptance Tests](docs/ACCEPTANCE_TESTS.md) — Full automated verification matrix.

---

## 🚀 Getting Started (Development)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install django django-htmx pillow

# Run migrations & server
python manage.py migrate
python manage.py runserver
```
