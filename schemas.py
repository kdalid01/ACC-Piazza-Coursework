
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from datetime import datetime


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
    expires_at: datetime


# Data returned by the API.
# This schema describes the response shape sent back to the client.
class PostResponse(BaseModel):
    id: int
    title: str
    body: str
    created_at: datetime
    expires_at: datetime

    # This allows Pydantic to read values from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)
