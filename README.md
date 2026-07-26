# Modern Movie Crew (MMC)

> **Distributed Production Operating System for Generative Filmmaking**
>
> Modern Movie Crew is NOT a simple crowdsourced media generator. It is a distributed production operating system for generative filmmaking. The key engine is **the chain of accountable human decisions between an unfinished need and an accepted film asset**.

---

## Core Principles & Governance Rules

1. **Strict Entity Separation & Hierarchy**:
   - Hierarchy: `Project` → `Act` → `Sequence` → `Scene` → `ProductionTask`.
   - **Character Library**: Canonical, versioned source of truth for each character (`Character`, `CharacterIdentityVersion`, `CharacterReferenceAsset`, `CharacterLook`, `VoiceProfile`, `PerformanceProfile`, `CharacterSceneState`, `CharacterTaskLink`, `CharacterRightsRecord`).
   - Tasks involving a character MUST reference an approved `CharacterIdentityVersion` and, when applicable, the correct `CharacterLook` and `CharacterSceneState`.

2. **Uploading NEVER Auto-Completes a Task**:
   - `ProductionTask` status: `DRAFT`, `READY`, `OPEN`, `SATISFIED`, `CLOSED`, `CANCELLED`.
   - `Submission` status: `DRAFT`, `IN_REVIEW`, `REVISION_REQUESTED`, `ACCEPTED`, `ALTERNATE`, `REJECTED`, `WITHDRAWN`.
   - Revisions create a new immutable `SubmissionVersion`. Revisions belong strictly to the individual `Submission`, never globally to the `ProductionTask`.

3. **Two-Layer Review & Departmental Authority**:
   - **Department Review**: Department roles review work (`APPROVED`, `ISSUE_FOUND`, `REVISION_RECOMMENDED`) and document responsibility.
   - **Director Decision**: Director/authorized lead makes final creative decision (`ACCEPT`, `ACCEPT_AS_ALTERNATE`, `REQUEST_REVISION`, `REJECT`).

4. **Immutable Revisions & Provenance**:
   - Every canonical selection change creates an append-only `CanonicalSelection` record with active/retired tracking (`retired_at__isnull=True`).
   - `AuditEvent` records are append-only.

---

## Quickstart & Local Development

### Prerequisites
- Python 3.13+
- Virtual environment (`venv` or `uv`)

### Installation & Setup

```bash
# Clone repository
git clone https://github.com/JosephJMWalker-MBA/modern-movie-crew.git
cd modern-movie-crew

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Run system check
python manage.py check

# Run complete test suite
python manage.py test

# Start local development server
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `django-insecure-...` | Django secret key for cryptographic signing |
| `DEBUG` | `True` | Debug mode (Set to `False` in production) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of permitted hostnames |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Comma-separated list of trusted CSRF origins |
| `DATABASE_URL` | None (uses SQLite) | PostgreSQL connection URI (e.g., `postgres://user:pass@localhost:5432/mmc_db`) |
| `SECURE_SSL_REDIRECT` | `False` | Enforce HTTPS redirect in production |
| `LOG_LEVEL` | `INFO` | Console logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Production Deployment: Eco Web Hosting / DirectAdmin

The live application is deployed at `modernmoviecrew.online` using DirectAdmin's Python application selector with Passenger.

### Server Configuration

- Python: `3.11.11`
- Application root: `/home/u100953/modernmoviecrew`
- Virtual environment: `/home/u100953/virtualenv/modernmoviecrew/3.11`
- Startup file: `passenger_wsgi.py`
- WSGI entry point: `application`
- Django settings module: `config.settings`

`passenger_wsgi.py` on the server must contain:

```python
import os
import sys

APP_ROOT = "/home/u100953/modernmoviecrew"

if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application
```

This file is tracked in Git and should remain identical between GitHub and the server.

### Production Environment Values

Configure these exact variable names in DirectAdmin's Python application settings:

```text
DEBUG=False
ALLOWED_HOSTS=modernmoviecrew.online,www.modernmoviecrew.online
CSRF_TRUSTED_ORIGINS=https://modernmoviecrew.online,https://www.modernmoviecrew.online
SECRET_KEY=<strong generated secret>
```

Generate a production secret locally with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Do not commit the generated secret. Store it only in the hosting environment.

### Current Database Decision

The production deployment currently uses SQLite because the existing `DATABASE_URL` parser configures PostgreSQL unconditionally. DirectAdmin's MariaDB credentials (`DB_NAME`, `DB_USER`, and related values) are not read by the current settings module.

Until MariaDB support is implemented in code:

- Leave `DATABASE_URL` unset in DirectAdmin.
- Back up the production SQLite database regularly.
- Do not set a MariaDB connection string that the current PostgreSQL-only parser will misinterpret.

### Deploy and Verify

```bash
source /home/u100953/virtualenv/modernmoviecrew/3.11/bin/activate
cd /home/u100953/modernmoviecrew
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

A correct production check reports:

```text
System check identified no issues (0 silenced).
```

Restart the Python application in DirectAdmin after changing code or environment variables.

### TLS / ACME

DirectAdmin ACME is enabled with Let's Encrypt. The certificate request may remain pending while DNS changes propagate. The application already serves over HTTPS, but the DirectAdmin certificate list should eventually show an issued, automatically renewable certificate for the root domain and intended hostnames.

---

## Production Readiness & Security Controls

- **Health Check Endpoint**: `GET /health/` returns `{"status": "healthy", "database": "connected"}`.
- **CSRF & Security Headers**: HSTS, X-Frame-Options (`DENY`), Content-Type-Options (`nosniff`), XSS protection, and secure cookies enabled when `DEBUG=False`.
- **Upload Hardening**: MIME validation, filename sanitization, collision-safe storage names, and CSV formula injection protection.
- **Public Provenance Isolation**: Public views consume published `ProjectProvenanceSnapshot` manifests. Raw internal audit trails, private reviews, rights attestations, tokens, and storage paths are never exposed.

---

## Backup & Restore Procedures

### Database Backup (PostgreSQL)
```bash
pg_dump -U <user> -h <host> -d <database_name> -F c -b -v -f mmc_backup_$(date +%Y%m%d).dump
```

### Database Restore (PostgreSQL)
```bash
pg_restore -U <user> -h <host> -d <database_name> -v mmc_backup_YYYYMMDD.dump
```

---

## Roles & Permissions Matrix

| Authority | Director | Department Head | Contributor | Guest |
|---|:---:|:---:|:---:|:---:|
| Assign / Open Tasks | ✅ | ❌ | ❌ | ❌ |
| Approve Packet Sections | ✅ | ✅ | ❌ | ❌ |
| Approve Character Identity | ✅ | ✅ | ❌ | ❌ |
| Submit Asset Version | ✅ | ✅ | ✅ | ❌ |
| Issue Department Review | ✅ | ✅ | ❌ | ❌ |
| Issue Director Revision | ✅ | ❌ | ❌ | ❌ |
| Accept Canonical Asset | ✅ | ❌ | ❌ | ❌ |
| Publish Provenance Snapshot | ✅ | ❌ | ❌ | ❌ |

---

## Release Checklist

- [x] All database migrations applied (`python manage.py migrate`).
- [x] Django system deployment check passed (`python manage.py check --deploy`).
- [x] Complete automated test suite passed (`python manage.py test`).
- [x] Environment variables configured for production (`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`).
- [x] Static files collected (`python manage.py collectstatic`).
- [x] Health check verified (`/health/`).
- [ ] DirectAdmin-managed Let's Encrypt certificate visible and renewing automatically.
- [ ] Production database migrated from SQLite to a supported server database before broader concurrency.
