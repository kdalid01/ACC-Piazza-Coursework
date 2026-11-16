from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db
from routers import auth
from security import get_current_user

from typing import Literal


def create_app(db_engine=engine):
    # Create database tables using the supplied engine.
    models.Base.metadata.create_all(bind=db_engine)

    app = FastAPI(title="Piazza API")

    app.include_router(auth.router, prefix="/auth")

    # Check whether the API is running.
    @app.get("/health")
    def health():
        return {"status": "healthy"}


    # Retrieve posts, optionally filtering by topic.
    @app.get(
        "/posts",
        response_model=list[schemas.PostResponse]
    )
    def get_posts(
        topic: Literal[
            "Politics", "Health", "Sport", "Tech"
        ] | None = None,
        status: Literal["Live", "Expired"] | None = None,
        db: Session = Depends(get_db),
        # Tells FastAPI to verify the JWT and retrieve the user before executing get_posts()
        current_user: models.User = Depends(get_current_user)
    ):
        query = db.query(models.Post)

        # Optional topic filtering.
        if topic is not None:
            query = (
                query.join(models.Post.topics)
                .filter(models.Topic.name == topic)
            )

        posts = query.all()

        # Filter posts by status option.
        if status is not None:
            now = datetime.now(timezone.utc)

            posts = [
                post for post in posts
                if post_status(post.expires_at, now) == status
            ]

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
        # Remove repeated topic names.
        topic_names = list(dict.fromkeys(post_data.topics))

        # Find existing Topic objects.
        topics = []

        for name in topic_names:
            topic = (
                db.query(models.Topic)
                .filter(models.Topic.name == name)
                .first()
            )

            # Create the topic if it doesn't already exist.
            if topic is None:
                topic = models.Topic(name=name)
                db.add(topic)
                # New Topic objects to receive their database-generated IDs
                db.flush()

            topics.append(topic)

        # New post's timestamp:
        now = datetime.now(timezone.utc)

        # Ensures that a new post's expiry is in the future
        if post_data.expires_at.astimezone(timezone.utc) <= now:
            raise HTTPException(
                status_code=422,
                detail="Expiry must be in the future"
            )


        # Create a post belonging to the logged-in user.
        post = models.Post(
            author_id=current_user.id,
            title=post_data.title,
            body=post_data.body,
            created_at=now.replace(tzinfo=None),
            expires_at=post_data.expires_at.astimezone(
                timezone.utc
            ).replace(tzinfo=None),
            # SQLAlchemy uses the relationship() definitions to correspond the post with its Topic objects.
            topics=topics
        )

        # Add the post to the database session.
        db.add(post)

        # Save the changes permanently.
        db.commit()

        # Reload the post to get its generated ID.
        db.refresh(post)

        return post

    return app
