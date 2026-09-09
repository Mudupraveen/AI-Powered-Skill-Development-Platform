import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from models import Student, SkillScore, QuizAttempt, RoadmapWeek

logger = logging.getLogger("seed")


def seed_database_if_empty(db: Session):
    """
    Checks if the database is empty and seeds a demo student with a pre-filled
    profile, one prior quiz attempt (SQL 40%, weak_subtopic="JOIN"),
    and a generated 4-week roadmap prioritizing Week 1 reinforcement.
    """
    student_count = db.query(Student).count()
    if student_count > 0:
        logger.info("[SEED] Database already populated with students. Skipping seed.")
        return

    logger.info("[SEED] Empty database detected. Seeding Demo Student and initial data...")

    # 1. Create Demo Student
    student = Student(id=1, name="Demo Student", created_at=datetime.utcnow())
    db.add(student)
    db.flush()

    # 2. Seed Initial Skill Scores
    # SQL is scored 40% with needs_reinforcement=True as required
    skills = [
        {"topic": "Python", "score_percent": 50, "needs_reinforcement": False},
        {"topic": "SQL", "score_percent": 40, "needs_reinforcement": True},
        {"topic": "HTML/CSS", "score_percent": 50, "needs_reinforcement": False},
        {"topic": "FastAPI", "score_percent": 20, "needs_reinforcement": False},
    ]

    for s in skills:
        skill_score = SkillScore(
            student_id=student.id,
            topic=s["topic"],
            score_percent=s["score_percent"],
            needs_reinforcement=s["needs_reinforcement"],
            last_updated=datetime.utcnow()
        )
        db.add(skill_score)

    # 3. Seed Prior Quiz Attempt (SQL, scored 40%, weak_subtopic="JOIN")
    demo_questions = [
        {
            "id": "q1",
            "text": "Which SQL JOIN returns all rows from the left table, and matched rows from the right table?",
            "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"],
            "correct_answer": "LEFT JOIN",
            "topic_tag": "SQL: JOIN",
            "subtopic": "JOIN"
        },
        {
            "id": "q2",
            "text": "How do you combine results from two tables where there is a match in BOTH tables?",
            "options": ["CROSS JOIN", "OUTER JOIN", "INNER JOIN", "UNION ALL"],
            "correct_answer": "INNER JOIN",
            "topic_tag": "SQL: JOIN",
            "subtopic": "JOIN"
        }
    ]
    demo_answers = {"q1": "INNER JOIN", "q2": "INNER JOIN"}

    quiz_attempt = QuizAttempt(
        student_id=student.id,
        topic="SQL",
        questions_json=json.dumps(demo_questions),
        answers_json=json.dumps(demo_answers),
        score=40,
        weak_subtopics_json=json.dumps(["JOIN"]),
        created_at=datetime.utcnow()
    )
    db.add(quiz_attempt)

    # 4. Seed 4-Week Roadmap with Week 1 prioritizing JOIN reinforcement
    roadmap_weeks = [
        RoadmapWeek(
            student_id=student.id,
            week_number=1,
            topics_json=json.dumps(["SQL JOINs Reinforcement", "Advanced Multi-Table Filtering"]),
            reason_text="The following subtopics scored below 50% and need reinforcement before moving on: [JOIN]. Prioritizing these in Week 1.",
            created_at=datetime.utcnow()
        ),
        RoadmapWeek(
            student_id=student.id,
            week_number=2,
            topics_json=json.dumps(["FastAPI Fundamentals & Routing", "Pydantic Request Schemas"]),
            reason_text="Building backend REST API skills from beginner foundation.",
            created_at=datetime.utcnow()
        ),
        RoadmapWeek(
            student_id=student.id,
            week_number=3,
            topics_json=json.dumps(["Python Async & Database Integration", "SQLAlchemy ORM Relationships"]),
            reason_text="Connecting Python services with SQL relational models for full-stack data persistence.",
            created_at=datetime.utcnow()
        ),
        RoadmapWeek(
            student_id=student.id,
            week_number=4,
            topics_json=json.dumps(["HTML/CSS Modern Layouts (Flexbox/Grid)", "Full-Stack End-to-End Integration"]),
            reason_text="Polishing user experience and completing cohesive end-to-end full-stack workflows.",
            created_at=datetime.utcnow()
        )
    ]

    for rw in roadmap_weeks:
        db.add(rw)

    db.commit()
    print("[SEED] Auto-created Demo Student with SQL 40% (weak_subtopic='JOIN', needs_reinforcement=True) and initial roadmap.")
    logger.info("[SEED] Auto-created Demo Student with SQL 40% (weak_subtopic='JOIN', needs_reinforcement=True) and initial roadmap.")
