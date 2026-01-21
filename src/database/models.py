from sqlalchemy import BigInteger, String, Boolean, DateTime, Enum, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func 
from src.database.database import Base

import enum

class UserStatus(enum.Enum):
    new="New"
    questionnaire_completed = "questionnaire_completed"
    approved = "approved"
    rejected = "rejected"
    member = "member"

class User(Base):
    tablename = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    fullname: Mapped[str | None] = mapped_column(String(128))

    status: Mapped[UserStatus]=mapped_column(Enum(UserStatus), default=UserStatus.new)
    create_at: Mapped[DateTime]=mapped_column(DateTime(timezone=True),server_default=func.now)

    questionnaire=relationship("Questionnaire", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")

class QuestionnaireStatus(enum.Enum):
    pending = "Pending"
    approved = "approved"
    rejected = "rejected"

class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    status: Mapped[QuestionnaireStatus] = mapped_column(enum(QuestionnaireStatus),default=QuestionnaireStatus.pending)
    create_at: Mapped[DateTime]=mapped_column(DateTime(timezone=True),server_default=func.now)

    user = relationship("User", back_populates="questionnaires")
    answer = relationship("Answer",back_populates="questionnaires")

class QuestionType(enum.Enum):
    text = "text"
    number = "number"
    choice = "choice"


class Question(Base):
    tablename = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    text: Mapped[str] = mapped_column(Text)
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer)

    answers = relationship("Answer", back_populates="question")


class Answer(Base):
    tablename = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)

    questionnaire_id: Mapped[int] = mapped_column(
        ForeignKey("questionnaires.id", ondelete="CASCADE")
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE")
    )

    answer_text: Mapped[str] = mapped_column(Text)

    questionnaire = relationship("Questionnaire", back_populates="answers")
    question = relationship("Question", back_populates="answers")

class Tariff(Base):
    tablename = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(64))
    price: Mapped[int] = mapped_column(Integer)  # в копейках
    duration_days: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions = relationship("Subscription", back_populates="tariff")

class Subscription(Base):
    tablename = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    tariff_id: Mapped[int] = mapped_column(
        ForeignKey("tariffs.id")
    )

    start_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")
    tariff = relationship("Tariff", back_populates="subscriptions")