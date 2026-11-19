# pyright: reportMissingImports=false
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now():
    return datetime.now(timezone.utc)


def pk():
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def user_fk():
    return mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)


def scan_fk(primary=False):
    return mapped_column(Uuid, ForeignKey("scans.id", ondelete="CASCADE"), primary_key=primary, index=not primary)


def ts():
    return mapped_column(DateTime(timezone=True), default=now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = ts()
    scans: Mapped[list["Scan"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    """One row per issued refresh token (stored as a SHA-256 hash)."""
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = ts()


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = ts()


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (Index("ix_scans_user_created", "user_id", "created_at"),)
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    scan_type: Mapped[str] = mapped_column(String(16))  # website|email|message|qr|file|phone
    input_summary: Mapped[str] = mapped_column(String(500))
    label: Mapped[str] = mapped_column(String(24))
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="completed", server_default="completed")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts()
    user: Mapped[User] = relationship(back_populates="scans")


class WebsiteScan(Base):
    __tablename__ = "website_scans"
    scan_id: Mapped[uuid.UUID] = scan_fk(True)
    url: Mapped[str] = mapped_column(Text)
    features: Mapped[dict] = mapped_column(JSON, default=dict)


class EmailScan(Base):
    __tablename__ = "email_scans"
    scan_id: Mapped[uuid.UUID] = scan_fk(True)
    sender: Mapped[str] = mapped_column(String(320), default="")
    subject: Mapped[str] = mapped_column(String(500), default="")
    body_excerpt: Mapped[str] = mapped_column(Text, default="")


class MessageScan(Base):
    __tablename__ = "message_scans"
    scan_id: Mapped[uuid.UUID] = scan_fk(True)
    platform: Mapped[str] = mapped_column(String(32), default="sms")
    text: Mapped[str] = mapped_column(Text)


class QrScan(Base):
    __tablename__ = "qr_scans"
    scan_id: Mapped[uuid.UUID] = scan_fk(True)
    decoded_url: Mapped[str] = mapped_column(Text)


class FileScan(Base):
    __tablename__ = "file_scans"
    scan_id: Mapped[uuid.UUID] = scan_fk(True)
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))


class PhoneReport(Base):
    __tablename__ = "phone_reports"
    id: Mapped[uuid.UUID] = pk()
    number: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(48))
    reported_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = ts()


class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"
    id: Mapped[uuid.UUID] = pk()
    scan_id: Mapped[uuid.UUID] = scan_fk()
    name: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(10))
    weight: Mapped[float] = mapped_column(Float)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    id: Mapped[uuid.UUID] = pk()
    scan_id: Mapped[uuid.UUID] = scan_fk()
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(32))
    probability: Mapped[float] = mapped_column(Float)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = ts()
