
from sqlalchemy import (
    Column, Integer, String, DateTime,
    ForeignKey, Table, UniqueConstraint, CheckConstraint
)
from database import Base
from sqlalchemy.orm import relationship


# User is a Python class, SQLAlchemy maps it to the user table.
class User(Base):
    # This is the table name that will be created in SQLite.
    __tablename__ = "users"

    # id is the primary key. SQLite will generate it automatically.
    id = Column(Integer, primary_key=True, index=True)

    # Each user must have a unique email address.
    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    # nullable=False means this column is required.
    # coursework requires securely hashed passwords.
    password_hash = Column(
        String,
        nullable=False
    )

    # One user can create multiple posts.
    posts = relationship("Post", back_populates="author")

    # One user can write many comments.
    comments = relationship("Comment", back_populates="author")



# Association table connecting posts and topics.
post_topics = Table(
    "post_topics",
    Base.metadata,
    Column(
        "post_id",
        Integer,
        ForeignKey("posts.id"),
        primary_key=True
    ),
    Column(
        "topic_id",
        Integer,
        ForeignKey("topics.id"),
        primary_key=True
    )
)


# Post is a Python class, SQLAlchemy maps it to the posts table.
class Post(Base):
    # Table name that will be created in SQLite.
    __tablename__ = "posts"

    # id is the primary key. SQLite will generate it automatically.
    id = Column(Integer, primary_key=True, index=True)

    # stores the ID of the user who created the post.
    # Each post belongs to one user.
    author_id = Column(
        Integer,
        # tells SQLAlchemy that this value references the users table.
        ForeignKey("users.id"), 
        nullable=False
    )

    # lets Python move between related objects.
    author = relationship("User", back_populates="posts")

    # A post must have a title and body.
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)

    # A post records when it was created and when it expires.
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # A post could belong to multiple topics.
    topics = relationship(
        "Topic",
        secondary=post_topics,
        back_populates="posts"
    )

    # Return topic names instead of Topic objects.
    @property
    def topic_names(self):
        return [topic.name for topic in self.topics]

    # API responses include UTC timezone information
    @property
    def created_at_utc(self):
        from rules import as_utc
        return as_utc(self.created_at)

    @property
    def expires_at_utc(self):
        from rules import as_utc
        return as_utc(self.expires_at)

    # Calculates the post's status whenever it is accessed.
    @property
    def status(self):
        from datetime import datetime, timezone
        from rules import post_status

        return post_status(
            self.expires_at,
            datetime.now(timezone.utc)
        )
    

    # All reactions associated with this post.
    reactions = relationship("Reaction", back_populates="post")

    # One post can have many comments.
    comments = relationship("Comment", back_populates="post")

    # Calculate the number of likes.
    @property
    def likes(self):
        return sum(
            reaction.value == "like"
            for reaction in self.reactions
        )

    # Calculate the number of dislikes.
    @property
    def dislikes(self):
        return sum(
            reaction.value == "dislike"
            for reaction in self.reactions
        )


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    post_id = Column(
        Integer,
        ForeignKey("posts.id"),
        nullable=False
    )

    value = Column(String, nullable=False)
    
    # Connect this reaction to its post.
    post = relationship("Post", back_populates="reactions")


    
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "post_id",
            name="uq_user_post_reaction"
        ),
        CheckConstraint(
            "value IN ('like', 'dislike')",
            name="ck_reaction_valid_value"
        ),
    )




# Comment is a Python class mapped to the comments table.
class Comment(Base):
    __tablename__ = "comments"

    # Each comment receives a unique ID.
    id = Column(Integer, primary_key=True, index=True)

    # The user who wrote the comment.
    author_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    # The post that the comment belongs to.
    post_id = Column(
        Integer,
        ForeignKey("posts.id"),
        nullable=False
    )

    # The text written by the user.
    body = Column(String, nullable=False)

    # When the comment was created.
    created_at = Column(DateTime, nullable=False)
    # Return the comment timestamp with UTC timezone information.
    @property
    def created_at_utc(self):
        from rules import as_utc
        return as_utc(self.created_at)

    # Connect each comment to its author.
    author = relationship("User", back_populates="comments")

    # Connect each comment to its post.
    post = relationship("Post", back_populates="comments")



# Topic is a Python class mapped to the topics table.
class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # One topic can contain multiple posts.
    posts = relationship(
        "Post",
        secondary=post_topics,
        back_populates="topics"
    )

