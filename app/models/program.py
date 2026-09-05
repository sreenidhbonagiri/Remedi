from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.medication import Medication


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    manufacturer: Mapped[str] = mapped_column(String(255))
    fpl_limit_percent: Mapped[float] = mapped_column(Float, default=400.0)
    description: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    mailing_address: Mapped[str] = mapped_column(String(512), default="")

    medications: Mapped[list[Medication]] = relationship(back_populates="program")
