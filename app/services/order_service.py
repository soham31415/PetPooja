from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem, OrderStatus
from app.models.session import DiningSession, SessionStatus
from app.models.restaurant import MenuItem
import uuid
from typing import List


async def create_order(
    db: AsyncSession,
    session_id: uuid.UUID,
    items: List[dict],
) -> Order:
    """
    Create a new order for a dining session.
    items: list of dicts with keys: menu_item_id, quantity, assigned_user_id (optional)
    """
    # Verify session exists and is active
    session = await db.get(DiningSession, session_id)
    if not session:
        raise ValueError("Session not found")
    if session.status != SessionStatus.ACTIVE:
        raise ValueError("Session is not active")

    # Verify all menu items exist and belong to the session's restaurant
    for item_data in items:
        menu_item = await db.get(MenuItem, item_data["menu_item_id"])
        if not menu_item:
            raise ValueError(f"Menu item {item_data['menu_item_id']} not found")
        if session.restaurant_id and menu_item.restaurant_id != session.restaurant_id:
            raise ValueError(
                f"Menu item {item_data['menu_item_id']} does not belong to the session's restaurant"
            )

    # Create order
    order = Order(session_id=session_id, status=OrderStatus.PENDING)
    db.add(order)
    await db.flush()  # Get the order ID without committing

    # Create order items
    for item_data in items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data["menu_item_id"],
            quantity=item_data.get("quantity", 1),
            assigned_user_id=item_data.get("assigned_user_id"),
        )
        db.add(order_item)

    await db.commit()

    # Reload with relationships
    return await get_order(db, order.id)


async def get_order(db: AsyncSession, order_id: int) -> Order:
    """Fetch an order with its items and their menu item details."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .where(Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise ValueError("Order not found")
    return order


async def get_orders_for_session(
    db: AsyncSession, session_id: uuid.UUID
) -> List[Order]:
    """List all orders for a dining session."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .where(Order.session_id == session_id)
    )
    return result.scalars().all()


# Valid status transitions
_VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED],
    OrderStatus.CONFIRMED: [OrderStatus.PAID],
    OrderStatus.PAID: [],
}


async def update_order_status(
    db: AsyncSession, order_id: int, new_status: OrderStatus
) -> Order:
    """Update the status of an order with transition validation."""
    order = await get_order(db, order_id)

    if new_status not in _VALID_TRANSITIONS.get(order.status, []):
        raise ValueError(
            f"Cannot transition from '{order.status.value}' to '{new_status.value}'"
        )

    order.status = new_status
    db.add(order)
    await db.commit()
    return await get_order(db, order_id)


async def add_item_to_order(db: AsyncSession, order_id: int, item_data: dict) -> Order:
    """Add an item to an existing order (only if pending)."""
    order = await get_order(db, order_id)
    if order.status != OrderStatus.PENDING:
        raise ValueError("Can only add items to pending orders")

    menu_item = await db.get(MenuItem, item_data["menu_item_id"])
    if not menu_item:
        raise ValueError(f"Menu item {item_data['menu_item_id']} not found")

    order_item = OrderItem(
        order_id=order_id,
        menu_item_id=item_data["menu_item_id"],
        quantity=item_data.get("quantity", 1),
        assigned_user_id=item_data.get("assigned_user_id"),
    )
    db.add(order_item)
    await db.commit()
    return await get_order(db, order_id)


async def remove_item_from_order(
    db: AsyncSession, order_id: int, item_id: int
) -> Order:
    """Remove an item from an order (only if pending)."""
    order = await get_order(db, order_id)
    if order.status != OrderStatus.PENDING:
        raise ValueError("Can only remove items from pending orders")

    result = await db.execute(
        select(OrderItem).where(
            OrderItem.id == item_id, OrderItem.order_id == order_id
        )
    )
    order_item = result.scalars().first()
    if not order_item:
        raise ValueError("Order item not found in this order")

    await db.delete(order_item)
    await db.commit()
    return await get_order(db, order_id)
