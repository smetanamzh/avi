from sqlalchemy import Column, Integer, String, Text, Boolean

from app.database.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)

    text = Column(Text, nullable=False)
    rewritten_text = Column(Text)

    category = Column(String, default="other")
    importance = Column(Integer, default=3)

    processed = Column(Boolean, default=False)
    published = Column(Boolean, default=False)
