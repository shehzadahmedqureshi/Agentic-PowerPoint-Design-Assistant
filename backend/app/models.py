import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TemplateSlide(Base):
    __tablename__ = "template_slides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    source_filename: Mapped[str] = mapped_column(String(500))
    slide_number: Mapped[int] = mapped_column(Integer)
    preview_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    structure: Mapped[dict] = mapped_column(JSONB)
    structural_description: Mapped[str] = mapped_column(Text)
    structural_embedding: Mapped[list[float]] = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

