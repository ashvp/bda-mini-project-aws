from pydantic import BaseModel, ConfigDict, Field


class HouseBase(BaseModel):
    apartment_block_num: str = Field(..., min_length=1, max_length=50, description="Apartment block number or name, e.g., 'Block A'")
    house_num: str = Field(..., min_length=1, max_length=50, description="House or flat number, e.g., '102'")


class HouseCreate(HouseBase):
    pass


class HouseResponse(HouseBase):
    houseid: int

    model_config = ConfigDict(from_attributes=True)
