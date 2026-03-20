# Home Cloud Drive

A self-hosted personal cloud storage app with a modern React frontend and a FastAPI backend.

Home Cloud Drive lets you upload, organize, preview, share, and manage files with authentication, quotas, activity tracking, and admin controls.

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Security notes](#security-notes)
- [Useful commands](#useful-commands)
- [Additional documentation](#additional-documentation)

## Features

- JWT authentication (register/login/current-user) with Password Reset Flow
- Resumable chunked file uploads & folder uploads with real-time UI progress
- Server-backed file search with background auto-indexing
- Drag-and-drop organization inside a detailed folder hierarchy
- HTTP Range Request streaming for seamless Video, Audio, & PDF inline preview
- Rename/move/copy/trash/restore/permanent delete flows
- Favorites (starred files)
- Image thumbnails generated server-side
- Secure sharing links (password, expiry, download limits)
- Storage usage reporting + activity logs
- Admin panel for user and quota management

## Architecture

This repository contains a full-stack deployment:

- **Frontend**: React + Vite, served by Nginx in production
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Deployment**: Docker Compose stack with:
  - backend API service
  - frontend static site service
  - optional Cloudflare Tunnel service

## Tech stack

### Frontend

- React 18
- Vite 6
- Lucide React
- Nginx (production)

### Backend

- FastAPI
- SQLAlchemy (async)
- SQLite (`aiosqlite`)
- `python-jose` (JWT)
- `passlib` + `bcrypt` (password hashing)
- Pillow (thumbnails)
- SlowAPI (rate limiting)

## Repository layout

```text
.
├── src/                      # Frontend source
│   ├── components/           # Auth/files/sharing/admin UI components
│   ├── App.jsx               # Main application shell
│   └── api.js                # Frontend API client
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry + startup tasks
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── auth.py           # Authentication helpers
│   │   ├── storage.py        # Local storage service
│   │   ├── thumbnails.py     # Thumbnail generation
│   │   └── routers/          # Route modules
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml        # Full deployment stack
├── Dockerfile                # Frontend image build
├── nginx.conf                # Frontend server config
└── .env.example              # Environment template
```

## Quick start (Docker)

### Prerequisites

- Docker + Docker Compose
- Writable host paths for storage and database files

### 1) Configure environment

```bash
cp .env.example .env
```

Set at least these values in `.env`:

- `SECRET_KEY` (strong random key)
- `STORAGE_PATH` (host path for uploaded files)
- `DATA_PATH` (host path for SQLite data)

### 2) Build and start

```bash
docker-compose up -d --build
```

### 3) Access the app

- Frontend: `http://localhost:3001`

> The backend API is intentionally not published directly by default in `docker-compose.yml`.

## Local development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Linux/macOS
# .\venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend URL: `http://localhost:8000`

### Frontend

From repository root:

```bash
npm install
npm run dev
```

Frontend URL (default): `http://localhost:5173`

## Configuration

Primary variables (root `.env`):

- `SECRET_KEY` — JWT signing key (required)
- `STORAGE_PATH` — host path for uploaded files
- `DATA_PATH` — host path for SQLite data
- `MAX_STORAGE_BYTES` — per-user quota (`0` = unlimited)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — token lifetime
- `CORS_ORIGINS` — comma-separated allowed origins
- `ALLOW_REGISTRATION` — `true` to allow public signups
- `TUNNEL_TOKEN` — required only if using tunnel service

See `backend/.env.example` for backend-specific defaults.

## API overview

Main groups under `/api`:

- `/api/auth` — authentication
- `/api/files` — file operations, upload/download, thumbnails, trash
- `/api/folders` — folder operations
- `/api/storage` — storage stats, activity, trash cleanup
- `/api/admin` — admin-only user/system endpoints
- `/api/share` — share link create/access/revoke

## Security notes

- Use a strong unique `SECRET_KEY` in production.
- Restrict `CORS_ORIGINS` to trusted origins.
- Keep `STORAGE_PATH` and `DATA_PATH` on durable volumes.
- Keep `ALLOW_REGISTRATION=false` unless public sign-up is intended.
- If using Cloudflare Tunnel, keep `TUNNEL_TOKEN` secret.

## Useful commands

```bash
# Frontend production build
npm run build

# Start services

docker-compose up -d --build

# Stop services

docker-compose down
```

## Additional documentation

- Backend service docs: [`backend/README.md`](backend/README.md)
- Development history: [`CHANGELOG.md`](CHANGELOG.md)
