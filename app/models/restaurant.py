from sqlalchemy import String, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from typing import List, Optional
import uuid

class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String)
    # The user account that manages this restaurant (menu + live order dashboard)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    menu_items: Mapped[List["MenuItem"]] = relationship(back_populates="restaurant")
    owner: Mapped[Optional["User"]] = relationship()
    tables: Mapped[List["RestaurantTable"]] = relationship(back_populates="restaurant")


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    label: Mapped[str] = mapped_column(String)
    # Opaque token encoded into the table's QR code; scanning it resolves
    # straight to this table without exposing the numeric restaurant/table ids.
    qr_token: Mapped[str] = mapped_column(String, unique=True, index=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="tables")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    
    # Tags to match against TasteProfile (e.g. ["spicy", "vegetarian"])
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    restaurant: Mapped["Restaurant"] = relationship(back_populates="menu_items")
