# -*- coding=utf-8 -*-
import asyncio
import datetime
import json
import logging
import sys

import httpx
from sqlalchemy import delete, func, insert, select

from . import db
from .config import config
from .models import GasStation, GasStationArea

__all__ = ["ParseError", "main", "parse_entry", "stations_in_area", "update"]

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


def parse_entry(entry, updated_at):
    latitude = float(entry["Latitud"].replace(",", "."))
    longitude = float(entry["Longitud (WGS84)"].replace(",", "."))
    if not (27.0 <= latitude <= 44.0 and -18.5 <= longitude <= 4.5):
        raise ValueError(f"the position {latitude}, {longitude} is outside Spain")

    texts = {
        "name": entry["Rótulo"],
        "address": entry["Dirección"],
        "postal_code": entry["C.P."],
        "locality": entry["Localidad"],
        "municipality": entry["Municipio"],
        "province": entry["Provincia"],
        "opening_hours": entry["Horario"],
    }
    if not all(isinstance(text, str) for text in texts.values()):
        raise ValueError("a descriptive field is not text")

    return {
        "id": int(entry["IDEESS"]),
        "latitude": latitude,
        "longitude": longitude,
        **texts,
        "prices": {
            field: text
            for field, text in entry.items()
            if field.startswith("Precio ") and isinstance(text, str) and text.strip()
        },
        "updated_at": updated_at,
    }


def _parse_feed(body, updated_at):
    try:
        feed = json.loads(body)
    except ValueError as error:
        raise ParseError(f"the answer is not JSON: {error}") from None

    if not isinstance(feed, dict):
        raise ParseError("the answer is not a JSON object")
    if feed.get("ResultadoConsulta") != "OK":
        raise ParseError(f"ResultadoConsulta is {feed.get('ResultadoConsulta')!r}")

    entries = feed.get("ListaEESSPrecio")
    if not isinstance(entries, list) or not entries:
        raise ParseError("ListaEESSPrecio is missing or empty")

    stations = []
    for entry in entries:
        try:
            stations.append(parse_entry(entry, updated_at))
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            station_id = None
            if isinstance(entry, dict):
                station_id = entry.get("IDEESS")
            logger.warning("Station %s skipped: %r", station_id, error)

    if not stations:
        raise ParseError("no entry is valid")

    return feed.get("Fecha"), len(entries), stations


async def stations_in_area(south, west, north, east):
    # The R*Tree keeps 32-bit floats and rounds each box outwards, so it can
    # match a station just outside the area. The index selects the candidates,
    # and the exact position in gas_station decides.
    query = (
        select(GasStation)
        .join(GasStationArea, GasStationArea.id == GasStation.id)
        .where(
            GasStationArea.max_latitude >= south,
            GasStationArea.min_latitude <= north,
            GasStationArea.max_longitude >= west,
            GasStationArea.min_longitude <= east,
            GasStation.latitude.between(south, north),
            GasStation.longitude.between(west, east),
        )
    )

    async with db.Session() as session:
        return list(await session.scalars(query))


async def update(transport=None):
    headers = {"Accept": "application/json", "User-Agent": "gasolinera"}
    try:
        async with asyncio.timeout(120), httpx.AsyncClient(transport=transport, headers=headers, timeout=120) as http:
            response = await http.get(
                "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
            )
    except (httpx.HTTPError, TimeoutError) as error:
        logger.error("Cannot read the station list: %r", error)
        return 1

    if response.status_code != 200:
        logger.error("Cannot read the station list: the status is %d", response.status_code)
        return 1

    try:
        feed_date, entry_count, stations = _parse_feed(response.content, _utcnow())
    except ParseError as error:
        logger.error("Cannot read the station list: %s", error)
        return 1

    async with db.Session() as session, session.begin():
        stored = await session.scalar(select(func.count()).select_from(GasStation))
        if len(stations) * 10 < stored * 9:
            logger.error("The list has %d stations, fewer than 90%% of the %d stored ones; the store is unchanged",
                         len(stations), stored)
            return 1
        await session.execute(delete(GasStation))
        await session.execute(insert(GasStation), stations)

    logger.info("Feed of %s: %d entries, %d stored, %d skipped",
                feed_date, entry_count, len(stations), entry_count - len(stations))
    return 0


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def main():
    logging.basicConfig(level=config.log_level, format="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s")
    # httpx logs every request at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    sys.exit(asyncio.run(update()))


if __name__ == "__main__":
    main()
