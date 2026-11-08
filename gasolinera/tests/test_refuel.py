# -*- coding=utf-8 -*-
import asyncio
from dataclasses import replace
import datetime
from decimal import Decimal
import json
import sqlite3

import pytest

from .. import refuel
from ..car import CarParameters
from ..opening_hours import OpeningState
from ..osrm import NoRoute, Route, RouterUnavailable

ORIGIN = (-3.70, 40.42)
DESTINATION = (2.17, 41.39)
NOW = datetime.datetime(2026, 11, 7, 18, 0, tzinfo=datetime.timezone.utc)
DIESEL = CarParameters(tank_volume=50, fuel_type="diesel", consume_80=6.0, consume_120=8.0, eur_per_hour=20.0,
                       reserve_km=50.0)


@pytest.fixture
def no_correction(monkeypatch):
    monkeypatch.setattr(refuel, "config", replace(refuel.config, time_multiplier=1.0))


def planned(segments=((1000.0, 40.0),), start=ORIGIN):
    longitude, latitude = start
    coordinates = tuple((longitude + n / 1000, latitude) for n in range(len(segments) + 1))
    distance = sum(segment[0] for segment in segments)
    duration = sum(segment[1] for segment in segments)
    return Route(distance=distance, duration=duration, leg_distance=(distance,), leg_duration=(duration,),
                 coordinates=coordinates, segment_distance=tuple(s[0] for s in segments),
                 segment_duration=tuple(s[1] for s in segments))


def detour(duration, to_station_s=600.0, to_station_m=10000.0):
    return Route(distance=20000.0, duration=duration, leg_distance=(to_station_m, 10000.0),
                 leg_duration=(to_station_s, duration - to_station_s))


class StubRouter:
    def __init__(self, route, detours=None):
        self.planned = route
        self.detours = detours or {}
        self.calls = []
        self.open = 0
        self.most_open = 0

    async def route(self, points, *, segments=False):
        self.calls.append((list(points), segments))
        if segments:
            return self.planned

        self.open += 1
        self.most_open = max(self.most_open, self.open)
        try:
            await asyncio.sleep(0.001)
        finally:
            self.open -= 1

        answer = self.detours.get(points[1], detour(self.planned.duration + 60))
        if isinstance(answer, Exception):
            raise answer
        return answer


def insert_station(db_path, station_id, latitude, longitude, prices, province="MADRID", hours="L-D: 24H", name=""):
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO gas_station VALUES (?, ?, ?, ?, '', '', '', '', ?, ?, ?, '2026-11-07 10:00:00')",
            (station_id, latitude, longitude, name, province, hours, json.dumps(prices)),
        )


def search(router, liters=5.0, parameters=DIESEL, now=NOW):
    return asyncio.run(refuel.search(router, ORIGIN, DESTINATION, parameters, now, liters=liters))


def search_range(router, range_km, parameters=DIESEL):
    return asyncio.run(refuel.search(router, ORIGIN, DESTINATION, parameters, NOW, range_km=range_km))


# The time correction


def test_the_default_multiplier_corrects_the_driving_time(store):
    assert refuel.config.time_multiplier == 0.933
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned(), {(-3.70, 40.42): detour(3100.0, to_station_s=3000.0)})

    [listed] = search(router).stations

    assert listed.arrival == NOW + datetime.timedelta(seconds=2799)


def test_the_correction_makes_a_segment_faster(monkeypatch):
    monkeypatch.setattr(refuel, "config", replace(refuel.config, time_multiplier=0.9))

    assert refuel.segment_speed(1000, 40) == pytest.approx(100)


# The consumption


@pytest.mark.parametrize("speed, consumption", [(100, 6.9), (130, 8.625), (50, 6.0), (80, 6.0), (120, 8.0)])
def test_the_consumption_curve(speed, consumption):
    assert refuel.consumption_at(DIESEL, speed) == pytest.approx(consumption)


def test_the_tank_reaches_5_l_on_the_route(no_correction):
    car = replace(DIESEL, consume_120=10.0)
    route = planned(((10000.0, 300.0),) * 10)

    index, fuel_left = refuel.fuel_walk(route, car, 10.0)

    assert index == 5
    assert fuel_left == pytest.approx(5.0)


def test_low_fuel_at_the_origin():
    assert refuel.fuel_walk(planned(((10000.0, 300.0),) * 3), DIESEL, 5.0) == (0, 5.0)


def test_a_segment_without_duration_uses_the_consumption_at_80():
    _index, fuel_left = refuel.fuel_walk(planned(((100000.0, 0.0),)), DIESEL, 20.0)

    assert fuel_left == pytest.approx(14.0)


def test_no_stop_is_needed_when_the_fuel_lasts(store):
    router = StubRouter(planned(((50000.0, 3000.0),)))

    answer = search(router, liters=20.0)

    assert answer == refuel.NoStop(fuel_left=pytest.approx(17.0))
    assert len(router.calls) == 1


# A search from a range


@pytest.mark.parametrize("inputs", [{}, {"liters": 10.0, "range_km": 100.0}])
def test_a_search_takes_either_liters_or_a_range(inputs):
    router = StubRouter(planned())

    with pytest.raises(ValueError):
        asyncio.run(refuel.search(router, ORIGIN, DESTINATION, DIESEL, NOW, **inputs))
    assert router.calls == []


def test_the_range_reaches_the_reserve_on_the_route():
    route = planned(((10000.0, 300.0),) * 10)

    index, range_left = refuel.range_walk(route, 80.0, 50.0)

    assert index == 3
    assert range_left == pytest.approx(50.0)


def test_a_range_below_the_reserve_searches_at_the_origin():
    assert refuel.range_walk(planned(((10000.0, 300.0),) * 3), 40.0, 50.0) == (0, 40.0)


def test_a_range_uses_no_consumption():
    route = planned(((10000.0, 300.0),) * 10)
    thirsty = replace(DIESEL, consume_80=29.0, consume_120=29.5)

    assert refuel.range_walk(route, 80.0, thirsty.reserve_km) == refuel.range_walk(route, 80.0, DIESEL.reserve_km)


def test_a_short_trip_with_a_range(store):
    router = StubRouter(planned(((100000.0, 3600.0),)))

    answer = search_range(router, 183.4)

    assert answer == refuel.NoStop(range_left=pytest.approx(83.4))
    assert len(router.calls) == 1


def test_a_range_that_leaves_only_the_reserve_needs_a_stop(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})

    answer = search_range(StubRouter(planned(((100000.0, 3600.0),))), 150.0)

    assert isinstance(answer, refuel.Stops)


def test_a_stop_from_a_range_buys_the_tank_minus_5_l(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})

    assert search_range(StubRouter(planned()), 10.0).liters == 45


def test_the_reserve_of_the_car_places_the_search_point(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    route = planned(((10000.0, 300.0),) * 10)

    no_stop = search_range(StubRouter(route), 150.0, parameters=replace(DIESEL, reserve_km=40.0))
    stop = search_range(StubRouter(route), 150.0, parameters=replace(DIESEL, reserve_km=60.0))

    assert no_stop == refuel.NoStop(range_left=pytest.approx(50.0))
    assert isinstance(stop, refuel.Stops)


# The planned route and the candidates


def test_the_planned_route_comes_first(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned())

    search(router)

    assert router.calls[0] == ([ORIGIN, DESTINATION], True)
    assert router.calls[1] == ([ORIGIN, (-3.70, 40.42), DESTINATION], False)


def test_a_station_without_the_fuel_is_no_candidate(store):
    insert_station(store, 1, 40.43, -3.70, {"Precio Gasoleo B": "1,549"})

    assert asyncio.run(refuel.candidates(ORIGIN, "diesel")) == []


def test_a_station_too_far_is_no_candidate(store):
    insert_station(store, 1, 40.42 + 51 / 111.2, -3.70, {"Precio Gasoleo A": "1,800"})
    insert_station(store, 2, 40.42 + 49 / 111.2, -3.70, {"Precio Gasoleo A": "1,800"})

    assert [c.station.id for c in asyncio.run(refuel.candidates(ORIGIN, "diesel"))] == [2]


def test_the_30_nearest_candidates_and_the_lower_id_on_a_tie(store):
    for station_id in range(1, 41):
        insert_station(store, station_id, 40.42 + (40 - station_id) // 2 / 1000, -3.70, {"Precio Gasoleo A": "1,8"})

    found = asyncio.run(refuel.candidates(ORIGIN, "diesel"))

    assert len(found) == 30
    assert [c.station.id for c in found[:4]] == [39, 40, 37, 38]


def test_a_candidate_has_its_group_price(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,799", "Precio Gasoleo Premium": "1,759"})

    [candidate] = asyncio.run(refuel.candidates(ORIGIN, "diesel"))

    assert (candidate.field, candidate.price) == ("Precio Gasoleo Premium", Decimal("1.759"))


# The detours


def test_the_detour_of_a_station(store, monkeypatch):
    monkeypatch.setattr(refuel, "config", replace(refuel.config, time_multiplier=0.9))
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned(((1000.0, 10000.0),)),
                        {(-3.70, 40.42): detour(10300.0, to_station_s=4000.0, to_station_m=150000.0)})

    [listed] = search(router).stations

    assert listed.detour_s == pytest.approx(270)
    assert listed.arrival == NOW + datetime.timedelta(seconds=3600)
    assert listed.distance_m == 150000


def test_a_station_that_the_router_cannot_reach_is_left_out(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    insert_station(store, 2, 40.43, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned(), {(-3.70, 40.42): NoRoute("x")})

    assert [listed.station.id for listed in search(router).stations] == [2]


def test_an_unavailable_router_stops_the_search(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned(), {(-3.70, 40.42): RouterUnavailable("x")})

    with pytest.raises(RouterUnavailable):
        search(router)


def test_no_more_than_four_open_detours(store):
    for station_id in range(1, 21):
        insert_station(store, station_id, 40.42 + station_id / 1000, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned())

    search(router)

    assert router.most_open == 4


# The cost and the order


def test_a_stop_fills_the_tank(store):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})

    assert search(StubRouter(planned()), liters=5.0).liters == 45


def test_the_two_parts_of_the_cost(no_correction):
    assert round(refuel.stop_cost(45, Decimal("1.800"), 600, 20), 2) == 84.33


def test_the_cost_decides_the_order_not_the_price(store, no_correction):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    insert_station(store, 2, 40.43, -3.70, {"Precio Gasoleo A": "1,750"})
    route = planned()
    router = StubRouter(route, {(-3.70, 40.42): detour(route.duration + 600),
                                (-3.70, 40.43): detour(route.duration + 1800)})

    stations = search(router).stations

    assert [listed.station.id for listed in stations] == [1, 2]
    assert [round(listed.cost, 2) for listed in stations] == [84.33, 88.75]


def test_time_that_costs_nothing_orders_by_price(store, no_correction):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,689"})
    insert_station(store, 2, 40.43, -3.70, {"Precio Gasoleo A": "1,699"})
    route = planned()
    router = StubRouter(route, {(-3.70, 40.42): detour(route.duration + 1800),
                                (-3.70, 40.43): detour(route.duration + 60)})

    stations = search(router, parameters=replace(DIESEL, eur_per_hour=0.0)).stations

    assert [listed.station.id for listed in stations] == [1, 2]


def test_ten_of_thirty(store):
    for station_id in range(1, 31):
        insert_station(store, station_id, 40.42 + station_id / 1000, -3.70, {"Precio Gasoleo A": "1,800"})

    assert len(search(StubRouter(planned())).stations) == 10


# The arrival, the time zone, and the link


def test_the_arrival_time(store, no_correction):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"})
    router = StubRouter(planned(), {(-3.70, 40.42): detour(6000.0, to_station_s=5400.0)})

    [listed] = search(router).stations

    assert listed.arrival == datetime.datetime(2026, 11, 7, 19, 30, tzinfo=datetime.timezone.utc)


@pytest.mark.parametrize("province, local_time", [("SANTA CRUZ DE TENERIFE", "20:30"), ("PALMAS (LAS)", "20:30"),
                                                  ("MADRID", "21:30")])
def test_the_time_zone_of_a_station(province, local_time):
    arrival = datetime.datetime(2026, 11, 7, 20, 30, tzinfo=datetime.timezone.utc)

    assert arrival.astimezone(refuel.station_zone(province)).strftime("%H:%M") == local_time


def test_the_opening_state_uses_the_local_arrival(store, no_correction):
    insert_station(store, 1, 40.42, -3.70, {"Precio Gasoleo A": "1,800"}, hours="L-D: 06:00-19:40")
    router = StubRouter(planned(), {(-3.70, 40.42): detour(6000.0, to_station_s=1800.0)})

    [listed] = search(router).stations

    assert listed.arrival.strftime("%H:%M") == "19:30"
    assert listed.state == OpeningState("closing_soon", listed.arrival + datetime.timedelta(minutes=10))


def test_the_link_of_a_station():
    assert refuel.station_link(39.211417, -1.539167) == (
        "https://www.google.com/maps/search/?api=1&query=39.211417%2C-1.539167")
