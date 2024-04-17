from sqlalchemy import Column, Integer, String, ForeignKey,Boolean,DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    tokens = relationship("Token", back_populates="user")
    is_admin = Column(Boolean, default=False)

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    author = Column(String, index=True)
    count = Column(Integer)
    borrower_email = Column(String, ForeignKey("users.email"))

class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="tokens")

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey('users.email'))
    book_id = Column(Integer, ForeignKey('books.id'))
    type = Column(String)  # "borrow" or "return"
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="history")
    book = relationship("Book", back_populates="history")

    __mapper_args__ = {
        'confirm_deleted_rows': False
    }