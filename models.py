"""
SQLAlchemy models for the blog application.

This module contains the Blog, User, and Comment entities and the
relationships between them.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Blog(Base):
    """Blog post model."""

    __tablename__ = "blogs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    comments = relationship("Comment", back_populates="blog", cascade="all, delete-orphan")


class User(Base):
    """Application user model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="reader", nullable=False)
    comments = relationship("Comment", back_populates="user")


class Comment(Base):
    """Comment placed on a blog post."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    blog_id = Column(Integer, ForeignKey("blogs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blog = relationship("Blog", back_populates="comments")
    user = relationship("User", back_populates="comments")
