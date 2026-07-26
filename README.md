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
- [x] Environment variables configured for production (`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL`).
- [x] Static files collected (`python manage.py collectstatic`).
- [x] Health check verified (`/health/`).
