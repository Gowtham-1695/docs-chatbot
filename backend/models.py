from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    text_length = Column(Integer)

    chunks = relationship("Chunk", back_populates="file")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    content = Column(String)
    embedding = Column(String)  # can store as JSON string

    file = relationship("File", back_populates="chunks")