# -*- coding=utf-8 -*-
import asyncio
from dataclasses import dataclass
import datetime
from decimal import Decimal
import math
import urllib.parse
from zoneinfo import ZoneInfo

from . import gas_stations
from .config import config
from .fuels import group_price
from .models import GasStation
from .opening_hours import OpeningState, state_at
from .osrm import NoRoute

__all__ = ["Candidate", "Listed", "NoStop", "Stops", "candidates", "consumption_at", "fuel_walk", "range_walk",
           "search", "segment_speed", "station_link", "station_zone", "stop_cost"]


@dataclass(frozen=True)
class Candidate:
    station: GasStation
    field: str
    price: Decimal
    distance_km: float


@dataclass(frozen=True)
class Listed:
    station: GasStation
    field: str
    price: Decimal
    distance_m: float
    detour_s: float
    # In the time zone of the station.
    arrival: datetime.datetime
    cost: float
    state: OpeningState


@dataclass(frozen=True)
class NoStop:
    fuel_left: float | None = None
    range_left: float | None = None


@dataclass(frozen=True)
class Stops:
    liters: float
    stations: tuple[Listed, ...]


def consumption_at(parameters, speed_kmh):
    if speed_kmh < 80:
        return parameters.consume_80

    growth = (speed_kmh ** 2 - 80 ** 2) / (120 ** 2 - 80 ** 2)
    return parameters.consume_80 + (parameters.consume_120 - parameters.consume_80) * growth


def segment_speed(distance_m, duration_s):
    return distance_m / (duration_s * config.time_multiplier) * 3.6


def fuel_walk(route, parameters, fuel):
    """The index of the first point with 5 L or less and the fuel left there.

    The index is None when the fuel left at the destination is more than 5 L.
    """
    for index, (distance, duration) in enumerate(zip(route.segment_distance, route.segment_duration)):
        if fuel <= 5:
            return index, fuel
        fuel -= distance / 1000 * _segment_consumption(parameters, distance, duration) / 100

    if fuel <= 5:
        return len(route.segment_distance), fuel
    return None, fuel


def range_walk(route, range_km, reserve_km):
    """The index of the first point with `reserve_km` or less of range left, and the range left there.

    The index is None when more than `reserve_km` is left at the destination.
    """
    for index, distance in enumerate(route.segment_distance):
        if range_km <= reserve_km:
            return index, range_km
        range_km -= distance / 1000

    if range_km <= reserve_km:
        return len(route.segment_distance), range_km
    return None, range_km


def _segment_consumption(parameters, distance, duration):
    if duration > 0:
        return consumption_at(parameters, segment_speed(distance, duration))
    return parameters.consume_80


async def candidates(position, fuel_type):
    """The 30 stations nearest to a `[longitude, latitude]` position that sell a fuel of the group."""
    longitude, latitude = position
    half_height = 50 / 111.2
    half_width = 50 / (111.2 * math.cos(math.radians(latitude)))
    stations = await gas_stations.stations_in_area(latitude - half_height, longitude - half_width,
                                                   latitude + half_height, longitude + half_width)

    found = []
    for station in stations:
        offer = group_price(station.prices, fuel_type)
        if offer is None:
            continue

        distance_km = _great_circle_km(latitude, longitude, station.latitude, station.longitude)
        if distance_km <= 50:
            field, price = offer
            found.append(Candidate(station=station, field=field, price=price, distance_km=distance_km))

    found.sort(key=lambda candidate: (candidate.distance_km, candidate.station.id))
    return found[:30]


def _great_circle_km(latitude_a, longitude_a, latitude_b, longitude_b):
    phi_a, phi_b = math.radians(latitude_a), math.radians(latitude_b)
    half_dphi = (phi_b - phi_a) / 2
    half_dlambda = math.radians(longitude_b - longitude_a) / 2
    a = math.sin(half_dphi) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(half_dlambda) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def stop_cost(liters, price, detour_s, eur_per_hour):
    return liters * float(price) + detour_s / 3600 * eur_per_hour


def station_zone(province):
    if province in ("PALMAS (LAS)", "SANTA CRUZ DE TENERIFE"):
        return ZoneInfo("Atlantic/Canary")
    return ZoneInfo("Europe/Madrid")


def station_link(latitude, longitude):
    query = urllib.parse.urlencode({"api": "1", "query": f"{latitude:.6f},{longitude:.6f}"})
    return f"https://www.google.com/maps/search/?{query}"


async def search(router, origin, destination, parameters, now, *, liters=None, range_km=None):
    """`NoStop` or `Stops` for a journey, from the fuel in liters or from the range in km.

    `now` is an aware datetime. A `RouterUnavailable` of any request and a `NoRoute` of the planned route go out
    unchanged.
    """
    if (liters is None) == (range_km is None):
        raise ValueError("a search takes either liters or range_km")

    route = await router.route([origin, destination], segments=True)
    if liters is not None:
        search_index, fuel_left = fuel_walk(route, parameters, liters)
        if search_index is None:
            return NoStop(fuel_left=fuel_left)
        stop_liters = parameters.tank_volume - fuel_left
    else:
        search_index, range_left = range_walk(route, range_km, parameters.reserve_km)
        if search_index is None:
            return NoStop(range_left=range_left)
        # The fuel at the search point is not known. Every candidate buys the
        # same amount, so it only weighs the price against the detour time.
        stop_liters = parameters.tank_volume - 5
    found = await candidates(route.coordinates[search_index], parameters.fuel_type)
    requests = asyncio.Semaphore(4)

    async def detour(candidate):
        station = candidate.station
        async with requests:
            try:
                return await router.route([origin, (station.longitude, station.latitude), destination])
            except NoRoute:
                return None

    routes = await asyncio.gather(*[detour(candidate) for candidate in found])

    multiplier = config.time_multiplier
    listed = []
    for candidate, detour_route in zip(found, routes):
        if detour_route is None:
            continue

        station = candidate.station
        detour_s = (detour_route.duration - route.duration) * multiplier
        arrival = (now + datetime.timedelta(seconds=detour_route.leg_duration[0] * multiplier)).astimezone(
            station_zone(station.province))
        listed.append(Listed(
            station=station,
            field=candidate.field,
            price=candidate.price,
            distance_m=detour_route.leg_distance[0],
            detour_s=detour_s,
            arrival=arrival,
            cost=stop_cost(stop_liters, candidate.price, detour_s, parameters.eur_per_hour),
            state=state_at(station.opening_hours, arrival),
        ))

    listed.sort(key=lambda entry: (entry.cost, entry.station.id))
    return Stops(liters=stop_liters, stations=tuple(listed[:10]))
