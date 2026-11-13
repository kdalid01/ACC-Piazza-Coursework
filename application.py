
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db


def create_app(db_engine=engine):
    # Create database tables using the supplied engine.
    models.Base.metadata.create_all(bind=db_engine)

    app = FastAPI(title="Piazza API")

    # Check whether the API is running.
    @app.get("/health")
    def health():
        return {"status": "healthy"}

    # Retrieve all users from the database.
    @app.get("/users", response_model=list[schemas.UserResponse])
    def get_users(db: Session = Depends(get_db)):
        users = db.query(models.User).all()
        return users

    # Retrieve all posts from the database.
    @app.get("/posts", response_model=list[schemas.PostResponse])
    def get_posts(db: Session = Depends(get_db)):
        posts = db.query(models.Post).all()
        return posts

    # Retrieve one post by its ID.
    @app.get("/posts/{post_id}", response_model=schemas.PostResponse)
    def get_post(post_id: int, db: Session = Depends(get_db)):
        post = db.query(models.Post).filter(
            models.Post.id == post_id
        ).first()

        if post is None:
            raise HTTPException(
                status_code=404,
                detail="Post not found"
            )

        return post

    # Create a new post.
    @app.post(
        "/posts",
        response_model=schemas.PostResponse,
        status_code=201
    )
    def create_post(
        post_data: schemas.PostCreate,
        db: Session = Depends(get_db)
    ):
        post = models.Post(
            title=post_data.title,
            body=post_data.body,
            created_at=datetime.now(timezone.utc),
            expires_at=post_data.expires_at
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        return post

    return app
