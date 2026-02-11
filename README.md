<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
</p>

<h1 align="center">📝 ScribeSnap</h1>

<p align="center">
  <strong>AI-Powered Handwritten Note Parser</strong><br/>
  A production-grade, full-stack application that converts handwritten notes into digital text using Google Gemini Vision — built with FastAPI, Next.js 14, PostgreSQL, and Docker.
</p>

<p align="center">
  <a href="#-architecture">Architecture</a> •
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-system-design">System Design</a> •
  <a href="#-engineering-decisions">Engineering Decisions</a>
</p>

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [System Design (HLD)](#-high-level-system-design-hld)
- [System Design (LLD)](#-low-level-system-design-lld)
- [Engineering Decisions](#-engineering-decisions)
- [Resilience Patterns](#-resilience-patterns)
- [Database Design](#-database-design)
- [Security Considerations](#-security-considerations)
- [Testing Strategy](#-testing-strategy)
- [Project Structure](#-project-structure)
- [Assumptions & Constraints](#-assumptions--constraints)
- [Troubleshooting](#-troubleshooting)
- [Future Roadmap](#-future-roadmap--technical-debt)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ScribeSnap Architecture                     │
│                                                                     │
│  ┌───────────┐     HTTP/REST     ┌──────────────┐    Async SQL     │
│  │  Next.js  │ ◄──────────────► │   FastAPI    │ ◄────────────►   │
│  │  Frontend │    JSON + Multipart│   Backend   │   asyncpg        │
│  │  (React)  │                   │  (Python)   │                   │
│  │           │                   │             │   ┌──────────┐   │
│  │  Port 3000│                   │  Port 8000  │──►│PostgreSQL│   │
│  └───────────┘                   └──────┬───────┘   │  Port 5432│   │
│       │                                 │           └──────────┘   │
│       │                                 │                           │
│  ┌────┴────┐                   ┌────────┴────────┐                 │
│  │ shadcn  │                   │  Google Gemini  │                 │
│  │ Tailwind│                   │  Vision API     │                 │
│  │ Framer  │                   │  (gemini-1.5)   │                 │
│  └─────────┘                   └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Core

| Feature              | Description                                                       |
| -------------------- | ----------------------------------------------------------------- |
| 📸 Image Upload      | Drag-and-drop or click-to-upload with real-time preview           |
| 🤖 AI Parsing        | Google Gemini Vision extracts handwritten text with high accuracy |
| 📖 Note History      | Cursor-based paginated history with infinite scroll               |
| 🔍 Search & Filter   | Full-text search and date range filtering                         |
| 📋 Copy to Clipboard | One-click copy of extracted text                                  |

### Engineering Excellence

| Feature               | Description                                                    |
| --------------------- | -------------------------------------------------------------- |
| 🔁 Circuit Breaker    | Prevents cascade failures when Gemini API is down              |
| 🔄 Retry with Backoff | Exponential backoff + jitter for transient failures            |
| 🛡 Rate Limiting      | Sliding window per-IP rate limiter (100 req/hr)                |
| 📊 Structured Logging | JSON-formatted logs with request ID correlation                |
| ❤️ Health Checks      | Deep health probes for DB and Gemini connectivity              |
| 🔒 Input Validation   | MIME type, file size, extension, and path traversal protection |

### UI/UX

| Feature          | Description                                         |
| ---------------- | --------------------------------------------------- |
| 🌙 Dark Mode     | System-aware with manual toggle via Command Palette |
| ⌨️ Cmd+K Palette | Global command palette for navigation and actions   |
| 💎 Glassmorphism | Apple-inspired frosted glass UI components          |
| 🎨 Animations    | Framer Motion transitions for premium feel          |
| ♿ Accessibility | ARIA labels, keyboard navigation, focus management  |

---

## 🛠 Tech Stack

### Backend

| Technology         | Purpose             | Why This Choice                                                       |
| ------------------ | ------------------- | --------------------------------------------------------------------- |
| **FastAPI**        | REST API framework  | Async-native, auto OpenAPI docs, type hints, fastest Python framework |
| **PostgreSQL 16**  | Relational database | UUID support, JSONB, robust indexing, battle-tested ACID compliance   |
| **SQLAlchemy 2.0** | Async ORM           | Type-safe queries, connection pooling, migration support via Alembic  |
| **asyncpg**        | PostgreSQL driver   | 3x faster than psycopg2, native async, prepared statement caching     |
| **Google Gemini**  | Vision AI model     | Multimodal input, excellent handwriting OCR, generous free tier       |
| **Tenacity**       | Retry library       | Declarative retry policies, exponential backoff, composable           |
| **python-magic**   | MIME detection      | Reads file headers (not extension) — prevents disguised uploads       |
| **Pydantic v2**    | Validation          | 5-17x faster than v1, compile-time model generation                   |

### Frontend

| Technology         | Purpose           | Why This Choice                                                     |
| ------------------ | ----------------- | ------------------------------------------------------------------- |
| **Next.js 14**     | React framework   | App Router, Server Components, built-in optimization                |
| **TypeScript**     | Type safety       | Catches bugs at compile time, better IDE experience                 |
| **shadcn/ui**      | Component library | Copy-paste components, full customization control, Radix primitives |
| **Tailwind CSS**   | Styling           | Utility-first, design tokens, dark mode, responsive out of box      |
| **TanStack Query** | Data fetching     | Caching, infinite queries, optimistic updates, devtools             |
| **Framer Motion**  | Animations        | Declarative, layout animations, gesture support                     |
| **react-dropzone** | File upload       | Accessible drag-and-drop with MIME filtering                        |

### Infrastructure

| Technology         | Purpose          | Why This Choice                                     |
| ------------------ | ---------------- | --------------------------------------------------- |
| **Docker**         | Containerization | Reproducible builds, isolated environments          |
| **Docker Compose** | Orchestration    | Single-command startup, service dependencies        |
| **Alembic**        | DB Migrations    | Version-controlled schema changes, rollback support |

---

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended) — OR —
- Python 3.12+, Node.js 18+, PostgreSQL 16+
- Google Gemini API key (free): https://aistudio.google.com/app/apikey

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/scribesnap.git
cd scribesnap

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start all services
docker compose up --build -d

# Verify health
curl http://localhost:8000/health
```

Services will be available at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

### Option 2: Local Development

```bash
# ── Backend ──────────────────────────────────────────
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# macOS only: Install libmagic for MIME detection
brew install libmagic

# Configure environment
cp ../.env.example .env
# Edit .env with your DATABASE_URL and GEMINI_API_KEY

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ── Frontend ─────────────────────────────────────────
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 🔐 Environment Variables

| Variable               | Required | Default                                        | Description                                                                    |
| ---------------------- | -------- | ---------------------------------------------- | ------------------------------------------------------------------------------ |
| `DATABASE_URL`         | ✅       | `postgresql+asyncpg://...localhost/scribesnap` | Async PostgreSQL connection string                                             |
| `GEMINI_API_KEY`       | ✅       | —                                              | Google Gemini API key ([get one free](https://aistudio.google.com/app/apikey)) |
| `GEMINI_MODEL`         | ❌       | `gemini-1.5-flash`                             | Model variant (`flash` = fast/cheap, `pro` = higher quality)                   |
| `STORAGE_ROOT`         | ❌       | `./storage`                                    | Directory for uploaded images                                                  |
| `MAX_FILE_SIZE`        | ❌       | `10485760` (10MB)                              | Maximum upload file size in bytes                                              |
| `CORS_ORIGINS`         | ❌       | `http://localhost:3000`                        | Comma-separated allowed origins                                                |
| `LOG_LEVEL`            | ❌       | `INFO`                                         | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                        |
| `DB_POOL_SIZE`         | ❌       | `20`                                           | Connection pool size (5–100)                                                   |
| `DB_MAX_OVERFLOW`      | ❌       | `10`                                           | Extra connections for traffic spikes (0–50)                                    |
| `DB_POOL_PRE_PING`     | ❌       | `true`                                         | Validate connections before use                                                |
| `RETRY_MAX_ATTEMPTS`   | ❌       | `3`                                            | Gemini API retry attempts (1–10)                                               |
| `RETRY_MIN_WAIT`       | ❌       | `2`                                            | Minimum retry wait in seconds                                                  |
| `RETRY_MAX_WAIT`       | ❌       | `10`                                           | Maximum retry wait in seconds                                                  |
| `CB_FAILURE_THRESHOLD` | ❌       | `5`                                            | Failures before circuit opens (2–20)                                           |
| `CB_RECOVERY_TIMEOUT`  | ❌       | `60`                                           | Seconds before retrying after circuit opens (10–300)                           |
| `RATE_LIMIT_REQUESTS`  | ❌       | `100`                                          | Max requests per window per IP                                                 |
| `RATE_LIMIT_WINDOW`    | ❌       | `3600`                                         | Rate limit window in seconds                                                   |

---

## 📡 API Reference

### `POST /api/parse` — Parse Handwritten Note

Uploads an image and extracts text using Gemini Vision.

```bash
curl -X POST http://localhost:8000/api/parse \
  -F "file=@handwritten_note.jpg"
```

**Response** `201 Created`:

```json
{
  "message": "Note parsed successfully",
  "parsed_text": "Dear Mom, I hope you are doing well...",
  "note": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "image_url": "/api/files/2024/01/15/550e8400.jpg",
    "parsed_text": "Dear Mom, I hope you are doing well...",
    "created_at": "2024-01-15T10:30:00Z",
    "status": "completed",
    "error_message": null
  }
}
```

**Error Responses**:
| Status | Error | Cause |
|--------|-------|-------|
| `400` | `validation_error` | Invalid file type, oversized, empty file |
| `429` | `rate_limit_exceeded` | Too many requests (check `Retry-After` header) |
| `503` | `circuit_breaker_open` | Gemini API unavailable, try again later |
| `500` | `internal_error` | Unexpected server error |

---

### `GET /api/notes` — List Notes (Paginated)

Cursor-based pagination for efficient traversal.

```bash
# First page
curl "http://localhost:8000/api/notes?limit=20"

# Next page (use next_cursor from previous response)
curl "http://localhost:8000/api/notes?limit=20&cursor=2024-01-15T10:30:00Z_550e8400"

# With date filter
curl "http://localhost:8000/api/notes?from_date=2024-01-01&to_date=2024-01-31"
```

**Response** `200 OK`:

```json
{
  "notes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "image_url": "/api/files/2024/01/15/550e8400.jpg",
      "text_preview": "Dear Mom, I hope you are doing...",
      "created_at": "2024-01-15T10:30:00Z",
      "status": "completed"
    }
  ],
  "total_count": 42,
  "next_cursor": "2024-01-14T09:15:00Z_330e7200",
  "has_more": true
}
```

**Headers**: `X-Total-Count: 42`, `Cache-Control: private, max-age=30`

---

### `GET /api/notes/{id}` — Get Note Detail

```bash
curl http://localhost:8000/api/notes/550e8400-e29b-41d4-a716-446655440000
```

---

### `GET /health` — Health Check

```bash
curl http://localhost:8000/health
```

**Response** `200 OK`:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "gemini": "reachable",
  "circuit_breaker": "closed",
  "uptime_seconds": 3600
}
```

---

## 🏛 High-Level System Design (HLD)

### System Context Diagram

```
                    ┌─────────────────────────────────────────┐
                    │              User's Browser              │
                    │                                         │
                    │  ┌─────────────────────────────────┐    │
                    │  │       Next.js 14 Frontend        │    │
                    │  │   (React, Tailwind, shadcn/ui)   │    │
                    │  └────────────┬──────────────────────┘    │
                    └───────────────┼──────────────────────────┘
                                    │
                                    │ REST API (JSON + Multipart)
                                    │ Port 3000 → Port 8000
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.12)                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Middleware Chain                       │   │
│  │  Rate Limiter → Request ID → Logging → GZip → CORS      │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │                    Route Layer                            │   │
│  │  POST /api/parse  │  GET /api/notes  │  GET /health       │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │                   Service Layer                           │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐   │   │
│  │  │ NoteService │  │ FileService  │  │ GeminiService  │   │   │
│  │  │ (orchestrate│  │ (validate +  │  │ (circuit break │   │   │
│  │  │  workflow)  │  │  store)      │  │  + retry)      │   │   │
│  │  └─────────────┘  └──────────────┘  └───────┬────────┘   │   │
│  └─────────────────────────────────────────────┼────────────┘   │
│                           │                     │               │
│              ┌────────────▼──┐         ┌────────▼────────┐      │
│              │  PostgreSQL   │         │  Google Gemini   │      │
│              │  (asyncpg)   │         │  Vision API      │      │
│              │  Port 5432   │         │  (External)      │      │
│              └──────────────┘         └─────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow — Parse Image

```
User                Frontend              Backend                  Gemini
 │                    │                     │                        │
 │  Drop image        │                     │                        │
 │───────────────────►│                     │                        │
 │                    │  POST /api/parse    │                        │
 │                    │  (multipart/form)   │                        │
 │                    │───────────────────► │                        │
 │                    │                     │  1. Rate limit check   │
 │                    │                     │  2. Validate extension │
 │                    │                     │  3. Validate MIME type │
 │                    │                     │  4. Validate file size │
 │                    │                     │  5. Store to disk      │
 │                    │                     │     /storage/YYYY/MM/  │
 │                    │                     │  6. Create DB record   │
 │                    │                     │     (status=processing)│
 │                    │                     │  7. Circuit breaker    │
 │                    │                     │     check              │
 │                    │                     │────────────────────────►│
 │                    │                     │  8. Gemini Vision API  │
 │                    │                     │◄────────────────────────│
 │                    │                     │  9. Update DB record   │
 │                    │                     │     (status=completed) │
 │                    │  201 Created        │                        │
 │                    │◄───────────────────│                        │
 │  Show result       │                     │                        │
 │◄───────────────────│                     │                        │
```

---

## 🔍 Low-Level System Design (LLD)

### Class Diagram

```
┌─────────────────────────┐       ┌──────────────────────────┐
│      Settings           │       │       Note (Model)       │
│ (pydantic-settings)     │       │  (SQLAlchemy)            │
├─────────────────────────┤       ├──────────────────────────┤
│ + database_url: str     │       │ + id: UUID (PK)          │
│ + gemini_api_key: str   │       │ + image_path: str        │
│ + storage_root: str     │       │ + parsed_text: str?      │
│ + max_file_size: int    │       │ + created_at: datetime   │
│ + db_pool_size: int     │       │ + status: enum           │
│ + cb_failure_threshold  │       │ + error_message: str?    │
│ + rate_limit_requests   │       │ + retry_count: int       │
├─────────────────────────┤       ├──────────────────────────┤
│ + validate_required()   │       │ INDEX: created_at DESC   │
│ + cors_origins_list     │       └──────────────────────────┘
└─────────────────────────┘
            │
            │ reads
            ▼
┌─────────────────────────┐
│    NoteService          │         ┌───────────────────────┐
│    (Orchestrator)       │────────►│   FileService         │
├─────────────────────────┤         ├───────────────────────┤
│ + parse_note()          │         │ + validate_extension()│
│ + get_note()            │         │ + validate_size()     │
│ + list_notes()          │         │ + validate_mime_type()│
├─────────────────────────┤         │ + validate_and_store()│
│ Uses: FileService       │         │ + cleanup_file()      │
│ Uses: GeminiService     │         └───────────────────────┘
│ Uses: AsyncSession      │
└──────────┬──────────────┘
           │
           │ uses
           ▼
┌─────────────────────────┐       ┌──────────────────────────┐
│  «abstract»             │       │   CircuitBreaker         │
│  LLMService             │       ├──────────────────────────┤
├─────────────────────────┤       │ - state: enum            │
│ + parse_image(): str    │       │ - failure_count: int     │
│ + health_check(): bool  │       │ - failure_threshold: int │
└──────────┬──────────────┘       │ - last_failure_time: float│
           │                       │ - recovery_timeout: int  │
           │ implements            ├──────────────────────────┤
           ▼                       │ + can_execute()          │
┌─────────────────────────┐       │ + record_success()       │
│    GeminiService        │──────►│ + record_failure()       │
├─────────────────────────┤ uses  │ + state (property)       │
│ - model: GenerativeModel│       └──────────────────────────┘
│ - circuit_breaker: CB   │
├─────────────────────────┤
│ + parse_image()         │  ◄── @retry(exponential_backoff)
│ + health_check()        │
│ - _build_prompt()       │
└─────────────────────────┘
```

### Circuit Breaker State Machine

```
                    ┌──────────┐
                    │  CLOSED  │ ◄──── Normal operation
                    │          │       All calls pass through
                    └────┬─────┘
                         │
                    failure_count++
                         │
                    failure_count >= threshold (5)?
                         │
                    ┌────▼─────┐
          ┌────────│   OPEN   │       All calls rejected
          │        │          │       Returns 503 immediately
          │        └────┬─────┘       No API calls made
          │             │
          │        recovery_timeout (60s) elapsed?
          │             │
          │        ┌────▼─────┐
          │        │HALF_OPEN │       ONE call allowed
          │        │          │       "Canary" request
          │        └─┬──────┬─┘
          │          │      │
          │     success  failure
          │          │      │
          │    ┌─────▼┐  ┌──▼──────┐
          │    │CLOSED│  │  OPEN   │
          └────│      │  │(reset   │
               │      │  │ timer)  │
               └──────┘  └─────────┘

Timeline Example:
  t=0s   t=10s  t=20s  t=30s  t=60s  t=61s
  ──┬──────┬──────┬──────┬──────┬──────┬───►
    │      │      │      │      │      │
   FAIL   FAIL   FAIL  FAIL   FAIL   TRY
   #1     #2     #3    #4     #5     ONE
                                │
                            CIRCUIT    HALF_OPEN
                            OPENS      (canary)
```

### Cursor-Based Pagination (vs Offset)

```
Why cursor > offset pagination:

Offset Pagination (BAD for large datasets):
  SELECT * FROM notes ORDER BY created_at DESC OFFSET 10000 LIMIT 20;
  ├── DB must scan & discard 10,000 rows
  ├── O(offset + limit) — gets slower as you paginate deeper
  └── Inconsistent if rows are inserted during pagination

Cursor Pagination (GOOD):
  SELECT * FROM notes
  WHERE (created_at, id) < ('2024-01-15T10:00:00Z', 'uuid-here')
  ORDER BY created_at DESC, id DESC
  LIMIT 20;
  ├── Uses B-tree index directly — seeks to position
  ├── O(log n + limit) — constant time regardless of page depth
  └── Consistent — new inserts don't shift results

Performance comparison at scale:
  ┌─────────────┬────────────┬─────────────┐
  │ Page Depth  │  Offset    │   Cursor    │
  ├─────────────┼────────────┼─────────────┤
  │ Page 1      │   ~2ms     │   ~2ms      │
  │ Page 100    │  ~15ms     │   ~2ms      │
  │ Page 1000   │ ~120ms     │   ~2ms      │
  │ Page 10000  │ ~1200ms    │   ~2ms      │ ← 600x faster
  └─────────────┴────────────┴─────────────┘
```

### Middleware Chain — Request Lifecycle

```
  Incoming HTTP Request
         │
         ▼
  ┌──────────────────────┐
  │   Rate Limiter       │──── 429 if exceeded
  │   (sliding window)   │     + Retry-After header
  └──────────┬───────────┘
             │ pass
             ▼
  ┌──────────────────────┐
  │   Request ID         │──── Generate UUID
  │   (ContextVar)       │     Set X-Request-ID header
  └──────────┬───────────┘     Store in async context
             │
             ▼
  ┌──────────────────────┐
  │   Logging Middleware  │──── Log: method, path, IP
  │   (structured JSON)  │     Start duration timer
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │   GZip Compression   │──── Compress responses > 500B
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │   CORS Middleware     │──── Validate origin
  └──────────┬───────────┘     Add CORS headers
             │
             ▼
  ┌──────────────────────┐
  │   Route Handler       │──── Business logic
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │   Exception Handler   │──── Catch & format errors
  │   (global)            │     Map to HTTP status codes
  └──────────┬───────────┘
             │
             ▼
  Outgoing HTTP Response
  (with X-Request-ID, timing, compression)
```

---

## 🧠 Engineering Decisions

### Why FastAPI over Django/Flask?

| Criterion        | Django                | Flask               | FastAPI ✅                  |
| ---------------- | --------------------- | ------------------- | --------------------------- |
| Async support    | Partial (3.1+)        | Limited (via Quart) | Native async/await          |
| Auto API docs    | ❌ External (DRF)     | ❌ External         | ✅ Built-in Swagger + ReDoc |
| Type safety      | ❌ Loose              | ❌ Loose            | ✅ Pydantic + type hints    |
| Performance      | ~5K req/s             | ~8K req/s           | ~15K req/s                  |
| Learning curve   | Steep                 | Gentle              | Moderate                    |
| For this project | Overkill (admin, ORM) | Too minimal         | Right-sized                 |

### Why PostgreSQL over MongoDB?

Our data is relational (notes have structured fields, indexes). PostgreSQL gives us:

- **UUID primary keys** — native `uuid` type (no string casting)
- **Timestamp with timezone** — critical for correct ordering
- **B-tree indexes** — powers our cursor pagination
- **ACID transactions** — data integrity on write path
- **JSON support** — if we need schema flexibility later

MongoDB would require manual consistency enforcement and cannot efficiently do cursor-based pagination across compound keys.

### Why Cursor Pagination over Offset?

See the [LLD section](#-low-level-system-design-lld) for the full performance comparison. Key reasons:

1. **Constant-time performance** regardless of page depth
2. **No skipped/duplicate rows** when data changes during pagination
3. **Index-only scans** — PostgreSQL never reads discarded rows

### Why Circuit Breaker Pattern?

Without it, when Gemini API goes down:

- Every request blocks for 60s (timeout) then fails
- Server threads are exhausted waiting
- Database connections pile up
- Entire application becomes unresponsive

With circuit breaker:

- After 5 consecutive failures → immediate 503 response (~1ms vs 60s)
- Gemini gets recovery time (no request bombardment)
- Other endpoints (health, list notes) remain responsive
- Automatic recovery when API returns

### Why Separate File Validation from API Layer?

The `FileService` performs 4-layer validation:

```
Layer 1: Extension Check     ← Fast reject (string comparison)
Layer 2: Size Check          ← Fast reject (integer comparison)
Layer 3: MIME Type Check     ← Reads file header bytes (python-magic)
Layer 4: Content Validation  ← Gemini processes the actual image

Why not just trust the extension?
  malware.jpg.exe → Extension says .exe ✅ rejected
  virus.png       → Extension says .png, but MIME is application/x-executable ✅ rejected
  image.txt       → Extension says .txt ✅ rejected (not in allowed list)
```

---

## 🔄 Resilience Patterns

### Retry Strategy (Tenacity)

```python
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((APIError, Timeout)),
)
```

**Timeline of retries with jitter:**

```
Attempt 1: Immediate          ──► FAIL
            wait: 2s + rand(0-2s) = ~3s
Attempt 2: +3 seconds         ──► FAIL
            wait: 4s + rand(0-2s) = ~5s
Attempt 3: +5 seconds         ──► SUCCESS or final FAIL
                                   Total max wait: ~8s
```

**Why jitter?** Prevents the thundering herd problem where multiple workers retry at the same time and overwhelm the recovering service.

### Rate Limiting (Sliding Window)

```
Window: 1 hour (3600 seconds)
Limit: 100 requests per IP

Timeline:
  ┌──────────────────────────────────────────────┐
  │ IP: 192.168.1.10                              │
  │                                                │
  │  10:00    10:15    10:30    10:45    11:00     │
  │   ├────────┼────────┼────────┼────────┤       │
  │   │ 30 req │ 25 req │ 20 req │ 25 req │       │
  │   │        │        │        │        │       │
  │   └────────┴────────┴────────┴────────┘       │
  │                                    ↑           │
  │                              Total: 100        │
  │                              NEXT REQUEST: 429 │
  │                              Retry-After: 900s │
  └────────────────────────────────────────────────┘
```

---

## 🗄 Database Design

### Notes Table (ER Diagram)

```
┌─────────────────────────────────────────────┐
│                    notes                     │
├─────────────────────────────────────────────┤
│ id            UUID         PK  DEFAULT uuid │
│ image_path    VARCHAR(512) NOT NULL          │
│ parsed_text   TEXT         NULLABLE          │
│ created_at    TIMESTAMPTZ  NOT NULL DEFAULT  │
│ status        VARCHAR(20)  NOT NULL DEFAULT  │
│               'processing'                   │
│ error_message TEXT         NULLABLE          │
│ retry_count   INTEGER      NOT NULL DEFAULT 0│
├─────────────────────────────────────────────┤
│ INDEX: ix_notes_created_at (created_at DESC)│
│   └── Used by: cursor pagination, list API  │
│   └── Type: B-tree (range scans)            │
│   └── Why DESC: Most recent notes first     │
└─────────────────────────────────────────────┘
```

### Status State Machine

```
                ┌─────────────┐
                │ processing  │ ← Initial state (record created)
                └──────┬──────┘
                       │
               ┌───────┴───────┐
               │               │
         ┌─────▼─────┐  ┌─────▼─────┐
         │ completed │  │  failed   │
         │           │  │           │
         └───────────┘  └───────────┘
           (final)        (final)
```

---

## 🔒 Security Considerations

| Threat                  | Mitigation                                                         |
| ----------------------- | ------------------------------------------------------------------ |
| **Path Traversal**      | File serving validates path doesn't escape `STORAGE_ROOT`          |
| **File Upload Attacks** | 4-layer validation: extension → size → MIME → content              |
| **SQL Injection**       | Parameterized queries via SQLAlchemy ORM                           |
| **XSS**                 | API returns JSON only (no HTML rendering)                          |
| **DDoS**                | Sliding window per-IP rate limiter                                 |
| **Credential Exposure** | Env vars only, never in code; `.env` is gitignored                 |
| **CORS**                | Restrictive allowlist (only configured origins)                    |
| **Server Info Leakage** | Internal errors return generic message, details logged server-side |

---

## 🧪 Testing Strategy

```
                  ┌───────────────┐
                  │  Unit Tests   │  ← Fast, no external deps
                  │  (mocked DB,  │     ~50ms per test
                  │   mocked API) │
                  ├───────────────┤
                  │  Integration  │  ← Real DB, mocked API
                  │  Tests        │     ~500ms per test
                  ├───────────────┤
                  │  E2E Tests    │  ← Full stack via Docker
                  │  (manual)     │     ~5s per test
                  └───────────────┘
```

**Run tests:**

```bash
cd backend
python -m pytest tests/ -v              # All tests
python -m pytest tests/ -m unit         # Unit tests only
python -m pytest tests/ -m "not slow"   # Skip slow tests
```

**Test coverage areas:**

- `test_file_service.py`: Extension validation, size limits, cleanup
- `test_gemini_service.py`: Circuit breaker states, mocked API, health check
- `test_note_service.py`: Parse workflow, get/list operations, error handling

---

## 📁 Project Structure

```
scribesnap/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # App factory + lifespan + exception handlers
│   │   ├── config.py            # Pydantic Settings (all env vars)
│   │   ├── database.py          # Async SQLAlchemy engine + session dependency
│   │   ├── exceptions.py        # Custom exception hierarchy (8 types)
│   │   ├── models/
│   │   │   └── note.py          # SQLAlchemy Note model (UUID PK, indexes)
│   │   ├── schemas/
│   │   │   └── note.py          # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── llm_base.py      # Abstract LLM interface (Strategy pattern)
│   │   │   ├── gemini_service.py # Gemini + Circuit Breaker + Retry
│   │   │   ├── file_service.py  # Upload validation + date-organized storage
│   │   │   └── note_service.py  # Business logic orchestrator
│   │   ├── routes/
│   │   │   ├── parse.py         # POST /api/parse (multipart upload)
│   │   │   ├── notes.py         # GET /api/notes (cursor pagination)
│   │   │   └── health.py        # GET /health (deep checks)
│   │   └── middleware/
│   │       ├── request_id.py    # UUID correlation (ContextVar)
│   │       ├── logging.py       # Structured JSON request logging
│   │       └── rate_limit.py    # Sliding window per-IP limiter
│   ├── alembic/                 # Database migrations
│   │   └── versions/
│   │       └── 001_create_notes_table.py
│   ├── tests/
│   │   ├── conftest.py          # Shared fixtures (mock DB, temp dirs)
│   │   ├── test_file_service.py
│   │   ├── test_gemini_service.py
│   │   └── test_note_service.py
│   ├── Dockerfile               # Multi-stage, non-root, health check
│   ├── requirements.txt         # Pinned dependencies with annotations
│   └── pyproject.toml           # Pytest configuration
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout (Providers, Navbar, Toaster)
│   │   │   ├── page.tsx         # Home — hero + upload zone
│   │   │   ├── history/page.tsx # Note history with infinite scroll
│   │   │   ├── notes/[id]/page.tsx # Note detail (image + text)
│   │   │   └── globals.css      # Design tokens + glassmorphism
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx   # Sticky nav, scroll-aware, blur
│   │   │   │   └── CommandPalette.tsx  # Cmd+K global actions
│   │   │   ├── upload/
│   │   │   │   ├── UploadZone.tsx      # State machine + drag-drop
│   │   │   │   └── ParseResult.tsx     # Split view + copy
│   │   │   └── notes/
│   │   │       ├── NoteCard.tsx        # Glass card + hover effects
│   │   │       ├── NoteGrid.tsx        # Infinite scroll + toggle
│   │   │       └── EmptyState.tsx      # Onboarding CTA
│   │   ├── hooks/
│   │   │   ├── useParseNote.ts  # Mutation (React Query)
│   │   │   └── useNoteHistory.ts # Infinite query + cursor
│   │   └── lib/
│   │       ├── api.ts           # Typed fetch wrapper
│   │       ├── types.ts         # Backend-synced interfaces
│   │       └── utils.ts         # cn(), date formatting, clipboard
│   └── Dockerfile               # Multi-stage standalone build
│
├── docker-compose.yml           # PostgreSQL + Backend + Frontend
├── .env.example                 # Documented environment template
└── .gitignore                   # Python, Node, Docker, IDE, storage
```

---

## 📌 Assumptions & Constraints

| Assumption                  | Rationale                                                  |
| --------------------------- | ---------------------------------------------------------- |
| **Single-user application** | No auth needed — runs locally                              |
| **English handwriting**     | Gemini prompt optimized for English                        |
| **10MB file size limit**    | Balances quality with server memory                        |
| **Local file storage**      | No cloud object storage (S3) for simplicity                |
| **In-memory rate limiter**  | Single-process deployment; Redis needed for multi-instance |
| **Synchronous parsing**     | User waits for result; 10-30s for complex images           |

---

## 🔧 Troubleshooting

<details>
<summary><strong>Port 5432 already in use</strong></summary>

```bash
# Find what's using the port
lsof -i :5432

# Option 1: Stop the conflicting process
# Option 2: Change the port in docker-compose.yml
ports:
  - "5433:5432"  # Map to 5433 instead
```

</details>

<details>
<summary><strong>GEMINI_API_KEY not working</strong></summary>

1. Verify the key at https://aistudio.google.com/app/apikey
2. Check it's in your `.env` file (not `.env.example`)
3. Run health check: `curl http://localhost:8000/health`
4. Check logs: `docker compose logs backend`
</details>

<details>
<summary><strong>python-magic import error on macOS</strong></summary>

```bash
# Install libmagic (required by python-magic for MIME detection)
brew install libmagic
```

</details>

<details>
<summary><strong>Database connection refused</strong></summary>

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Force restart
docker compose restart postgres

# Nuclear option: reset DB
docker compose down -v && docker compose up -d
```

</details>

<details>
<summary><strong>Frontend can't reach backend (CORS error)</strong></summary>

Ensure `CORS_ORIGINS` includes your frontend URL:

```bash
CORS_ORIGINS=http://localhost:3000
```

</details>

---

## 🗺 Future Roadmap & Technical Debt

### Near-term

- [ ] **Redis rate limiter** — Replace in-memory with Redis for multi-instance support
- [ ] **WebSocket progress** — Real-time parsing progress instead of polling
- [ ] **Batch upload** — Process multiple images concurrently
- [ ] **Full-text search** — PostgreSQL `tsvector` indexing for parsed text search

### Mid-term

- [ ] **Authentication** — OAuth2 / JWT for multi-user support
- [ ] **S3 storage** — Cloud object storage for images
- [ ] **Worker queue** — Celery + Redis for async parsing (return immediately, poll for result)
- [ ] **PDF export** — Download notes as formatted PDF

### Long-term

- [ ] **Multi-language support** — Detect and parse non-English handwriting
- [ ] **Handwriting style training** — Fine-tune model on user's specific handwriting
- [ ] **Mobile app** — React Native with camera integration
- [ ] **Collaborative notes** — Share parsed notes with others

### Known Technical Debt

| Item                                          | Impact                             | Priority |
| --------------------------------------------- | ---------------------------------- | -------- |
| In-memory rate limiter resets on restart      | Low (single-user)                  | P3       |
| No request body size limit middleware         | Medium (relies on file validation) | P2       |
| Frontend uses `<img>` instead of `next/image` | Low (performance)                  | P3       |
| No database connection retry on startup       | Medium (startup race condition)    | P2       |

---

<p align="center">
  Built with ❤️ using FastAPI, Next.js, and Google Gemini<br/>
  <sub>Every file contains inline documentation following the what/why/how/when/where/who framework</sub>
</p>
