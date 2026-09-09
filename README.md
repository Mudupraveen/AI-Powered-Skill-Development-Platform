# SkillForge AI: Adaptive Learning & Skill Development Platform

A fully functional, runnable AI-powered learning and skill development platform. The system conducts targeted skill assessments, detects learning gaps, dynamically generates personalized 4-week learning roadmaps using Anthropic Claude Sonnet 4.6 (prioritizing weak subtopics in Week 1), and provides an interactive "Ask a Doubt" AI tutor with direct follow-up quiz practice.

---

## Tech Stack

- **Backend**: FastAPI (Python 3.10+) with Pydantic validation & CORS
- **Database**: SQLite via SQLAlchemy (`skill_platform.db`, auto-created and seeded on first run)
- **Frontend**: React (Vite) + Tailwind CSS + Lucide Icons
- **AI Engine**: Anthropic Claude API (`claude-sonnet-4-6`) called via HTTPS with strict JSON validation, retry handling, and fallback resilience.

---

## Quick Start (Two-Command Launch)

### 1. Backend Setup & Startup

From the project root directory:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run backend API server
uvicorn main:app --reload
```
*(Alternative if uvicorn is not directly in your PATH: `python -m uvicorn main:app --reload`)*

The FastAPI backend will start at `http://127.0.0.1:8000`. On first run, it auto-creates SQLite database `skill_platform.db` and seeds the demo student with pre-populated SQL assessment results (40% score, weak subtopic: JOIN) and an initial roadmap.

Interactive API documentation is available at:
- **Swagger UI**: `http://127.0.0.1:8000/docs`

---

### 2. Frontend Setup & Startup

In a new terminal window in the project root directory:

```bash
# 1. Install frontend packages
npm install

# 2. Run Vite React development server
npm run dev
```

The frontend will start at `http://localhost:5173`. Open this URL in your web browser.

---

## Environment Configuration (.env)

Create or edit the `.env` file in the project root directory:

```env
# Anthropic Claude API Key (Required for live Claude Sonnet 4.6 responses)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

> **Note on Resilient Architecture**: If `ANTHROPIC_API_KEY` is not provided or invalid, the backend automatically uses an intelligent local domain generator so the entire application, assessment flow, and replanner can be demonstrated and verified with zero crashes or 500 errors. Once a valid key is saved in `.env`, the system seamlessly connects to `claude-sonnet-4-6`.

---

## Core Features & Architecture

### 1. Seed Data on Startup
- On first launch with an empty database, a **Demo Student** (`id=1`) is automatically created with:
  - Skill scores: Python (50%), SQL (40%, `needs_reinforcement=True`), HTML/CSS (50%), FastAPI (20%).
  - Prior quiz attempt on SQL with weak subtopic `"JOIN"`.
  - Initial 4-week roadmap with Week 1 dedicated to SQL JOINs reinforcement.

### 2. Assessment Agent (`POST /api/assess/{topic}`)
- Generates 4 diagnostic multiple choice questions for any technical topic.
- **Zero-Knowledge Security**: Correct answers are stored strictly on the server in SQLite (`active_quizzes` table) and are never exposed to the frontend prior to submission.

### 3. Server-Side Scoring & Reinforcement Logic (`POST /api/assess/{topic}/submit`)
- Evaluates student answers against server ground truth.
- If score is `< 50%` for a subtopic or overall topic, the backend automatically flags `needs_reinforcement = True` on the `SkillScore` record.
- Logs decision in the server terminal:
  `[ASSESSMENT AGENT] Topic: 'SQL' | Score: 1/4 (25%) | Weak Subtopics: ['JOIN'] | needs_reinforcement: True`

### 4. Planner Agent (`POST /api/roadmap/replan` & `GET /api/roadmap`)
- Checks for any `needs_reinforcement` flags first.
- If any exist, Week 1 of the 4-week plan **MUST** prioritize reinforcement on those weak subtopics before moving on.
- Visible terminal logging:
  `[PLANNER AGENT] Reinforcement required for: ['JOIN']. Prioritizing in Week 1.`

### 5. Ask a Doubt Tutor (`POST /api/ask`)
- Answers technical questions with clear conceptual explanations and code examples.
- Automatically detects relevant practice topics (`suggested_topic`) and provides a one-click button in the UI: **"Practice this topic: [Topic] -> Launch Quiz"**.

---

## API Contract Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/profile` | Updates student skill levels (`Beginner=20%`, `Intermediate=50%`, `Advanced=80%`) |
| `GET` | `/api/profile` | Fetches current student profile, scores, and reinforcement flags |
| `POST` | `/api/assess/{topic}` | Generates 4-question MCQ assessment (returns questions without answers) |
| `POST` | `/api/assess/{topic}/submit` | Scores assessment server-side, flags reinforcement if <50%, records attempt |
| `POST` | `/api/roadmap/replan` | Calls Planner Agent to generate/overwrite 4-week roadmap |
| `GET` | `/api/roadmap` | Returns current saved roadmap (auto-replanning if none exists) |
| `POST` | `/api/ask` | Answers technical queries and suggests related quiz topics |

---

## Automated Verification

To run the automated end-to-end integration test suite:

```bash
python test_flow.py
```
