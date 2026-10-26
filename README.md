# Signature Studio

An internal web application for managing company email signatures.

Admins manage employee details, signature templates and **one company-wide banner**. Every
employee's email signature is generated on demand from:

```
EMPLOYEE DATA  +  ACTIVE SIGNATURE TEMPLATE  +  CURRENT PUBLISHED BANNER  →  EMAIL SIGNATURE HTML
```

The banner is **never copied into employee records**. Publishing a new banner changes every
generated signature at once, with no employee record modified.

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Folder structure](#folder-structure)
- [Quick start (no Docker)](#quick-start-no-docker)
- [Environment variables](#environment-variables)
- [Database, migrations and seed data](#database-migrations-and-seed-data)
- [Development login](#development-login)
- [Testing](#testing)
- [Docker](#docker)
- [API overview](#api-overview)
- [Email signature generation](#email-signature-generation)
- [Banner behaviour](#banner-behaviour)
- [Outlook installer (classic Outlook for Windows)](#outlook-installer-classic-outlook-for-windows)
- [Future Outlook / Microsoft 365 integration](#future-outlook--microsoft-365-integration)
- [Future Gmail / Google Workspace integration](#future-gmail--google-workspace-integration)
- [Known limitations](#known-limitations)

---

## Features

**Admin**
- Dashboard with employee, banner and template stats, the current banner, and a live signature preview for any employee
- Employees: search, filter by department and status, add, view, edit, activate/deactivate, delete, optional login account
- Signature builder: pick an employee and template, preview it in an email-style frame, view the HTML, copy the rendered signature, copy the HTML, download HTML
- Templates: create and edit designs (layout, colours, font, photo/social toggles) and activate one
- Banners: create, upload an image, preview, save as draft, publish (with confirmation), unpublish, archive, delete, full history
- Audit log of every sign-in and change
- Settings: company name, default website, legal disclaimer, and an on/off switch for the company logo in signatures
- Built-in Casterly logo (`backend/app/static/brand/casterly-logo.png`): shown on the sign-in page, in the sidebar and, when switched on, at the right of every signature just above the banner (fitted in a 100 × 100 px box). It is fixed in the code, not uploaded; to change it, replace the file and redeploy

**Employee**
- View own profile and own generated signature
- See the current company banner (read-only)
- Copy the signature (rich HTML), copy the raw HTML, or download it

**Security**
- JWT auth, Argon2 password hashing, and logout that revokes the token
- Role checks on the backend for every endpoint (the UI hiding buttons is not relied on)
- Validation on all input, a consistent error envelope, and no stack traces or secrets in responses

## Tech stack

| Layer    | Technology |
|----------|------------|
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS v4, lucide icons |
| Backend  | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL (the only supported database) |
| Auth     | JWT (PyJWT) and Argon2 (argon2-cffi) |
| Tests    | pytest (backend), Vitest and React Testing Library (frontend) |

## Architecture

```
┌──────────────────────┐   REST /api/*  (JSON envelope)    ┌───────────────────────────────┐
│ React SPA (Vite)     │ ────────────────────────────────▶ │ FastAPI                       │
│  pages → hooks       │                                   │  api/ routers  (auth + roles) │
│  (TanStack Query)    │ ◀──────────────────────────────── │  services/     business logic │
│  → services/api.ts   │                                   │  renderers/    email HTML     │
└──────────────────────┘                                   │  database/     SQLAlchemy     │
                                                           └──────────────┬────────────────┘
                                                                          │
                                                               PostgreSQL / SQLite
```

- **Routers** (`app/api`) validate input with Pydantic, enforce roles via dependencies and return `{"success": true, "data": ...}`.
- **Services** (`app/services`) hold all business rules and transactions. Each mutation writes its audit entry in the same transaction.
- **Renderers** (`app/renderers`) are pure functions that turn plain data into email-safe HTML. They never touch the database.
- **Frontend** pages use React Query hooks (`src/hooks/queries.ts`). Every mutation invalidates the affected queries, so the UI always shows real backend state.

Two rules are central:

1. `banner_service.get_current_published_banner()` is the **only** code that decides which banner belongs in signatures.
2. `renderers/banner.py::render_banner_html()` is the **only** banner renderer. The final signature and every UI banner preview (admin editor, banners page, overview, employee page) use its output, via the frontend `BannerPreview` component.

## Folder structure

```
signature-studio/
├── backend/
│   ├── app/
│   │   ├── main.py                 # app factory, CORS, routers, /uploads static files
│   │   ├── seed.py                 # development seed data
│   │   ├── core/                   # config, security (JWT/Argon2), dependencies, errors
│   │   ├── database/               # engine/session, UTC datetime type, models/
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── api/                    # auth, employees, banners, signatures, templates,
│   │   │                           # overview, audit, settings, uploads
│   │   ├── services/               # auth, employee, banner, template, signature,
│   │   │                           # audit, settings, storage
│   │   ├── renderers/              # banner.py, classic.py, minimal.py, layout registry
│   │   └── utils/                  # validators, URL resolution, placeholder images
│   ├── alembic/                    # migrations (0001 schema, 0002 logo switch, 0003 Outlook status)
│   ├── scripts/acceptance.py       # end-to-end scenario against a running server
│   ├── tests/                      # pytest suite
│   ├── uploads/                    # local file storage (served at /uploads)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/             # ui/, banners/, signatures/, employees/, templates/, common/
│   │   ├── layouts/AppShell.tsx    # sidebar + top bar
│   │   ├── pages/                  # LoginPage, admin/*, employee/*
│   │   ├── hooks/                  # useAuth, React Query hooks, signature actions
│   │   ├── services/               # http client, API modules, token storage
│   │   ├── routes/                 # AppRoutes, ProtectedRoute
│   │   ├── types/ utils/ test/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── LICENSE
└── README.md
```

## Quick start (no Docker)

Prerequisites: **Python 3.12+**, **Node.js 20+** and **PostgreSQL 15+**. Create a database user and two
databases (`signature_studio`, and `signature_studio_test` for the tests), e.g. in `psql` as the `postgres` user:

```sql
CREATE ROLE signature_app LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE signature_studio OWNER signature_app;
CREATE DATABASE signature_studio_test OWNER signature_app;
```

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set SECRET_KEY, e.g. the output of:
python -c "import secrets; print(secrets.token_urlsafe(48))"

alembic upgrade head          # create the database schema
python -m app.seed            # load development data (safe to run again)
uvicorn app.main:app --reload --port 8000
```

API: <http://localhost:8000/api>. Interactive docs: <http://localhost:8000/api/docs>.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # defaults work for local development
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/uploads` to the backend,
so no CORS setup is needed in development.

## Environment variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | **required** | PostgreSQL only: `postgresql+psycopg://user:pass@host:5432/signature_studio` |
| `TEST_DATABASE_URL` | *(tests only)* | PostgreSQL test database (name must end in `_test`; wiped on every test run) |
| `SECRET_KEY` | **required** | JWT signing key, at least 32 characters. No default, so secrets are never hardcoded |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Session length without "Remember me" |
| `REMEMBER_ME_EXPIRE_DAYS` | `7` | Session length with "Remember me" |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Absolute base for every image URL in generated email HTML. In production, set it to a URL that email recipients can reach |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins |
| `UPLOAD_DIR` | `uploads` | Local folder for uploaded images |
| `MAX_UPLOAD_MB` | `5` | Upload size limit |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | *(empty)* | Leave empty to use the dev proxy. Set to the API origin for a separate deployment |
| `VITE_BACKEND_PROXY_TARGET` | `http://localhost:8000` | Where the dev server proxies `/api` and `/uploads` |

## Database, migrations and seed data

Tables are created **only** by Alembic, never by hand:

```bash
alembic upgrade head                                   # apply migrations
alembic revision --autogenerate -m "describe change"   # after changing models
```

| Table | Purpose |
|-------|---------|
| `users` | Login accounts: email, Argon2 `password_hash`, `role` (ADMIN/EMPLOYEE), `is_active` |
| `employees` | Personal signature data (name, designation, contacts, photo, social links). Optional `user_id` link to a login. **No banner fields.** |
| `signature_templates` | Layout key and style options. A partial unique index allows **at most one active** template |
| `banners` | Name, title, description, image, target URL, status, start/end dates, published_at, created_by. A partial unique index allows **at most one PUBLISHED** banner |
| `audit_logs` | user, action, entity type/id, description, timestamp |
| `revoked_tokens` | JWT IDs revoked by logout, cleaned up after expiry |
| `app_settings` | Single row: company name, default website, legal disclaimer, `show_logo_in_signature` (on by default) |

All timestamps are stored in **UTC**. The UI converts to and from the viewer's local time.

`python -m app.seed` creates 1 admin, 3 employees (with logins and generated avatar images),
2 templates (one active), app settings, and 2 banners (one published, one draft). It generates
its own placeholder images, so it works offline.

## Development login

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@example.com` | `Admin@12345` |
| Employee | `john.carter@example.com` | `Employee@123` |
| Employee | `priya.nair@example.com` | `Employee@123` |
| Employee | `alex.morgan@example.com` | `Employee@123` |

> ⚠️ These credentials are for local development only. Never run the seed script against a production database.

## Testing

```bash
# Backend: auth, authorization, employees, banners, publishing, signatures, audit, uploads, migrations
cd backend
pytest

# Tests run against the PostgreSQL database in TEST_DATABASE_URL (backend/.env); it is wiped on every run.

# Frontend: login, protected routes, employee list and creation, banner creation and preview,
# publish confirmation, current banner display, signature preview and copy
cd frontend
npm test
npm run typecheck

# End-to-end scenario against a running backend (creates Rahul and Priya, publishes and
# replaces banners, unpublishes, checks every signature and the audit log)
cd backend
python scripts/acceptance.py --base-url http://localhost:8000
```

## Docker

```bash
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
docker compose up --build
docker compose exec backend python -m app.seed
```

This runs PostgreSQL, FastAPI (which applies migrations on start) and the built frontend behind
nginx at <http://localhost:5173>. Docker is optional, and the app runs fully without it.

For the production Ubuntu server, follow [`deploy/DEPLOY.md`](deploy/DEPLOY.md). It covers the private
PostgreSQL, localhost-only ports, `.env` generation, the host nginx site, and creating the first admin
with `python -m app.create_admin` (never `app.seed` in production).

## API overview

All JSON endpoints return `{"success": true, "data": ...}` or
`{"success": false, "error": {"code": "...", "message": "..."}}` with an appropriate HTTP status.

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/api/auth/login` | public | Email and password (+ `remember_me`) → JWT |
| GET | `/api/auth/me` | any | Current user and employee profile |
| POST | `/api/auth/logout` | any | Revoke the current token |
| GET | `/api/employees` | admin | List with `q`, `department`, `status`, `page`, `page_size` |
| POST | `/api/employees` | admin | Create (optional `password` creates a login) |
| GET | `/api/employees/me` | any | Own profile |
| GET | `/api/employees/{id}` | admin / self | Get one |
| PUT | `/api/employees/{id}` | admin | Update |
| PATCH | `/api/employees/{id}/status` | admin | Activate or deactivate |
| DELETE | `/api/employees/{id}` | admin | Delete |
| GET | `/api/banners` | admin | History, optional `status` filter |
| GET | `/api/banners/current` | any | The banner currently in signatures (with rendered HTML) |
| POST | `/api/banners/preview` | admin | Render an unsaved banner |
| POST | `/api/banners` | admin | Create (always DRAFT) |
| GET / PUT / DELETE | `/api/banners/{id}` | admin | Get, update or delete |
| POST | `/api/banners/{id}/publish` | admin | Publish, replacing the current banner in one transaction |
| POST | `/api/banners/{id}/unpublish` | admin | Back to DRAFT |
| POST | `/api/banners/{id}/archive` | admin | Archive |
| GET | `/api/signatures/me` | any | Own signature |
| GET | `/api/signatures/{employee_id}` | admin / self | Signature JSON: `html`, employee, template, banner |
| GET | `/api/signatures/{employee_id}/preview` | admin / self | Full HTML page |
| GET | `/api/signatures/{employee_id}/html` | admin / self | **Raw email-ready HTML** (`?download=true` for a file) |
| GET / POST | `/api/templates` | admin | List or create |
| PUT | `/api/templates/{id}` | admin | Update |
| POST | `/api/templates/{id}/activate` | admin | Make active |
| GET | `/api/templates/layouts` | admin | Available layouts |
| GET | `/api/overview` | admin | Dashboard data |
| GET | `/api/audit-logs` | admin | Paginated, filter by `action`, `entity_type`, `q` |
| GET / PUT | `/api/settings` | admin | Company settings (name, website, disclaimer, logo on/off) |
| GET | `/api/branding` | public | Company name and logo URL (used by the sign-in page) |
| POST | `/api/uploads` | admin | Multipart `file` + `kind` (`banner` or `photo`) → stored path and URL |

## Email signature generation

`signature_service.generate_employee_signature(employee_id)`:

1. Loads the employee.
2. Loads the active template (or the built-in default design if none exists).
3. Calls `get_current_published_banner()`.
4. Renders the HTML with `render_signature_html(employee, template, banner)`.
5. Returns the HTML. Nothing is stored.

The generated HTML is built for email clients:
- Table-based layout with inline styles only: no `<style>` blocks, flexbox, grid or positioning
- No JavaScript
- Every user value is HTML-escaped
- Clickable `mailto:`, `tel:`, website, social and banner links
- Images always use **absolute** URLs built from `PUBLIC_BASE_URL`. Uploaded files are stored as
  `/uploads/...` paths, so changing the domain later updates every signature.

To add a new design, write a `render(ctx) -> str` module in `app/renderers/` and register it in
`app/renderers/__init__.py::LAYOUTS`. Admins can then create templates that use it.

## Banner behaviour

- Stored statuses are `DRAFT`, `PUBLISHED` and `ARCHIVED`. `SCHEDULED` and `EXPIRED` are **derived**
  from a published banner's start and end dates, so no background job is needed.
- **Publishing** runs in one transaction: validate → demote the currently published banner to DRAFT →
  publish the selected banner → set `published_at` → write audit entries → commit. A partial unique
  index guarantees at most one published banner even under concurrent requests.
- A published banner is **in signatures** only between its optional start and end dates.
- **Unpublishing** keeps the record (it returns to DRAFT). Signatures then have no banner.
- **Archived** banners cannot be edited or published and never appear in signatures. Published
  banners must be unpublished before they can be deleted.
- Editing the published banner updates every signature immediately.

> **Important: already-sent email is never changed.** Publishing a banner affects signatures
> generated from that moment on. Emails that have already been sent keep the signature they were
> sent with. With copy/paste signatures, employees need to copy their signature again after a
> banner change. The planned Outlook and Gmail integrations will automate this for new messages.

## Outlook installer (classic Outlook for Windows)

Employees can install their signature into Outlook with one download. No HTML copying.

1. On **My Signature** (or, for admins, on any signature page) click **Install in Outlook**.
2. Run the downloaded `Casterly-Signature-Setup_….exe`. **Don't rename it**: the file name carries the
   employee's installation key.
3. Restart Outlook. The signature is set as the default for new emails, replies and forwards.

How it works:
- Everyone downloads the **same** program (`backend/app/installer/CasterlySignatureSetup.exe`); only the file
  name differs: `Casterly-Signature-Setup_<server-url>.<employee-id>.<key>.exe`. The key is an HMAC of the
  employee id with `SECRET_KEY`, checked by the public `GET /api/installer/signature` endpoint. Keeping the
  program byte-identical means it can be code-signed once.
- The program writes only its own signature, `%APPDATA%\Microsoft\Signatures\Casterly.htm` / `.txt`
  (keeping one backup, `Casterly.htm.previous`). Other signatures in the folder are never touched.
- **First install:** it sets `NewSignature` / `ReplySignature` under
  `HKCU\Software\Microsoft\Office\16.0\Common\MailSettings` to "Casterly", so it becomes the default.
  **Re-runs** update the same signature in place and **keep whatever default the user has chosen**. It never
  sets a default to "(none)".
- It sets `DisableRoamingSignaturesTemporaryToggle` so Microsoft 365 cloud signatures don't overwrite the file.
- The installed signature uses **live banner addresses** instead of one specific banner:
  `GET /banner/current.png` (current banner image, or an invisible 1px strip if none) and
  `GET /banner/current` (redirects to its target URL). Publishing or unpublishing a banner changes every
  installed signature with no reinstall. Personal-detail changes need a re-run.
  Because the image is live, previously sent emails also show the current banner when reopened.
- Downloads and installations are recorded in the audit log.

Build the installer (uses the C# compiler that ships with Windows):

```bash
powershell -ExecutionPolicy Bypass -File installer/build.ps1
```

Test it without touching Outlook: `Casterly-Signature-Setup_….exe --dry-run C:\temp\sig-test` writes the files
and a `result.txt` there and skips the registry.

Limitations: classic Outlook for Windows only (new Outlook, Outlook on the web and mobile don't read signature
files). Unsigned programs trigger Windows SmartScreen ("More info → Run anyway"); sign the `.exe` with a
code-signing certificate to avoid it. `PUBLIC_BASE_URL` must be reachable by employees' PCs and by email
recipients.

## Outlook add-in and signature settings

The add-in (**new Outlook / Outlook on the web / classic Outlook**) inserts a freshly generated signature
into each new email, reply and forward. It **never changes the user's Outlook signature settings**.

- It does **not** call `disableClientSignatureAsync`. In Outlook on the web and new Outlook that call disables
  the user's signature option for new mail and replies, and in classic Outlook/Mac it sets both defaults to
  "(none)". That was the cause of Outlook ending up on "No signature".
- It calls `isClientSignatureEnabledAsync` to see whether the user has their own default signature switched on.
  - **Settings → "use the Casterly signature even if an employee has their own default" off (default):**
    the user's own default is kept; the Casterly signature is inserted automatically only when Outlook has
    no default. The **Insert Casterly signature** button always inserts it.
  - **On:** the Casterly signature is inserted in every new email. `setSignatureAsync` replaces a signature
    already in the email, so there is never a duplicate.
- Office.js has **no API to create saved Outlook signatures or set Outlook's default signature**, and the
  project has no Microsoft Graph integration. The UI therefore says "Default signature must be selected in
  Outlook" instead of claiming it was configured.
- Every insert (or failure, with Outlook's error text) is reported to `GET /api/outlook/report` and stored
  per employee in `outlook_addin_status` (one row, updated in place). Admins see it in the **Outlook** panel
  on the Signatures page and the employee page (`GET /api/signatures/{id}/outlook-status`).

## Send email (signature setup emails)

On **Signatures** (and an employee's page) admins click **Send email**. The employee receives their signature
(with images) and a personal link, `PUBLIC_BASE_URL/setup/<employee-id>.<key>`. The link opens a page, with no
login, that offers the closest thing to one-click setup for each client. A web page cannot change Outlook's
settings by itself, so these are the steps that exist:

- **New Outlook / Outlook on the web:** download the add-in manifest and add it once with **My Add-ins → Add a
  custom add-in → Add from File**. Signatures are then inserted automatically into new emails, replies and forwards.
  The add-in needs `PUBLIC_BASE_URL` to be a permanent public `https://` address. Temporary `trycloudflare.com`
  quick-tunnel addresses are refused at startup.
- **Classic Outlook on Windows:** download the personal installer (sets new + reply signatures).
- **Other apps:** copy the signature, or **Download Signature HTML**.

Automatic sending needs SMTP settings in `backend/.env` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`SMTP_FROM`, `SMTP_SECURITY`). Without them, **Send email** opens a ready-written email in the admin's mail app
with the link. Sends are recorded in the audit log.

## Future Outlook / Microsoft 365 integration

*Not implemented yet.* The API is ready for it:

```
Employee opens the Outlook compose window
  → Outlook add-in (Office.js, on-send / compose event)
  → GET /api/signatures/{employee_id}/html   (or /api/signatures/me)
  → employee identity → employee data + active template + current published banner
  → email-ready HTML signature
  → add-in inserts it into the message body
```

Remaining work: an Office add-in manifest and task pane, Microsoft Entra ID (Azure AD) SSO, and
mapping the Entra identity to an employee (by email), in place of or alongside the local JWT login.

## Future Gmail / Google Workspace integration

*Not implemented yet.* The same `/html` output can be pushed to Gmail with the Gmail API
(`users.settings.sendAs.update`, `signature` field) using a Google Workspace service account
with domain-wide delegation. A scheduled job or a "sync on publish" hook would update every
employee's signature after each banner change.

## Known limitations

- **Outlook and Gmail integrations are not implemented** (see above). Today, employees copy their
  signature into their email client.
- Already-sent emails are never updated (this is how email works).
- Uploaded files are stored on local disk. `services/storage_service.py` has a `Storage` interface
  ready for S3 or Azure Blob, but only `LocalStorage` exists.
- Email clients differ: Outlook for Windows ignores `border-radius`, so profile photos show square there.
- There is no rate limiting on login and no self-service password reset. Admins set passwords.
- Employees cannot edit their own profile. Admins manage all employee data.
- A single company (tenant) per deployment.
