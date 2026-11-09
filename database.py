import hashlib
import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./studenttalk.db")

# sqlite needs check_same_thread=False; postgres does not accept that arg
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Student(Base):
    __tablename__ = "students"

    student_id = Column(String, primary_key=True, index=True)
    course = Column(String, nullable=True)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    message = Column(Text, nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'bot'
    wellbeing_score = Column(Float, nullable=True)


class FlaggedEvent(Base):
    __tablename__ = "flagged_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    reason = Column(Text, nullable=False)
    severity = Column(Float, nullable=False)  # 0-10, higher = more severe
    reviewed = Column(Boolean, default=False, nullable=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    course_id = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    content_hash = Column(String, nullable=False)


def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
