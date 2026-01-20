from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum
import datetime

Base = declarative_base()

class ApplicationStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)
    tariff = Column(String, default=None)
    subscription_end = Column(DateTime, default=None)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
