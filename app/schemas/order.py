from pydantic import BaseModel, UUID4
from typing import List, Optional
from app.models.order import OrderStatus
from .restaurant import MenuItemRead

class OrderItemBase(BaseModel):
    menu_item_id: int
    quantity: int = 1
    assigned_user_id: Optional[UUID4] = None

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemRead(OrderItemBase):
    id: int
    menu_item: MenuItemRead

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    session_id: UUID4

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderRead(OrderBase):
    id: int
    status: OrderStatus
    items: List[OrderItemRead] = []

    class Config:
        from_attributes = True
