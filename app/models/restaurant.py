from sqlalchemy import String, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from typing import List

class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String)
    
    menu_items: Mapped[List["MenuItem"]] = relationship(back_populates="restaurant")

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
