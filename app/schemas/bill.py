from pydantic import BaseModel, UUID4
from typing import List


class BillItemDetail(BaseModel):
    """A single item on someone's share of the bill."""
    menu_item_name: str
    quantity: int
    unit_price: float
    share_amount: float  # What this user pays for this item
    is_shared: bool  # Whether the item was split among participants


class UserBillShare(BaseModel):
    """One user's portion of the bill."""
    user_id: UUID4
    username: str
    items: List[BillItemDetail] = []
    total: float = 0.0


class BillSummary(BaseModel):
    """Complete bill breakdown for a dining session."""
    session_id: UUID4
    grand_total: float = 0.0
    per_person: List[UserBillShare] = []
