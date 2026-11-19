
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from datetime import datetime
from typing import Literal


# Data returned by the API.
# This schema describes the response sent back to the client.
class UserResponse(BaseModel):
    id: int
    email: str

    # Allows Pydantic to read values from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)



# Data accepted when registering a new user.
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


# Data accepted when logging in.
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Data returned after a successful login.
class TokenResponse(BaseModel):
    access_token: str
    token_type: str



# Data accepted when creating a post.
# This schema describes the request body for POST /posts.
class PostCreate(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    
    # list[...] means the client supplies a list.
    # Literal[...] restricts each entry to one of the four permitted names.
    # Field(min_length=1) ensures the list isn't empty.
    topics: list[
        Literal["Politics", "Health", "Sport", "Tech"]
    ] = Field(min_length=1)

    expires_at: datetime

    # Prevents whitespace-only titles and messages,
    # Rejects expiry timestamps without a timezone.
    @field_validator("title", "body")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be empty or whitespace")
        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Expiry timestamp must include a timezone")
        return value



class CommentResponse(BaseModel):
    id: int
    author_id: int
    post_id: int
    body: str
    created_at: datetime = Field(
        validation_alias="created_at_utc"
    )

    model_config = ConfigDict(from_attributes=True)



# Data returned by the API.
# This schema describes the response shape sent back to the client.
class PostResponse(BaseModel):
    id: int
    author_id: int
    title: str
    body: str
    # Tells Pydantic to read the topic names from the SQLAlchemy model's topic_names property, while returning them in JSON under "topics".
    topics: list[str] = Field(validation_alias="topic_names")
    
    created_at: datetime = Field(
        validation_alias="created_at_utc"
    )
    
    expires_at: datetime = Field(
        validation_alias="expires_at_utc"
    )

    status: Literal["Live", "Expired"]

    likes: int
    dislikes: int
    comments: list[CommentResponse]

    # This allows Pydantic to read values from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)



class ReactionCreate(BaseModel):
    value: Literal["like", "dislike"]


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Comment cannot be whitespace-only")
        return value

