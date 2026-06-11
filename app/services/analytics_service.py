from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.order import Order, OrderItem, OrderStatus
from app.models.session import DiningSession, SessionParticipant
from app.models.restaurant import MenuItem
from app.schemas.analytics import MenuItemStat, RestaurantAnalytics


async def get_restaurant_analytics(db: AsyncSession, restaurant_id: int, top_n: int = 5) -> RestaurantAnalytics:
    """Aggregate stats for a restaurant's owner dashboard: order volume and
    status breakdown, revenue, average group size, and best-selling items."""

    # Orders by status (+ total)
    status_rows = (
        await db.execute(
            select(Order.status, func.count(Order.id))
            .join(DiningSession, Order.session_id == DiningSession.id)
            .where(DiningSession.restaurant_id == restaurant_id)
            .group_by(Order.status)
        )
    ).all()
    orders_by_status = {status.value: count for status, count in status_rows}
    total_orders = sum(orders_by_status.values())

    # Revenue: sum(quantity * price) across all order items for this restaurant's orders
    total_revenue = (
        await db.execute(
            select(func.coalesce(func.sum(OrderItem.quantity * MenuItem.price), 0.0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .join(DiningSession, Order.session_id == DiningSession.id)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .where(DiningSession.restaurant_id == restaurant_id)
        )
    ).scalar_one()

    # Average participants per session (active + past), for sessions at this restaurant
    participant_counts_subq = (
        select(
            SessionParticipant.session_id,
            func.count(SessionParticipant.user_id).label("participant_count"),
        )
        .join(DiningSession, SessionParticipant.session_id == DiningSession.id)
        .where(DiningSession.restaurant_id == restaurant_id)
        .group_by(SessionParticipant.session_id)
        .subquery()
    )
    average_participants = (
        await db.execute(select(func.coalesce(func.avg(participant_counts_subq.c.participant_count), 0.0)))
    ).scalar_one()

    # Top-selling menu items by quantity ordered
    top_item_rows = (
        await db.execute(
            select(
                MenuItem.id,
                MenuItem.name,
                func.sum(OrderItem.quantity).label("quantity_ordered"),
                func.sum(OrderItem.quantity * MenuItem.price).label("revenue"),
            )
            .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .join(DiningSession, Order.session_id == DiningSession.id)
            .where(DiningSession.restaurant_id == restaurant_id)
            .group_by(MenuItem.id, MenuItem.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(top_n)
        )
    ).all()

    top_menu_items = [
        MenuItemStat(
            menu_item_id=row.id,
            name=row.name,
            quantity_ordered=int(row.quantity_ordered),
            revenue=float(row.revenue),
        )
        for row in top_item_rows
    ]

    return RestaurantAnalytics(
        restaurant_id=restaurant_id,
        total_orders=total_orders,
        orders_by_status=orders_by_status,
        total_revenue=float(total_revenue),
        average_participants_per_session=float(average_participants),
        top_menu_items=top_menu_items,
    )
