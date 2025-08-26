from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Album(Base):
    __tablename__ = "albums"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
