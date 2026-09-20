from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse
from app.schemas.house import HouseResponse


class MaintenanceBase(BaseModel):
    problem_category: str = Field(..., min_length=2, max_length=100, description="Category of problem, e.g., 'Plumbing', 'AC / Electrical', 'Carpentry'")
    details: str = Field(..., min_length=5, description="Detailed description of the issue")


class MaintenanceAssign(BaseModel):
    isAssignedTo: str = Field(..., min_length=1, max_length=150, description="Name or role of person/technician assigned to work on the problem")


class MaintenanceResponse(MaintenanceBase):
    maintanance_id: int
    date: datetime
    houseid: int
    userid: int
    image_url: str
    isAssignedTo: Optional[str] = None

    user: Optional[UserResponse] = None
    house: Optional[HouseResponse] = None

    model_config = ConfigDict(from_attributes=True)
