from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.program import Program


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    generic_name: Mapped[str] = mapped_column(String(255), default="")
    strength: Mapped[str] = mapped_column(String(128), default="")
    form: Mapped[str] = mapped_column(String(64), default="")
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"))

    program: Mapped[Program] = relationship(back_populates="medications")
