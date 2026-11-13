
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

import models
from database import engine, get_db

import schemas


# Create the database tables when the app starts.
models.Base.metadata.create_all(bind=engine)


app = FastAPI(title="Piazza API")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/users", response_model=list[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    # Read all users from the database.
    users = db.query(models.User).all()

    return users
