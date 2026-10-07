"""Pydantic schemas used by the API endpoints."""

from pydantic import BaseModel, ConfigDict


class BlogCreate(BaseModel):
    """Request model for creating a blog post."""

    title: str
    content: str


class BlogResponse(BlogCreate):
    """Response model returned after creating or fetching a blog post."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Request model for signing up a user."""

    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """Request model for user login."""

    username: str
    password: str


class UserOut(BaseModel):
    """Public user information returned by the API."""

    id: int
    username: str
    email: str
    role: str
    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    """Request model for adding a comment."""

    text: str
    blog_id: int


class CommentResponse(CommentCreate):
    """Response model returned for comment operations."""

    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
