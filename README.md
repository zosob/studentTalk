# StudentTalk

An AI-powered academic chatbot with early-warning wellbeing monitoring for undergraduate students.

Students ask questions about course material via a chat interface. Behind the scenes, every message is analysed for stress and confusion signals. When a student's wellbeing score drops below a threshold, the event is flagged and stored for faculty review.

---

## Architecture

```
Browser
  |
  |-- student.html  --WebSocket-->  /ws/{student_id}
  |                                       |
  `-- faculty.html  --POST------->  /upload_syllabus
                                   /uploadAssignment
                                   /wellbeing_dashboard
                                          |
                              +-----------.---------------+
                              v           v               v
                        Wellbeing    Ollama LLM      PostgreSQL
                        Monitor      (llama3.1:8b)   (or SQLite)
                              |                          |
                              `---- FlaggedEvent --------'
                                    Conversation
                                    Student
                                    Document
```

**Key components**

| File | Purpose |
|---|---|
| `main.py` | FastAPI app - routes, WebSocket handler, DB persistence |
| `database.py` | SQLAlchemy models and engine setup |
| `wellbeingMonitor.py` | VADER + TextBlob sentiment scoring, keyword detection |
| `courseKnowledgeBase.py` | FAISS vector index for semantic search over uploaded materials |
| `run_chatbot.py` | Startup script - installs deps, checks Ollama and DB, launches server |
| `static/` | HTML frontend (student chat, faculty upload) |

---

## Database Schema

```
students
  student_id   TEXT  PK
  course        TEXT
  enrolled_at   TIMESTAMP

conversations
  id             INT   PK
  student_id     TEXT  (FK -> students)
  timestamp      TIMESTAMP
  message        TEXT
  role           TEXT  ('user' | 'bot')
  wellbeing_score FLOAT

flagged_events
  id          INT   PK
  student_id  TEXT  (FK -> students)
  timestamp   TIMESTAMP
  reason      TEXT  (e.g. "stress_indicators=3, confusion_indicators=1")
  severity    FLOAT (0-10, higher = more severe)
  reviewed    BOOL

documents
  id            INT   PK
  filename      TEXT
  course_id     TEXT  (null until multi-tenant support is added)
  uploaded_at   TIMESTAMP
  content_hash  TEXT  (SHA-256 of extracted text)
```

Tables are created automatically on startup if they do not exist.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Tested on 3.11 |
| [Ollama](https://ollama.com) | Must be running locally with `llama3.1:8b` pulled |
| PostgreSQL 14+ | Optional - SQLite is used automatically if `DATABASE_URL` is not set |
| conda (recommended) | Environment name `student-chatbot` |

---

## Setup

### 1. Create and activate the conda environment

```bash
conda create -n student-chatbot python=3.11
conda activate student-chatbot
```

### 2. Install dependencies

```bash
pip install fastapi "uvicorn[standard]" websockets sentence-transformers \
    textblob vaderSentiment PyPDF2 faiss-cpu ollama python-multipart \
    sqlalchemy psycopg2-binary python-dotenv python-docx
```

Or let the startup script handle it:

```bash
python run_chatbot.py
```

### 3. Configure the database

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

**.env** (PostgreSQL):
```
DATABASE_URL=postgresql://user:password@localhost:5432/studenttalk
```

**.env** (SQLite - no setup needed, good for local dev):
```
# leave DATABASE_URL unset, or:
DATABASE_URL=sqlite:///./studenttalk.db
```

Create the PostgreSQL database if you haven't already:

```bash
createdb studenttalk
```

Tables are created automatically when the app starts.

### 4. Start Ollama

```bash
ollama serve
ollama pull llama3.1:8b
```

### 5. Run the server

```bash
python run_chatbot.py
# or directly:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/static/student.html` | Student chat UI |
| `GET` | `/static/faculty.html` | Faculty upload UI |
| `POST` | `/upload_syllabus` | Upload a syllabus (PDF / DOCX / TXT) |
| `POST` | `/uploadAssignment` | Upload an assignment document |
| `GET` | `/wellbeing_dashboard` | JSON summary of flags and per-student stats |
| `WS` | `/ws/{student_id}` | Real-time chat for a student |

### WebSocket message format

**Client -> Server**
```json
{ "message": "I'm really struggling with pointers" }
```

**Server -> Client**
```json
{
  "message": "Let's break pointers down step by step...",
  "wellbeing_score": 4.2,
  "flagged": false
}
```

### Wellbeing dashboard response

```json
{
  "total_flags": 12,
  "recent_flags": [
    {
      "id": 7,
      "student_id": "student_abc123",
      "timestamp": "2026-03-30T14:22:00",
      "reason": "stress_indicators=3, confusion_indicators=2",
      "severity": 8.1,
      "reviewed": false
    }
  ],
  "student_summary": {
    "student_abc123": {
      "flag_count": 3,
      "last_flagged": "2026-03-30T14:22:00",
      "reviewed_count": 1
    }
  }
}
```

---

## Wellbeing Scoring

Each student message is scored 0-10 (lower = more concerning):

```
score = 5
      + (vader_compound + 1) x 2.5   # sentiment: scales [-1,1] to [0,5]
      - stress_keyword_count  x 1.5
      - confusion_keyword_count x 0.5
```

A `FlaggedEvent` is written to the database when `score < 3.0` or `stress_keywords > 2`.

---

## Roadmap

- **User Authentication** - JWT-based login; faculty and student roles; protect `/wellbeing_dashboard` behind faculty auth
- **Wellbeing Dashboard UI** - Timeline of flags per student, sentiment trend graphs, weekly summary view
- **Multi-tenant / Course Support** - Scope uploaded documents to a `course_id` so different courses get different RAG context
- **Alembic Migrations** - Schema version control as the DB evolves
