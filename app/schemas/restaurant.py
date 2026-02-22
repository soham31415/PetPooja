from pydantic import BaseModel
from typing import List, Optional

class MenuItemBase(BaseModel):
    name: str
    description: str
    price: float
    tags: List[str] = []

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemRead(MenuItemBase):
    id: int
    restaurant_id: int

    class Config:
        from_attributes = True

class RestaurantBase(BaseModel):
    name: str
    address: str

class RestaurantCreate(RestaurantBase):
    pass

class RestaurantRead(RestaurantBase):
    id: int
    menu_items: List[MenuItemRead] = []

    class Config:
        from_attributes = True
