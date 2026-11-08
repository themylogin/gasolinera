# -*- coding=utf-8 -*-
from dataclasses import dataclass
import json
import math

import httpx

__all__ = ["NoRoute", "Route", "Router", "RouterUnavailable"]


class RouterUnavailable(Exception):
    pass


class NoRoute(Exception):
    pass


@dataclass(frozen=True)
class Route:
    distance: float
    duration: float
    leg_distance: tuple[float, ...]
    leg_duration: tuple[float, ...]
    # [longitude, latitude] per point. Empty unless segments were requested.
    coordinates: tuple[tuple[float, float], ...] = ()
    segment_distance: tuple[float, ...] = ()
    segment_duration: tuple[float, ...] = ()


class Router:
    def __init__(self, base_url, transport=None, exclude=None):
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.exclude = exclude

    async def distance_to_road(self, location):
        longitude, latitude = location
        body = await self._get(f"/nearest/v1/driving/{longitude:.6f},{latitude:.6f}", {"number": "1"})
        waypoints = body.get("waypoints") or []
        if not waypoints:
            return math.inf

        return float(waypoints[0]["distance"])

    async def route(self, points, *, segments=False):
        coordinates = ";".join(f"{longitude:.6f},{latitude:.6f}" for longitude, latitude in points)
        params = {"overview": "false", "steps": "false"}
        if segments:
            params = {"overview": "full", "steps": "false", "geometries": "geojson",
                      "annotations": "distance,duration"}
        if self.exclude is not None:
            params["exclude"] = self.exclude

        body = await self._get(f"/route/v1/driving/{coordinates}", params)
        try:
            return _read_route(body, segments)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise RouterUnavailable(f"the route answer cannot be read: {error!r}") from None

    async def _get(self, path, params):
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=30) as http:
                response = await http.get(f"{self.base_url}{path}", params=params)
        except httpx.HTTPError as error:
            raise RouterUnavailable(f"{self.base_url} did not answer: {error!r}") from None

        try:
            body = json.loads(response.content)
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise RouterUnavailable(f"{self.base_url} answered HTTP {response.status_code} without a JSON object")

        code = body.get("code")
        if code == "Ok":
            return body
        if code in ("NoRoute", "NoSegment"):
            raise NoRoute(f"{code}: {body.get('message', '')}")

        raise RouterUnavailable(f"{self.base_url} answered {code}: {body.get('message', '')}")


def _read_route(body, segments):
    routes = body.get("routes") or []
    if not routes:
        raise NoRoute("the router returned no route")

    route = routes[0]
    legs = route["legs"]
    answer = Route(
        distance=float(route["distance"]),
        duration=float(route["duration"]),
        leg_distance=tuple(float(leg["distance"]) for leg in legs),
        leg_duration=tuple(float(leg["duration"]) for leg in legs),
    )
    if not segments:
        return answer

    [leg] = legs
    coordinates = tuple((float(longitude), float(latitude))
                        for longitude, latitude in route["geometry"]["coordinates"])
    segment_distance = tuple(float(distance) for distance in leg["annotation"]["distance"])
    segment_duration = tuple(float(duration) for duration in leg["annotation"]["duration"])
    if len(segment_distance) != len(segment_duration) or len(coordinates) != len(segment_distance) + 1:
        raise RouterUnavailable(
            f"{len(coordinates)} points for {len(segment_distance)} segment distances"
            f" and {len(segment_duration)} segment durations"
        )

    return Route(
        distance=answer.distance,
        duration=answer.duration,
        leg_distance=answer.leg_distance,
        leg_duration=answer.leg_duration,
        coordinates=coordinates,
        segment_distance=segment_distance,
        segment_duration=segment_duration,
    )
