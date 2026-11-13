
from sqlalchemy import Column, Integer, String, DateTime
from database import Base

# User is a Python class, but SQLAlchemy maps it to the user table.
class User(Base):
    # This is the table name that will be created in SQLite.
    __tablename__ = "users"

    # id is the primary key. SQLite will generate it automatically.
    id = Column(Integer, primary_key=True, index=True)

    # email must be unique, so two courses cannot use the same code.
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


# Post is a Python class, but SQLAlchemy maps it to the posts table.
class Post(Base):
    # Table name that will be created in SQLite.
    __tablename__ = "posts"

    # id is the primary key. SQLite will generate it automatically.
    id = Column(Integer, primary_key=True, index=True)

    # A post must have a title and body.
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)

    # A post records when it was created and when it expires.
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
