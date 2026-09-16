# FacultyTwin

FacultyTwin is a course-grounded AI teaching assistant: it answers student
questions using a professor's own syllabus and course materials (RAG over
uploaded PDFs/docs), flags signs of student stress or confusion during
conversations, and gives faculty a weekly digest of engagement and wellbeing
trends. It's designed to run locally with Ollama so student data never
leaves the institution.

This repo is the open-source release referenced in our grant proposal's
Outcomes section — released for peer adoption and community-led iteration.

## Features

- **Course knowledge base** (`courseKnowledgeBase.py`) — RAG over uploaded
  syllabi/assignments (PDF, DOCX, TXT) using sentence-transformer embeddings
  and a FAISS index.
- **Chat interface** — a WebSocket endpoint (`main.py`) plus a static web
  frontend, and a **Discord bot** (`discordBot.py`) so students can reach
  the assistant where they already are.
- **Wellbeing monitoring** (`wellbeingMonitor.py`) — sentiment analysis
  (VADER + TextBlob) and stress/confusion keyword detection on every
  message, producing a 0–10 wellbeing score and flagging concerning
  messages for review.
- **Deadline nudges** (`nudgeEngine.py`) — students opt in via Discord;
  the bot DMs a reminder at 24 hours and 2 hours before a registered
  assignment deadline.
- **Faculty digest** (`facultyDigest.py`) — a weekly, per-student summary
  of message volume, average wellbeing score, and flags, available at
  `GET /faculty_digest`.

## Architecture

```
Student ──► Discord bot (discordBot.py) ─┐
                                          ├─► main.py (FastAPI)
Student ──► Web widget (static/) ────────┘        │
                                                    ├─► courseKnowledgeBase.py (RAG / FAISS)
                                                    ├─► wellbeingMonitor.py (sentiment)
                                                    ├─► nudgeEngine.py (deadline reminders)
                                                    ├─► facultyDigest.py (weekly report)
                                                    └─► Ollama (llama3.1:8b, local)
```

Storage is currently in-memory (see the `# In-memory storage` comment in
`main.py`); a PostgreSQL layer is the next planned step so history survives
restarts.

## Setup

### 1. Install Ollama and pull the model

```bash
# https://ollama.com
ollama serve
ollama pull llama3.1:8b
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or use the guided setup script, which checks Ollama and installs packages
for you:

```bash
python run_chatbot.py
```

### 3. Run the server

```bash
python main.py
```

- Chat widget: http://localhost:8000
- Faculty wellbeing dashboard: http://localhost:8000/wellbeing_dashboard
- Faculty weekly digest: http://localhost:8000/faculty_digest

### 4. (Optional) Run the Discord bot

1. Create a bot at the [Discord Developer Portal](https://discord.com/developers/applications),
   enable the **Message Content Intent**, and invite it to your server.
2. Export the token and start the bot alongside the server:

   ```bash
   export DISCORD_BOT_TOKEN=your-token-here
   python discordBot.py
   ```

3. In Discord: `!ask <question>`, `!subscribe_nudges` / `!unsubscribe_nudges`
   for deadline reminders.

### 5. Register assignment deadlines (for nudges)

```bash
curl -X POST http://localhost:8000/deadlines \
  -H "Content-Type: application/json" \
  -d '{"assignment_id": "hw3", "course": "CS 201", "title": "Homework 3", "due": "2026-10-01T23:59:00"}'
```

## Privacy

All processing runs locally via Ollama by default — no student message
content is sent to a third-party API. Wellbeing flags are stored in-memory
for faculty review and are not shared outside the course context. See the
grant proposal for the full data-handling and opt-in participation plan.

## Roadmap

- [ ] Persist chat history, flags, and deadlines to PostgreSQL
- [ ] Faculty authentication for the dashboard/digest endpoints
- [ ] Course-scoped (multi-tenant) knowledge bases
- [ ] Pilot evaluation + published outcome metrics (see grant Outcomes)

## License

MIT — see [LICENSE](LICENSE).

## Citing this project

A peer-reviewed writeup and conference presentation are planned as part of
the funded pilot; citation details will be added here once published.