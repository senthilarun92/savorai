from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)

    # Every recipe belongs to exactly one application user.
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cuisine = Column(String(100), nullable=True)
    diet = Column(String(100), nullable=True)
    language = Column(String(50), nullable=True)
    servings = Column(Integer, nullable=True)
    prep_time = Column(Integer, nullable=True)
    cook_time = Column(Integer, nullable=True)
    difficulty = Column(String(50), nullable=True)
    ingredients = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    nutrition = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
