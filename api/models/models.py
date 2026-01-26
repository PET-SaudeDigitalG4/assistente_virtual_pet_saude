from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_wpp = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    text = Column(String, nullable=False)
    sender = Column(String, nullable=False)  
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    chat = relationship("Chat", back_populates="messages")

class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String, primary_key=True, index=True) 
    value = Column(String, nullable=False)           
    description = Column(String, nullable=True)       
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    level = Column(String, nullable=False) 
    event_type = Column(String, nullable=False) 
    message = Column(Text, nullable=False) 
    metadata_info = Column(JSON, nullable=True) 
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
