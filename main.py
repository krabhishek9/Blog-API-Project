"""
FastAPI application entry point.

This module wires together the database, authentication helpers, and the blog
API endpoints. The app is intentionally structured into sections so each part
of the application is easy to follow.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas
from auth import create_access_token, hash_password, verify_password, verify_token
from database import SessionLocal, engine

# Create database tables when the application starts.
models.Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Default admin user setup
# ---------------------------------------------------------------------------
def create_default_admin():
    """Ensure an admin user exists with the expected default credential."""
    db = SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()

        if admin_user is None:
            admin_user = models.User(
                username="admin",
                email="admin@example.com",
                password=hash_password("1234"),
                role="admin",
            )
            db.add(admin_user)
        else:
            admin_user.email = "admin@example.com"
            admin_user.role = "admin"
            admin_user.password = hash_password("1234")

        db.commit()
        db.refresh(admin_user)
    finally:
        db.close()


app = FastAPI(title="Blog API", version="1.0.0")


@app.on_event("startup")
def startup_event():
    """Run startup tasks such as seeding the default admin user."""
    create_default_admin()


# ---------------------------------------------------------------------------
# Database dependency
# ---------------------------------------------------------------------------
def get_db():
    """Provide a database session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.get("/")
def home():
    """Return a welcome message for the API."""
    return {"message": "Blog API started successfully"}


@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT token.

    Swagger UI sends credentials as form fields: username and password.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user.username, "user_id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user account and store a hashed password."""
    existing_user = (
        db.query(models.User)
        .filter((models.User.username == user.username) | (models.User.email == user.email))
        .first()
    )

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role="reader",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ---------------------------------------------------------------------------
# Blog routes
# ---------------------------------------------------------------------------
@app.post("/blogs", response_model=schemas.BlogResponse)
def create_blog(
    blog: schemas.BlogCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Create a new blog post. The route is protected by JWT verification."""
    del current_user
    new_blog = models.Blog(title=blog.title, content=blog.content)
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    return new_blog


@app.get("/blogs")
def get_blogs(
    page: int = 1,
    limit: int = 5,
    search: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Return a paginated list of blog posts, optionally filtered by title."""
    if page < 1:
        raise HTTPException(status_code=400, detail="Page number must be greater than 0")
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be greater than 0")

    query = db.query(models.Blog)
    if search:
        query = query.filter(models.Blog.title.ilike(f"%{search}%"))

    total = query.count()
    start = (page - 1) * limit
    blogs = query.offset(start).limit(limit).all()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "data": blogs,
    }


@app.get("/blogs/{blog_id}", response_model=schemas.BlogResponse)
def get_blog(blog_id: int, db: Session = Depends(get_db), current_user: dict = Depends(verify_token)):
    """Fetch a single blog post by ID."""
    del current_user
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()

    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    return blog


@app.put("/blogs/{blog_id}", response_model=schemas.BlogResponse)
def update_blog(
    blog_id: int,
    blog: schemas.BlogCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Update an existing blog post."""
    del current_user
    existing_blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()

    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    existing_blog.title = blog.title
    existing_blog.content = blog.content
    db.commit()
    db.refresh(existing_blog)
    return existing_blog


@app.delete("/blogs/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), current_user: dict = Depends(verify_token)):
    """Delete a blog post by ID."""
    del current_user
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id)
    existing_blog = blog.first()

    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog.delete()
    db.commit()
    return {"message": "Blog deleted successfully"}


# ---------------------------------------------------------------------------
# Comment routes
# ---------------------------------------------------------------------------
@app.post("/comments", response_model=schemas.CommentResponse)
def add_comment(
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Create a comment for a blog post using the logged-in user's identity."""
    blog = db.query(models.Blog).filter(models.Blog.id == comment.blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    new_comment = models.Comment(
        text=comment.text,
        blog_id=comment.blog_id,
        user_id=current_user["user_id"],
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment


# ---------------------------------------------------------------------------
# File upload route
# ---------------------------------------------------------------------------
@app.post("/upload-image")
def upload_image(file: UploadFile = File(...)):
    """Save an uploaded image inside the static folder and return its URL."""
    upload_dir = Path("static")
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / file.filename
    with file_path.open("wb") as destination:
        destination.write(file.file.read())

    return {"filename": file.filename, "url": f"/static/{file.filename}"}
