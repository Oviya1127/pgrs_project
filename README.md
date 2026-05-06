# SPGRS – Smart Public Grievance Redressal System

A production-ready grievance redressal portal with a FastAPI backend, PostgreSQL database, and static HTML/JS frontends for citizens and admins.

---

## Tech stack

| Layer     | Technology                          |
|----------|--------------------------------------|
| API      | FastAPI, Uvicorn                    |
| Database | PostgreSQL (asyncpg)                 |
| Auth     | JWT (python-jose), bcrypt (passlib)  |
| Config   | Pydantic Settings, `.env`           |
| Storage  | Cloudinary (attachments)             |
| Frontend | Static HTML, CSS, JavaScript         |

---

## Project structure

```
pgrs_project/
├── config/
│   └── settings.py          # App config (DB, JWT, Cloudinary) from .env
├── backend/
│   ├── app.py               # FastAPI app (API + static mount)
│   ├── middleware/          # Auth, role guard
│   ├── models/              # Pydantic request/response models
│   ├── routes/              # API routers (auth, user, grievance, admin, etc.)
│   ├── services/            # Business logic (auth, grievance, upload, etc.)
│   └── utils/               # DB pool, constants, validators, helpers
├── frontend/
│   ├── assets/              # CSS, JS
│   ├── admin/               # Admin portal HTML pages
│   └── user/                # User portal HTML pages
├── scripts/                 # Optional utility scripts
├── .env.example             # Copy to .env and fill in values
├── create_database.py       # Full DB create + schema + seed
├── create_new_admin.py      # Create/update default admin user
├── seed.py                 # Minimal seed (admin + sample citizen)
├── run.py                  # Start API (8000) + admin server (8001)
└── requirements.txt
```

---

## Setup and run (production-like)

### 1. Virtual environment and dependencies

```bash
python -m venv venv
.\venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2. Environment

Copy `.env.example` to `.env` and set at least:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (PostgreSQL)
- `SECRET_KEY` (strong random string for JWT)
- Optionally: `CLOUDINARY_*` for file uploads

### 3. Database and admin

Run in order:

```bash
python create_database.py   # Creates DB, tables, and full seed data
python create_new_admin.py  # Ensures admin user (sara_admin@gmail.com)
python seed.py              # Ensures admin + citizen@spgrs.com if needed
```

### 4. Start the application

```bash
python run.py
```

- **API & user portal:** http://localhost:8000  
  - User login: http://localhost:8000/ or http://localhost:8000/static/user/user_login.html  
  - API docs: http://localhost:8000/docs  
- **Admin portal:** http://localhost:8001/ or http://localhost:8001/static/admin/admin_login.html  

---

## Default credentials (from seed)

| Role   | Email                 | Password   |
|--------|------------------------|------------|
| Admin  | sara_admin@gmail.com  | admin123   |
| User   | testing@gmail.com     | testing123 |
| Citizen| citizen@spgrs.com     | user123   |

---

## Scripts overview

| Script                | Purpose |
|-----------------------|--------|
| `create_database.py` | One-time/full setup: create DB, drop/create tables, seed users/locations/categories/departments/grievances etc. Uses `config/settings` and `.env`. |
| `create_new_admin.py` | Create or update admin `sara_admin@gmail.com` / `admin123` and ensure `admins` table entry. |
| `seed.py`             | Lightweight: ensure admin and `citizen@spgrs.com` exist (no schema changes). |
| `run.py`              | Starts both servers (API on 8000, admin static on 8001). |

---

## Production notes

- Set a strong `SECRET_KEY` and restrict CORS `allow_origins` in `backend/app.py` for production.
- Run under a process manager (e.g. systemd, Docker) and use a reverse proxy (e.g. Nginx) for HTTPS.
- Keep `.env` out of version control (already in `.gitignore`).
# pgrs_project
