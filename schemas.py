
from pydantic import BaseModel, ConfigDict


# Data returned by the API.
# This schema describes the response sent back to the client.
class UserResponse(BaseModel):
    id: int
    email: str

    # Allows Pydantic to read values from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)
