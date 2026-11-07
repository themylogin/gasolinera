# -*- coding=utf-8 -*-
import asyncio
import json
import math

import httpx
import pytest

from ..osrm import NoRoute, Router, RouterUnavailable


class Source:
    def __init__(self, body=None, status=200, error=None):
        self.body = body
        self.status = status
        self.error = error
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if isinstance(self.body, bytes):
            return httpx.Response(self.status, content=self.body)
        return httpx.Response(self.status, json=self.body)


def router(source):
    return Router("http://osrm:5000", transport=httpx.MockTransport(source))


def one_leg(distances=(100.0, 200.0), durations=(10.0, 20.0), points=3):
    return {
        "code": "Ok",
        "routes": [{
            "distance": 300.0,
            "duration": 30.0,
            "geometry": {"coordinates": [[-3.7, 40.4], [-3.699, 40.4], [-3.698, 40.4], [-3.697, 40.4]][:points]},
            "legs": [{"distance": 300.0, "duration": 30.0,
                      "annotation": {"distance": list(distances), "duration": list(durations)}}],
        }],
    }


def test_nearest_request_and_distance():
    source = Source({"code": "Ok", "waypoints": [{"distance": 12.5, "location": [-3.7, 40.4]}]})

    distance = asyncio.run(router(source).distance_to_road((-3.7038, 40.4168)))

    assert distance == 12.5
    [request] = source.requests
    assert str(request.url) == "http://osrm:5000/nearest/v1/driving/-3.703800,40.416800?number=1"


def test_nearest_without_a_waypoint_is_infinitely_far():
    assert asyncio.run(router(Source({"code": "Ok", "waypoints": []})).distance_to_road((0.0, 0.0))) == math.inf


def test_route_with_segments():
    source = Source(one_leg())

    route = asyncio.run(router(source).route([(-3.7038, 40.4168), (2.1686, 41.3874)], segments=True))

    [request] = source.requests
    assert request.url.path == "/route/v1/driving/-3.703800,40.416800;2.168600,41.387400"
    assert dict(request.url.params) == {
        "overview": "full", "steps": "false", "geometries": "geojson", "annotations": "distance,duration"}
    assert route.distance == 300.0
    assert route.duration == 30.0
    assert route.coordinates == ((-3.7, 40.4), (-3.699, 40.4), (-3.698, 40.4))
    assert route.segment_distance == (100.0, 200.0)
    assert route.segment_duration == (10.0, 20.0)


def test_route_with_two_legs():
    source = Source({"code": "Ok", "routes": [{
        "distance": 500.0, "duration": 50.0,
        "legs": [{"distance": 150.0, "duration": 15.0}, {"distance": 350.0, "duration": 35.0}],
    }]})

    route = asyncio.run(router(source).route([(-3.7, 40.4), (-3.6, 40.5), (-3.5, 40.6)]))

    [request] = source.requests
    assert dict(request.url.params) == {"overview": "false", "steps": "false"}
    assert route.leg_distance == (150.0, 350.0)
    assert route.leg_duration == (15.0, 35.0)
    assert route.coordinates == ()


@pytest.mark.parametrize("code", ["NoRoute", "NoSegment"])
def test_no_route(code):
    with pytest.raises(NoRoute):
        asyncio.run(router(Source({"code": code, "message": "x"}, status=400)).route([(0, 0), (1, 1)]))


@pytest.mark.parametrize("source", [
    Source({"code": "InvalidQuery", "message": "x"}, status=400),
    Source(b"<html>Bad Gateway</html>", status=502),
    Source(error=httpx.ConnectError("refused")),
    Source(one_leg(points=4)),
    Source(one_leg(durations=(10.0,))),
])
def test_router_unavailable(source):
    with pytest.raises(RouterUnavailable):
        asyncio.run(router(source).route([(0, 0), (1, 1)], segments=True))


def test_an_answer_without_routes_is_no_route():
    with pytest.raises(NoRoute):
        asyncio.run(router(Source({"code": "Ok", "routes": []})).route([(0, 0), (1, 1)]))


def test_the_body_is_read_whatever_the_content_type():
    body = json.dumps({"code": "Ok", "waypoints": [{"distance": 1.0}]}).encode()

    assert asyncio.run(router(Source(body)).distance_to_road((0.0, 0.0))) == 1.0
