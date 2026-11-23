
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from backend.database import Base


class QuizHistory(Base):
    __tablename__ = "quiz_history"

    id = Column(Integer, primary_key=True, index=True)

    pdf_name = Column(String, nullable=True)

    total_questions = Column(Integer, nullable=False)

    correct_answers = Column(Integer, nullable=False)

    score_percentage = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
