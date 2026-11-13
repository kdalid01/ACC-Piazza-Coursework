
from pydantic import BaseModel, ConfigDict, Field

from datetime import datetime


# Data returned by the API.
# This schema describes the response sent back to the client.
class UserResponse(BaseModel):
    id: int
    email: str

    # Allows Pydantic to read values from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)



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
