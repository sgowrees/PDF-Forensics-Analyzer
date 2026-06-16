# PDF Forensics Analyzer

A full-stack web application for detecting PDF tampering. Users upload documents through a dashboard; the backend compares them against trusted baseline PDFs and returns a structured risk report with score breakdowns. Admins manage baselines and monitor system-wide analysis activity.

## Features

### User dashboard (`/dashboard`)

- Email/password registration and login (JWT)
- Upload PDFs (max 20 MB) for forensic analysis
- View tamper reports with risk level (`LOW` / `MEDIUM` / `HIGH`), score, findings, and module breakdown
- Browse past results and reopen previous analyses

### Admin dashboard (`/admin`)

- Overview stats: documents, users, baselines, high-risk count
- **Baseline management** — list, upload, and remove trusted PDF templates
- **All analyses** — system-wide document table with owner, risk, and status
- Auto-sync of on-disk baseline PDFs into the admin catalog

User role management is exposed via the admin API (`/api/users/admin/users/`) for programmatic use; promote accounts locally with the Django shell snippet below.

### Forensics engine

The analysis pipeline runs entirely in Python (PyMuPDF + custom checks):

| Module | What it checks |
|--------|----------------|
| **Classifier** | Document type and issuer from text heuristics |
| **Baseline match** | Finds the closest trusted PDF in `templates/baselines/documents/` |
| **Comparison** | Page count, form fields, layout deltas vs baseline |
| **Text** | Encoding anomalies, invisible characters, formatting fingerprints |
| **Layout** | Overlapping blocks, spacing anomalies |
| **Images** | Unexpected images, geometry changes |
| **Metadata** | PDF metadata inconsistencies |
| **Signatures** | Digital signature presence and validity |

Risk scoring aggregates module deltas into a 0–100 score:

- **LOW** — score ≤ 30  
- **MEDIUM** — score ≤ 60  
- **HIGH** — score > 60  

## Tech stack

| Layer | Stack |
|-------|-------|
| **Backend** | Django 6, Django REST Framework, Simple JWT, SQLite |
| **Frontend** | React 19, TypeScript, Vite, React Router 7 |
| **PDF analysis** | PyMuPDF, pdfplumber, pdfminer.six |
| **Tooling** | uv (Python), pytest, Playwright (frontend scaffold), Ruff |

## Project structure

```
PDF-Forensics-Analyzer/
├── backend/
│   ├── apps/
│   │   ├── documents/          # PDF upload, analysis API, forensics engine
│   │   │   ├── forensics/      # analyzer, baseline, checks, scoring, …
│   │   │   ├── api/            # REST views, serializers, URLs
│   │   │   └── services/       # AnalysisService (upload → analyze → persist)
│   │   └── users/              # Auth, roles, admin user API
│   ├── config/                 # Django settings, root URLs
│   ├── templates/
│   │   └── baselines/documents/  # Trusted baseline PDF catalog (used by engine)
│   ├── tests/                  # pytest + CLI analysis script
│   ├── manage.py
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── api/                # HTTP client + JWT helpers
    │   ├── auth/               # AuthContext, protected routes
    │   ├── components/         # FileUpload, AnalysisReport, BaselineManager, …
    │   └── pages/              # Login, Register, UserDashboard, AdminDashboard
    ├── tests/                  # Playwright tests
    └── package.json
```

## Getting started

### Prerequisites

- **Python 3.14**
- **Node.js 20+** (LTS recommended)
- **[uv](https://docs.astral.sh/uv/)** for Python dependency management

### 1. Backend

```bash
cd backend

# Create venv and install dependencies
uv sync

# Install JWT support (required by auth; add to pyproject.toml if missing)
uv pip install djangorestframework-simplejwt

# Optional — defaults work for local dev
# Create backend/.env if you need custom values:
#   SECRET_KEY=your-secret-key
#   DEBUG=True

# Database
uv run python manage.py migrate

# Run server
uv run python manage.py runserver
```

API: `http://127.0.0.1:8000`  
Django admin: `http://127.0.0.1:8000/admin/`

### 2. Frontend

```bash
cd frontend

npm install

# frontend/.env
# VITE_API_URL=http://127.0.0.1:8000

npm run dev
```

App: `http://localhost:5173`

Vite proxies `/api` to the backend during development.

### 3. Create an admin user

Register through the UI, then promote the account:

```bash
cd backend
uv run python manage.py shell -c "
from apps.users.models import User
u = User.objects.get(email='you@example.com')
u.role = 'admin'
u.save()
"
```

Or use Django admin after creating a superuser:

```bash
uv run python manage.py createsuperuser
```

## Usage

### Analyze a PDF (UI)

1. Register or log in at `/login`
2. Open `/dashboard`
3. Drop or select a PDF
4. Review the report (risk badge, score breakdown, findings)
5. Use **Past results** to reopen earlier analyses

### Manage baselines (admin)

1. Log in as an admin → redirected to `/admin`
2. Under **Baseline templates**:
   - **+ Add baseline** — uploads a trusted PDF into `templates/baselines/documents/`
   - **Remove** — deletes the file and database record (with confirmation)
3. New baselines are picked up automatically by the forensics catalog matcher

### Analyze a PDF (CLI)

Run the engine directly without the web app:

```bash
cd backend
uv run python tests/scripts/run_analysis.py path/to/upload.pdf --pretty
uv run python tests/scripts/run_analysis.py path/to/upload.pdf --baseline path/to/baseline.pdf --pretty
```

## API reference

Authentication uses **Bearer JWT** tokens. Login stores `access` and `refresh` in `localStorage`.

### Auth & users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/users/register/` | — | Register (`email`, `password`) |
| `POST` | `/api/users/login/` | — | Login → `{ access, refresh }` |
| `POST` | `/api/users/logout/` | — | Logout (client clears tokens) |
| `GET` | `/api/users/me/` | User | Current user profile |
| `GET` | `/api/users/dashboard/` | User | Stats (admin gets extra fields) |
| `POST` | `/api/auth/refresh/` | — | Refresh access token |
| `GET` | `/api/users/admin/users/` | Admin | List all users |
| `PATCH` | `/api/users/admin/users/<id>/role/` | Admin | Set role (`admin` / `user`) |

### Documents

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/documents/` | User | List documents (admin: all; user: own) |
| `POST` | `/api/documents/upload/` | User | Upload PDF → analysis report |
| `GET` | `/api/documents/<uuid>/` | User | Document detail + analysis |
| `GET` | `/api/documents/templates/` | Admin | List baseline templates |
| `POST` | `/api/documents/templates/upload/` | Admin | Upload baseline PDF |
| `DELETE` | `/api/documents/templates/<id>/` | Admin | Remove baseline |

### Example: login + upload

```bash
# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/users/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"yourpassword"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Upload
curl -X POST http://127.0.0.1:8000/api/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.pdf"
```

## Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key` | Django secret key |
| `DEBUG` | `True` | Debug mode |

Settings modules: `config.settings.local` (dev), `config.settings.production`, `config.settings.test`.

CORS and CSRF are configured for `http://localhost:5173`.

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend base URL |

## Testing

### Backend (pytest)

```bash
cd backend
uv run pytest
```

Includes a real-PDF integration test in `tests/test_analysis.py` (paths point to files under `templates/`).

### Frontend (Playwright)

```bash
cd frontend
npx playwright install
npx playwright test
```

A GitHub Actions workflow runs Playwright on push/PR to `main` / `master`.

### Lint

```bash
# Backend
cd backend && uv run ruff check .

# Frontend
cd frontend && npm run lint
```

## How baselines work

1. Trusted PDFs live in `backend/templates/baselines/documents/`.
2. When a user uploads a document, the classifier determines type and issuer.
3. `load_baseline()` picks a match by filename mapping, catalog similarity, or type/issuer path.
4. `compare()` and check modules diff the upload against the baseline.
5. Admins add/remove baselines via the API; uploads write directly to the catalog directory so analysis uses them immediately.

On first baseline list load, any PDFs already on disk are registered in the database (`baseline_sync`).

## Roles

| Role | Access |
|------|--------|
| `user` | Own uploads, own history, dashboard stats for own documents |
| `admin` | Everything above + `/admin`, baseline CRUD, all documents, user list API |

## License

MIT (see `backend/pyproject.toml`).
