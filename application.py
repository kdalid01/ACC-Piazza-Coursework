from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
import rules

from database import engine, get_db
from routers import auth
from security import get_current_user
from rules import post_status, as_utc

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
            now = rules.utcnow()

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
        now = rules.utcnow()

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

        
    # Create or update the current user's reaction to a post.
    @app.put("/posts/{post_id}/reaction")
    def react_to_post(
        post_id: int,
        reaction_data: schemas.ReactionCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
    ):
        # Find the requested post.
        post = db.query(models.Post).filter(
            models.Post.id == post_id
        ).first()

        if post is None:
            raise HTTPException(
                status_code=404,
                detail="Post not found"
            )

        # Expired posts cannot receive new reactions.
        now = rules.utcnow()

        if post_status(post.expires_at, now) == "Expired":
            raise HTTPException(
                status_code=409,
                detail="Cannot react to an expired post"
            )

        # Authors cannot react to their own posts.
        if post.author_id == current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Authors cannot react to their own posts"
            )

        # Find this user's existing reaction, if any.
        existing_reaction = db.query(models.Reaction).filter(
            models.Reaction.user_id == current_user.id,
            models.Reaction.post_id == post_id
        ).first()

        if existing_reaction is None:
            # Insert a new reaction.
            reaction = models.Reaction(
                user_id=current_user.id,
                post_id=post_id,
                value=reaction_data.value
            )
            db.add(reaction)
        else:
            # Replace the existing reaction value.
            existing_reaction.value = reaction_data.value

        db.commit()

        # Count the post's likes and dislikes.
        reactions = db.query(models.Reaction).filter(
            models.Reaction.post_id == post_id
        ).all()

        likes = sum(r.value == "like" for r in reactions)
        dislikes = sum(r.value == "dislike" for r in reactions)

        return {
            "post_id": post_id,
            "likes": likes,
            "dislikes": dislikes
        }
    

    @app.post(
        "/posts/{post_id}/comments",
        response_model=schemas.CommentResponse,
        status_code=201
    )
    def create_comment(
        post_id: int,
        comment_data: schemas.CommentCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
    ):
        # 1. Find the post.
        post = db.query(models.Post).filter(
            models.Post.id == post_id
        ).first()

        if post is None:
            raise HTTPException(
                status_code=404,
                detail="Post not found"
            )

        # 2. Check that the post has not expired.
        if post_status(
            post.expires_at,
            rules.utcnow()
        ) == "Expired":
            raise HTTPException(
                status_code=409,
                detail="Cannot comment on an expired post"
            )

        # 3. Create the new comment.
        new_comment = models.Comment(
            author_id=current_user.id,
            post_id=post.id,
            body=comment_data.body,
            created_at=rules.utcnow().replace(tzinfo=None)
        )

        # 4. Save the comment to the database.
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)

        # 5. Return the saved comment.
        return new_comment



    
    # Find the most-active live post in a topic.
    @app.get(
        "/topics/{topic}/most-active",
        response_model=list[schemas.PostResponse]
    )
    def get_most_active_post(
        topic: Literal["Politics", "Health", "Sport", "Tech"],
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
    ):
        # Find posts belonging to the requested topic.
        posts = (
            db.query(models.Post)
            .join(models.Post.topics)
            .filter(models.Topic.name == topic)
            .all()
        )

        # Keep only live posts.
        now = rules.utcnow()

        live_posts = [
            post for post in posts
            if post_status(post.expires_at, now) == "Live"
        ]

        # No live posts means an empty list.
        if not live_posts:
            return []

        # Rank by activity, creation time, then post ID.
        ranked_posts = sorted(
            live_posts,
            key=lambda post: (
                -(post.likes + post.dislikes),
                -as_utc(post.created_at).timestamp(),
                post.id
            )
        )

        # Return the winner as a list.
        return [ranked_posts[0]]

    return app
