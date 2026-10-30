import enum
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, UniqueConstraint, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class JobStatus(enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ItemStatus(enum.Enum):
    PENDING = "pending"
    CREATED = "created"
    FAILED = "failed"


class Base(DeclarativeBase):
    pass


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    settings: Mapped[dict] = mapped_column(JSON)  # Словарь с настройками кампании
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class LaunchJob(Base):
    __tablename__ = "launch_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"))
    count: Mapped[int]  # количество кампаний для запуска
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.QUEUED)


class LaunchItem(Base):
    __tablename__ = "launch_items"
    __table_args__ = (UniqueConstraint("job_id", "index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("launch_jobs.id"))
    index: Mapped[int]  # индекс в списке кампаний
    status: Mapped[ItemStatus] = mapped_column(default=ItemStatus.PENDING)
    external_campaign_id: Mapped[str | None]  # ID кампании на платформе
    error_message: Mapped[str | None]  # сообщение об ошибке, если статус "failed"
    attempts: Mapped[int] = mapped_column(default=0)  # количество попыток запуска

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str]

class TikTokOAuthState(Base):
    __tablename__ = "tiktok_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))