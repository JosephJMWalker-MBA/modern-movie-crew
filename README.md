# Modern Movie Crew (MMC)

> **A distributed production operating system for generative filmmaking.**

Modern Movie Crew converts scripts into governed, assignable production graphs. Contributors pool creative labor, generation credits, AI model access, performance, set design, sound, and editorial judgment to produce canonically governed motion pictures.

---

## 🎬 Governing Principle
*"Many members performing distinct functions, yet contributing to one body."* (1 Corinthians 12)

Modern Movie Crew is model-agnostic and workflow-first. Creative generations happen externally using whatever accounts and models contributors already own (Sora, Runway, Veo, Kling, Suno, ElevenLabs). MMC provides the relational governance, packet specs, version control, review rooms, and credit ledger that turn isolated clips into a cohesive film.

---

## 🛠️ Stack & Architecture
- **Framework**: Python 3.13 / Django 5.2 LTS
- **Database**: PostgreSQL (SQLite for local development)
- **Frontend**: Django Templates + HTMX 2.x + Tailwind CSS
- **Storage**: Direct presigned S3 object uploads

---

## 📚 Core Specifications
- [AGENTS.md](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/AGENTS.md) — Operational guidelines for AI coding agents.
- [Product Constitution](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/PRODUCT_CONSTITUTION.md) — Product vision, pillars, and governance principles.
- [Domain Model](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/DOMAIN_MODEL.md) — Relational schema and entity rules.
- [Workflow & State Machine](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/WORKFLOW_STATES.md) — Task, packet, and submission states.
- [Roles & Permissions Matrix](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/ROLES_AND_PERMISSIONS.md) — Permission capability flags.
- [Credit Ledger System](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/CREDIT_SYSTEM.md) — Provenance tracking & credit rules.
- [Milestones & Roadmap](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/MILESTONES.md) — Implementation roadmap.
- [Acceptance Tests](file:///Users/josephjmwalker-mba/Documents/GitHub/Modern%20Movie%20Crew/docs/ACCEPTANCE_TESTS.md) — Automated verification criteria.

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
