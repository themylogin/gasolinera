# -*- coding=utf-8 -*-
import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["Base", "Car", "GasStation", "GasStationArea"]


class Base(DeclarativeBase):
    pass


class GasStation(Base):
    __tablename__ = "gas_station"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    postal_code: Mapped[str] = mapped_column(Text, nullable=False)
    locality: Mapped[str] = mapped_column(Text, nullable=False)
    municipality: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str] = mapped_column(Text, nullable=False)
    opening_hours: Mapped[str] = mapped_column(Text, nullable=False)
    prices: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Naive UTC. SQLite keeps no offset and compares these values as text.
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class GasStationArea(Base):
    """The R*Tree index of the station positions.

    Triggers on `gas_station` write it. Code that writes it directly makes it
    disagree with the table.
    """

    __tablename__ = "gas_station_area"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    min_latitude: Mapped[float] = mapped_column(Float)
    max_latitude: Mapped[float] = mapped_column(Float)
    min_longitude: Mapped[float] = mapped_column(Float)
    max_longitude: Mapped[float] = mapped_column(Float)


class Car(Base):
    __tablename__ = "car"

    telegram_user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tank_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    gauge_steps: Mapped[int] = mapped_column(Integer, nullable=False, server_default="16")
    fuel_type: Mapped[str] = mapped_column(Text, nullable=False)
    consume_80: Mapped[float] = mapped_column(Float, nullable=False)
    consume_120: Mapped[float] = mapped_column(Float, nullable=False)
    eur_per_hour: Mapped[float] = mapped_column(Float, nullable=False)
    reserve_km: Mapped[float] = mapped_column(Float, nullable=False, server_default="50")
