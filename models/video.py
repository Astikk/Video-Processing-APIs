from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime, timezone
from db.session import Base

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    size = Column(Integer)
    duration = Column(Float)  # in seconds
    upload_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
