import os
from pathlib import Path
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker



# Enable foreign-key enforcement for SQLite connections.
@event.listens_for(Engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# This creates a SQLite database file called piazza.db.
DATABASE_PATH = Path(__file__).resolve().parent / "piazza.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


# The engine is the connection point between SQLAlchemy and the database.
engine = create_engine(
    DATABASE_URL,
    # SQLite normally checks that one connection is used by one thread.
    # We disable that check because FastAPI can handle requests in different threads.
    connect_args={"check_same_thread": False}
)


# SessionLocal creates database sessions.
# A session is the object we use to talk to the database.
# autocommit=False means we choose when to save changes with db.commit().
# autoflush=False keeps SQLAlchemy from sending changes before we ask it to.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Database SQLAlchemy model classes will inherit from this Base class.
Base = declarative_base()

def get_db():
    # Open a database session for one API request.
    db = SessionLocal()

    try:
        # yield gives the open session to the route function.
        yield db

    finally:
        # Always close the session after the request finishes.
        db.close()
