from pydantic import BaseModel
from typing import Dict, List


class MenuItemStat(BaseModel):
    menu_item_id: int
    name: str
    quantity_ordered: int
    revenue: float


class RestaurantAnalytics(BaseModel):
    restaurant_id: int
    total_orders: int
    orders_by_status: Dict[str, int]
    total_revenue: float
    average_participants_per_session: float
    top_menu_items: List[MenuItemStat]
