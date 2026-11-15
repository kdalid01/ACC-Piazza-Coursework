
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas

from database import get_db
from security import (
    create_access_token,
    hash_password,
    verify_password
)


# Group authentication-related endpoints.
router = APIRouter()


# Register a new Piazza user.
@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=201
)
def register(
    user: schemas.UserRegister,
    db: Session = Depends(get_db)
):
    # Check if the email is already registered.
    existing_user = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    # Create a User object with a hashed password.
    db_user = models.User(
        email=user.email,
        password_hash=hash_password(user.password)
    )

    # Save the user in SQLite.
    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    # Reload database-generated values, including id.
    db.refresh(db_user)

    return db_user


# Log in an existing Piazza user.
@router.post(
    "/login",
    response_model=schemas.TokenResponse
)
def login(
    user_login: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    # Find the user by their email address.
    user = (
        db.query(models.User)
        .filter(models.User.email == user_login.email)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Check the password against the stored hash.
    if not verify_password(
        user_login.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Create an expiring JWT.
    token = create_access_token(
        {"sub": user.email}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }
