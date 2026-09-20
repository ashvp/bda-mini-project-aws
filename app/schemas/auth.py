from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Unique username for the resident")
    password: str = Field(..., min_length=6, max_length=128, description="Account password (min 6 characters)")
    apartment_block_num: str = Field(..., min_length=1, max_length=50, description="Apartment block number or name, e.g. 'A'")
    house_num: str = Field(..., min_length=1, max_length=50, description="House or flat number, e.g. '402'")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username of the user or admin")
    password: str = Field(..., min_length=1, description="Account password")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[int] = None
    is_admin: Optional[bool] = None
    exp: Optional[int] = None
