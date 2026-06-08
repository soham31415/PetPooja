from pydantic import BaseModel, UUID4
from typing import Optional


class RestaurantTableBase(BaseModel):
    label: str


class RestaurantTableCreate(RestaurantTableBase):
    pass


class RestaurantTableRead(RestaurantTableBase):
    id: int
    restaurant_id: int
    qr_token: str

    class Config:
        from_attributes = True


class TableInfo(BaseModel):
    """Public info resolved by scanning a table's QR code."""
    table_id: int
    label: str
    restaurant_id: int
    restaurant_name: str
    active_session_id: Optional[UUID4] = None
