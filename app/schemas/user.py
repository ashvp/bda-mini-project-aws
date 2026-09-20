from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.house import HouseResponse


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Username of the resident or admin")
    isAdmin: bool = False


class UserResponse(UserBase):
    userid: int
    houseid: Optional[int] = None
    house: Optional[HouseResponse] = None

    model_config = ConfigDict(from_attributes=True)
