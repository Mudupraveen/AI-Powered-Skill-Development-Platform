from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="Demo Student")
    created_at = Column(DateTime, default=datetime.utcnow)

    skill_scores = relationship("SkillScore", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    roadmap_weeks = relationship("RoadmapWeek", back_populates="student", cascade="all, delete-orphan")


class SkillScore(Base):
    __tablename__ = "skill_scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    topic = Column(String(100), nullable=False, index=True)
    score_percent = Column(Integer, default=20)
    needs_reinforcement = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="skill_scores")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    topic = Column(String(100), nullable=False)
    questions_json = Column(Text, nullable=False)  # JSON serialized questions
    answers_json = Column(Text, nullable=False)    # JSON serialized student answers
    score = Column(Integer, nullable=False)
    weak_subtopics_json = Column(Text, default="[]") # JSON list of weak subtopic strings
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="quiz_attempts")


class RoadmapWeek(Base):
    __tablename__ = "roadmap_weeks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False)
    topics_json = Column(Text, nullable=False)      # JSON list of topic strings
    reason_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="roadmap_weeks")


class ActiveQuiz(Base):
    """
    Stores generated quiz data server-side so correct answers and explanations
    are never exposed to the client prior to quiz submission.
    """
    __tablename__ = "active_quizzes"

    id = Column(String(64), primary_key=True, index=True)
    topic = Column(String(100), nullable=False)
    questions_json = Column(Text, nullable=False)  # Contains questions with answers and explanations
    created_at = Column(DateTime, default=datetime.utcnow)
