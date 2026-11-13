
from sqlalchemy import Column, Integer, String
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
