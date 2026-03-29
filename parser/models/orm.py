"""SQLAlchemy 2.x ORM models."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BIGINT,
    CHAR,
    INT,
    TEXT,
    VARCHAR,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _engine():
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "novel_db")
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASS", "")
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, echo=False)


engine = _engine()


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_site: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    source_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500))
    title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    category: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    summary: Mapped[Optional[str]] = mapped_column(TEXT)
    chapter_count: Mapped[Optional[int]] = mapped_column(Integer)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    detected_encoding: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    parse_status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "success", "failed"),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    total_words: Mapped[Optional[int]] = mapped_column(Integer)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="book", cascade="all, delete-orphan"
    )
    parse_logs: Mapped[list["ParseLog"]] = relationship(
        "ParseLog", back_populates="book"
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    chapter_num: Mapped[int] = mapped_column(Integer, nullable=False)
    chapter_title: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    content: Mapped[Optional[str]] = mapped_column(TEXT)
    content_hash: Mapped[Optional[str]] = mapped_column(CHAR(64))
    word_count: Mapped[Optional[int]] = mapped_column(Integer)

    book: Mapped["Book"] = relationship("Book", back_populates="chapters")


class ParseLog(Base):
    __tablename__ = "parse_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    book_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("books.id"))
    log_type: Mapped[str] = mapped_column(
        Enum("info", "warning", "error"),
        nullable=False,
        default="info",
        server_default="info",
    )
    message: Mapped[Optional[str]] = mapped_column(VARCHAR(500))
    detected_encoding: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    parse_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    book: Mapped[Optional["Book"]] = relationship("Book", back_populates="parse_logs")
