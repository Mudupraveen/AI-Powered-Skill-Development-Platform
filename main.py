import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, Base, get_db, SessionLocal
import models
from seed import seed_database_if_empty
import ai_service

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and auto-seed if empty
    logger.info("[STARTUP] Initializing SQLite database and checking seed state...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()
    yield
    # Shutdown
    logger.info("[SHUTDOWN] Application shutting down.")


app = FastAPI(
    title="AI-Powered Skill Development Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# Explicit CORS configuration for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# PYDANTIC SCHEMAS
# ==============================================================================

class ProfileRequest(BaseModel):
    skills: Dict[str, str]  # e.g. {"Python": "Beginner", "SQL": "Intermediate"}


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: Dict[str, str]  # e.g. {"q1": "Selected Answer Text"}


class AskRequest(BaseModel):
    question: str


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AI-Powered Learning & Skill Development Platform",
        "docs_url": "/docs"
    }


@app.get("/api/profile")
def get_profile(db: Session = Depends(get_db)):
    """
    Returns current student profile, skills, scores, and needs_reinforcement flags.
    """
    student = db.query(models.Student).first()
    if not student:
        raise HTTPException(status_code=404, detail="No student profile found")

    skill_scores = db.query(models.SkillScore).filter_by(student_id=student.id).all()
    skills_dict = {}
    for s in skill_scores:
        # Determine rating label based on percentage
        rating = "Beginner"
        if s.score_percent >= 75:
            rating = "Advanced"
        elif s.score_percent >= 45:
            rating = "Intermediate"

        skills_dict[s.topic] = {
            "score_percent": s.score_percent,
            "needs_reinforcement": s.needs_reinforcement,
            "rating": rating,
            "last_updated": s.last_updated.isoformat() if s.last_updated else None
        }

    return {
        "student_id": student.id,
        "name": student.name,
        "skills": skills_dict
    }


@app.post("/api/profile")
def update_profile(payload: ProfileRequest, db: Session = Depends(get_db)):
    """
    POST /api/profile
    body: { "skills": { "Python": "Beginner", "SQL": "Beginner", "HTML/CSS": "Intermediate", "FastAPI": "Beginner" } }
    -> creates/updates Student + initial SkillScore rows (map Beginner=20%, Intermediate=50%, Advanced=80%)
    -> returns { "student_id": int, "skills": {...} }
    """
    student = db.query(models.Student).first()
    if not student:
        student = models.Student(name="Demo Student", created_at=datetime.utcnow())
        db.add(student)
        db.flush()

    rating_map = {
        "beginner": 20,
        "intermediate": 50,
        "advanced": 80
    }

    result_skills = {}

    for topic, rating_str in payload.skills.items():
        percent = rating_map.get(str(rating_str).strip().lower(), 20)
        # Check if SkillScore exists
        skill_score = db.query(models.SkillScore).filter_by(student_id=student.id, topic=topic).first()
        if not skill_score:
            skill_score = models.SkillScore(
                student_id=student.id,
                topic=topic,
                score_percent=percent,
                needs_reinforcement=(percent < 50),
                last_updated=datetime.utcnow()
            )
            db.add(skill_score)
        else:
            skill_score.score_percent = percent
            skill_score.needs_reinforcement = (percent < 50)
            skill_score.last_updated = datetime.utcnow()

        result_skills[topic] = rating_str

    db.commit()
    return {
        "student_id": student.id,
        "skills": result_skills
    }


@app.post("/api/assess/{topic}")
async def create_assessment(topic: str, db: Session = Depends(get_db)):
    """
    POST /api/assess/{topic}
    -> calls Assessment Agent, generates 4 MCQ questions for that topic
    -> returns { "quiz_id": string, "questions": [ { "id", "text", "options": ["a","b","c","d"], "topic_tag" } ] }
       (correct answers stored server-side ONLY, never sent to frontend)
    """
    try:
        generated = await ai_service.generate_assessment_quiz(topic)
    except Exception as e:
        logger.error(f"Failed to generate assessment for {topic}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not generate assessment for topic '{topic}'. Please retry."
        )

    # Store correct answers and explanations on server only
    active_quiz = models.ActiveQuiz(
        id=generated["quiz_id"],
        topic=topic,
        questions_json=json.dumps(generated["server_data"]),
        created_at=datetime.utcnow()
    )
    db.add(active_quiz)
    db.commit()

    return {
        "quiz_id": generated["quiz_id"],
        "questions": generated["questions"]
    }


@app.post("/api/assess/{topic}/submit")
async def submit_assessment(topic: str, payload: QuizSubmitRequest, db: Session = Depends(get_db)):
    """
    POST /api/assess/{topic}/submit
    body: { "quiz_id": string, "answers": { "q_id": "selected_option" } }
    -> scores server-side, returns { "score": int, "total": int, "weak_subtopics": [string], "explanations": { "q_id": string } }
    -> also updates SkillScore for that topic in DB
    AGENT LOGIC:
    - If score_percent < 50 for a subtopic or overall, set 'needs_reinforcement' flag on that SkillScore row
    """
    active_quiz = db.query(models.ActiveQuiz).filter_by(id=payload.quiz_id).first()
    if not active_quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz session expired or not found. Please start a new assessment."
        )

    server_questions = json.loads(active_quiz.questions_json)
    total_questions = len(server_questions)
    correct_count = 0
    weak_subtopics_set = set()
    explanations = {}

    subtopic_stats = {}  # { subtopic: {"correct": int, "total": int} }

    for q in server_questions:
        qid = q["id"]
        correct_answer = str(q.get("correct_answer", "")).strip().lower()
        submitted_answer = str(payload.answers.get(qid, "")).strip().lower()
        subtopic = q.get("subtopic") or q.get("topic_tag") or topic
        explanations[qid] = q.get("explanation", "Correct answer is: " + q.get("correct_answer", ""))

        if subtopic not in subtopic_stats:
            subtopic_stats[subtopic] = {"correct": 0, "total": 0}
        subtopic_stats[subtopic]["total"] += 1

        # Check if match (flexible for option text or choice letter)
        if submitted_answer and (
            submitted_answer == correct_answer or
            submitted_answer in correct_answer or
            correct_answer in submitted_answer
        ):
            correct_count += 1
            subtopic_stats[subtopic]["correct"] += 1
        else:
            weak_subtopics_set.add(subtopic)

    # Check for subtopics scoring < 50%
    subtopics_under_50 = []
    for sub, stats in subtopic_stats.items():
        pct = (stats["correct"] / stats["total"]) * 100
        if pct < 50:
            subtopics_under_50.append(sub)
            weak_subtopics_set.add(sub)

    score_percent = int(round((correct_count / total_questions) * 100)) if total_questions > 0 else 0
    weak_subtopics_list = list(weak_subtopics_set)
    passed = (score_percent >= 50 and len(subtopics_under_50) == 0)
    needs_reinforcement = not passed

    # Student lookup
    student = db.query(models.Student).first()
    if not student:
        student = models.Student(name="Demo Student")
        db.add(student)
        db.flush()

    # Update or insert SkillScore
    skill_score = db.query(models.SkillScore).filter_by(student_id=student.id, topic=topic).first()
    if not skill_score:
        skill_score = models.SkillScore(
            student_id=student.id,
            topic=topic,
            score_percent=score_percent,
            needs_reinforcement=needs_reinforcement,
            last_updated=datetime.utcnow()
        )
        db.add(skill_score)
    else:
        skill_score.score_percent = score_percent
        skill_score.needs_reinforcement = needs_reinforcement
        skill_score.last_updated = datetime.utcnow()

    # Record QuizAttempt
    quiz_attempt = models.QuizAttempt(
        student_id=student.id,
        topic=topic,
        questions_json=active_quiz.questions_json,
        answers_json=json.dumps(payload.answers),
        score=score_percent,
        weak_subtopics_json=json.dumps(weak_subtopics_list),
        created_at=datetime.utcnow()
    )
    db.add(quiz_attempt)
    db.commit()

    # ONLY WHEN STUDENT FAILS EXAM: Generate / update preparation roadmap
    preparation_roadmap_given = False
    if not passed:
        # Student failed: generate preparation roadmap
        print(f"[ASSESSMENT AGENT] Exam FAILED for '{topic}' (Score: {score_percent}% < 50%). Generating preparation roadmap.")
        logger.info(f"[ASSESSMENT AGENT] Exam FAILED for '{topic}' (Score: {score_percent}% < 50%). Generating preparation roadmap.")
        
        skills_map = {s.topic: s.score_percent for s in db.query(models.SkillScore).filter_by(student_id=student.id).all()}
        reinforce_topics = [s.topic for s in db.query(models.SkillScore).filter_by(student_id=student.id).all() if s.needs_reinforcement]
        
        # Overwrite previous plan in RoadmapWeek table with targeted preparation plan
        try:
            weeks_plan = await ai_service.generate_roadmap_plan(
                student_skills=skills_map,
                weak_subtopics=weak_subtopics_list,
                reinforce_topics=reinforce_topics or [topic]
            )
            db.query(models.RoadmapWeek).filter_by(student_id=student.id).delete()
            for w_data in weeks_plan:
                week_record = models.RoadmapWeek(
                    student_id=student.id,
                    week_number=w_data.get("week", 1),
                    topics_json=json.dumps(w_data.get("topics", [])),
                    reason_text=w_data.get("reason", "Tailored step for skill progression."),
                    created_at=datetime.utcnow()
                )
                db.add(week_record)
            db.commit()
            preparation_roadmap_given = True
        except Exception as e:
            logger.error(f"Error generating preparation roadmap: {e}")
    else:
        # Student passed: check if there are other topics needing reinforcement
        other_reinforcements = [
            s.topic for s in db.query(models.SkillScore).filter_by(student_id=student.id).all()
            if s.needs_reinforcement and s.topic != topic
        ]
        if not other_reinforcements:
            # Student has cleared all exams, remove any previous preparation roadmap
            db.query(models.RoadmapWeek).filter_by(student_id=student.id).delete()
            db.commit()
            preparation_roadmap_given = False
        else:
            preparation_roadmap_given = True
        print(f"[ASSESSMENT AGENT] Exam PASSED for '{topic}' (Score: {score_percent}% >= 50%). No new preparation roadmap needed.")
        logger.info(f"[ASSESSMENT AGENT] Exam PASSED for '{topic}' (Score: {score_percent}% >= 50%). No new preparation roadmap needed.")

    message = (
        f"Assessment not cleared ({score_percent}%). A 4-week preparation roadmap has been generated to reinforce weak areas before retaking."
        if not passed else
        f"Congratulations! You passed the {topic} assessment ({score_percent}%). No preparation roadmap is required."
    )

    return {
        "score": correct_count,
        "total": total_questions,
        "score_percent": score_percent,
        "passed": passed,
        "status": "passed" if passed else "failed",
        "weak_subtopics": weak_subtopics_list,
        "explanations": explanations,
        "preparation_roadmap_given": preparation_roadmap_given,
        "message": message
    }


@app.post("/api/roadmap/replan")
async def replan_roadmap(db: Session = Depends(get_db)):
    """
    POST /api/roadmap/replan
    -> ONLY generates preparation roadmap if student has failed an exam (<50% score or needs_reinforcement).
    -> If no exam is failed, returns empty weeks and confirms no preparation roadmap is needed.
    """
    student = db.query(models.Student).first()
    if not student:
        student = models.Student(name="Demo Student")
        db.add(student)
        db.flush()

    # Query skills & reinforcement flags
    skill_scores = db.query(models.SkillScore).filter_by(student_id=student.id).all()
    skills_map = {s.topic: s.score_percent for s in skill_scores}
    reinforce_topics = [s.topic for s in skill_scores if s.needs_reinforcement]

    # Check if student has any failed attempts (<50%)
    failed_attempts = (
        db.query(models.QuizAttempt)
        .filter_by(student_id=student.id)
        .filter(models.QuizAttempt.score < 50)
        .all()
    )

    has_failed_exam = bool(reinforce_topics or failed_attempts)

    if not has_failed_exam:
        # Rule: ONLY when student fails exam give preparation roadmap!
        logger.info("[PLANNER AGENT] Student has not failed any exam. Clearing preparation roadmap.")
        db.query(models.RoadmapWeek).filter_by(student_id=student.id).delete()
        db.commit()
        return {
            "has_failed_exam": False,
            "weeks": [],
            "message": "No preparation roadmap required. Preparation roadmaps are only provided when an exam is failed (<50%)."
        }

    # Retrieve weak subtopics from recent quiz attempts
    recent_attempts = (
        db.query(models.QuizAttempt)
        .filter_by(student_id=student.id)
        .order_by(models.QuizAttempt.created_at.desc())
        .limit(5)
        .all()
    )
    weak_subtopics_all = []
    for att in recent_attempts:
        try:
            weaks = json.loads(att.weak_subtopics_json)
            weak_subtopics_all.extend(weaks)
        except Exception:
            pass

    unique_weaks = list(dict.fromkeys(weak_subtopics_all))

    # Generate targeted preparation roadmap for failed exam
    weeks_plan = await ai_service.generate_roadmap_plan(
        student_skills=skills_map,
        weak_subtopics=unique_weaks,
        reinforce_topics=reinforce_topics or list(dict.fromkeys(a.topic for a in failed_attempts))
    )

    # Overwrite previous plan in RoadmapWeek table
    db.query(models.RoadmapWeek).filter_by(student_id=student.id).delete()

    for w_data in weeks_plan:
        week_record = models.RoadmapWeek(
            student_id=student.id,
            week_number=w_data.get("week", 1),
            topics_json=json.dumps(w_data.get("topics", [])),
            reason_text=w_data.get("reason", "Tailored step for skill progression."),
            created_at=datetime.utcnow()
        )
        db.add(week_record)

    db.commit()

    return {
        "has_failed_exam": True,
        "failed_topics": reinforce_topics or list(dict.fromkeys(a.topic for a in failed_attempts)),
        "message": "Preparation roadmap provided for failed exam remediation.",
        "weeks": weeks_plan
    }


@app.get("/api/roadmap")
async def get_roadmap(db: Session = Depends(get_db)):
    """
    GET /api/roadmap
    -> returns current saved preparation roadmap ONLY if student has failed an exam.
    -> If student has not failed any exam, returns empty weeks with clear message.
    """
    student = db.query(models.Student).first()
    if not student:
        student = models.Student(name="Demo Student")
        db.add(student)
        db.flush()

    skill_scores = db.query(models.SkillScore).filter_by(student_id=student.id).all()
    reinforce_topics = [s.topic for s in skill_scores if s.needs_reinforcement]
    failed_attempts = (
        db.query(models.QuizAttempt)
        .filter_by(student_id=student.id)
        .filter(models.QuizAttempt.score < 50)
        .all()
    )
    has_failed_exam = bool(reinforce_topics or failed_attempts)

    if not has_failed_exam:
        # Clean up any leftover weeks
        db.query(models.RoadmapWeek).filter_by(student_id=student.id).delete()
        db.commit()
        return {
            "has_failed_exam": False,
            "weeks": [],
            "message": "No preparation roadmap required. Preparation roadmaps are only provided when an exam is failed (<50%)."
        }

    saved_weeks = (
        db.query(models.RoadmapWeek)
        .filter_by(student_id=student.id)
        .order_by(models.RoadmapWeek.week_number.asc())
        .all()
    )

    if not saved_weeks:
        logger.info("[ROADMAP] Student failed exam but no roadmap saved. Auto-triggering replan...")
        replan_res = await replan_roadmap(db=db)
        return replan_res

    weeks = []
    for w in saved_weeks:
        try:
            topics = json.loads(w.topics_json)
        except Exception:
            topics = []
        weeks.append({
            "week": w.week_number,
            "topics": topics,
            "reason": w.reason_text
        })

    return {
        "has_failed_exam": True,
        "failed_topics": reinforce_topics or list(dict.fromkeys(a.topic for a in failed_attempts)),
        "weeks": weeks
    }


@app.post("/api/ask")
async def ask_doubt(payload: AskRequest):
    """
    POST /api/ask
    body: { "question": string }
    -> returns { "answer": string, "suggested_topic": string | null }
       (suggested_topic lets frontend show a "Practice this" button)
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty."
        )

    res = await ai_service.answer_student_doubt(payload.question.strip())
    return res
