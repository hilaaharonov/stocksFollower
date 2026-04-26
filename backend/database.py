from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone

from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class WatchedStock(Base):
    __tablename__ = "watched_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active = Column(Boolean, default=True)


class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)
    symbol = Column(String(20), nullable=True)  # None means applies to all
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged = Column(Boolean, default=False)


class AiNote(Base):
    __tablename__ = "ai_notes"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    note = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
