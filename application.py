
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db
from routers import auth
from security import get_current_user


def create_app(db_engine=engine):
    # Create database tables using the supplied engine.
    models.Base.metadata.create_all(bind=db_engine)

    app = FastAPI(title="Piazza API")

    app.include_router(auth.router, prefix="/auth")

    # Check whether the API is running.
    @app.get("/health")
    def health():
        return {"status": "healthy"}


    # Retrieve all posts from the database.
    @app.get("/posts", response_model=list[schemas.PostResponse])
    def get_posts(
        db: Session = Depends(get_db),
        # Tells FastAPI to verify the JWT and retrieve the user before executing get_posts()
        current_user: models.User = Depends(get_current_user)
    ):
        posts = db.query(models.Post).all()
        return posts

    # Retrieve one post by its ID.
    @app.get("/posts/{post_id}", response_model=schemas.PostResponse)
    def get_post(
        post_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
    ):  
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
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
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
