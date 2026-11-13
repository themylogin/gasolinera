# -*- coding=utf-8 -*-
"""The store is a real SQLite file in a temporary directory, migrated by Alembic.
The triggers and the R*Tree index exist only in the revision, so a schema built
from the models would test neither.

The source is an httpx mock transport. No test reaches MITECO.
"""
import asyncio
import copy
import datetime
import json
import logging
from pathlib import Path
import sqlite3

import httpx
import pytest
from sqlalchemy import event

from .. import db, gas_stations


@pytest.fixture
def feed():
    return json.loads((Path(__file__).parent / "miteco_sample.json").read_text(encoding="utf-8"))


def entry(feed, station_id):
    return copy.deepcopy(next(row for row in feed["ListaEESSPrecio"] if row["IDEESS"] == station_id))


class Source:
    def __init__(self, status=200, body=None, error=None):
        self.status = status
        self.body = body
        self.error = error
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return httpx.Response(self.status, content=self.body)


def run(body=None, status=200, error=None):
    if not isinstance(body, (bytes, type(None))):
        body = json.dumps(body).encode("utf-8")
    source = Source(status, body, error)
    status = asyncio.run(gas_stations.update(transport=httpx.MockTransport(source)))
    return status, source


def rows(db_path):
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in connection.execute("SELECT * FROM gas_station")}


def insert_station(db_path, station_id, latitude, longitude, prices="{}"):
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO gas_station"
            " (id, latitude, longitude, name, address, postal_code, locality, municipality, province,"
            "  opening_hours, prices, updated_at)"
            " VALUES (?, ?, ?, '', '', '', '', '', '', '', ?, '2026-11-01 10:00:00')",
            (station_id, latitude, longitude, prices),
        )


def index_entries(db_path, station_id):
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            "SELECT min_latitude, max_latitude, min_longitude, max_longitude FROM gas_station_area WHERE id = ?",
            (station_id,),
        ).fetchall()


# The request


def test_one_request_to_the_full_list(store, feed):
    status, source = run(feed)

    assert status == 0
    [request] = source.requests
    assert request.method == "GET"
    assert str(request.url) == (
        "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    )
    assert request.headers["Accept"] == "application/json"


# The entries


def test_a_listed_station_is_stored_under_its_id(store, feed):
    run(feed)

    assert 4375 in rows(store)


def test_the_position_is_converted_from_the_decimal_comma(store, feed):
    run(feed)

    station = rows(store)[4375]
    assert station["latitude"] == 39.211417
    assert station["longitude"] == -1.539167


def test_a_station_at_0_0_is_skipped_and_logged(store, feed, caplog):
    with caplog.at_level(logging.WARNING):
        status, _ = run(feed)

    assert status == 0
    assert 11988 not in rows(store)
    assert "Station 11988 skipped" in caplog.text


def test_swapped_coordinates_are_skipped_and_logged(store, feed, caplog):
    with caplog.at_level(logging.WARNING):
        run(feed)

    assert 16268 not in rows(store)
    assert "Station 16268 skipped" in caplog.text


def test_a_station_in_the_canary_islands_is_stored(store, feed):
    canary = entry(feed, "7901")
    canary["Latitud"] = "27,7"
    canary["Longitud (WGS84)"] = "-18,0"
    feed["ListaEESSPrecio"] = [canary]

    run(feed)

    assert rows(store)[7901]["latitude"] == 27.7


@pytest.mark.parametrize("field, value", [("IDEESS", "x"), ("Latitud", ""), ("Rótulo", None)])
def test_an_entry_that_cannot_be_read_is_skipped(store, feed, field, value):
    broken = entry(feed, "4375") | {"IDEESS": "1"}
    broken[field] = value
    feed["ListaEESSPrecio"].append(broken)

    status, _ = run(feed)

    assert status == 0
    assert sorted(rows(store)) == [4375, 7901]


def test_an_entry_without_a_field_is_skipped(store, feed):
    broken = entry(feed, "4375") | {"IDEESS": "1"}
    del broken["Horario"]
    feed["ListaEESSPrecio"].append(broken)

    run(feed)

    assert sorted(rows(store)) == [4375, 7901]


def test_an_entry_that_is_not_an_object_is_skipped(store, feed):
    feed["ListaEESSPrecio"].append("junk")

    status, _ = run(feed)

    assert status == 0
    assert sorted(rows(store)) == [4375, 7901]


def test_the_descriptive_fields_are_stored_as_text(store, feed):
    run(feed)

    station = rows(store)[4375]
    assert station["name"] == "Nº 10.935"
    assert station["address"] == "AVENIDA CASTILLA LA MANCHA, 26"
    assert station["postal_code"] == "02250"
    assert station["locality"] == "ABENGIBRE"
    assert station["municipality"] == "Abengibre"
    assert station["province"] == "ALBACETE"
    assert station["opening_hours"] == "L-D: 07:00-22:00"


def test_only_the_sold_fuels_are_stored_unchanged(store, feed):
    station = entry(feed, "4375")
    for field in station:
        if field.startswith("Precio "):
            station[field] = ""
    station["Precio Gasoleo A"] = "1,799"
    station["Precio Gasolina 95 E5"] = "1,649"
    feed["ListaEESSPrecio"] = [station]

    run(feed)

    assert json.loads(rows(store)[4375]["prices"]) == {"Precio Gasoleo A": "1,799", "Precio Gasolina 95 E5": "1,649"}


def test_an_unknown_price_field_is_stored(store, feed):
    feed["ListaEESSPrecio"][0]["Precio Gasolina 100"] = "2,100"

    run(feed)

    assert json.loads(rows(store)[4375]["prices"])["Precio Gasolina 100"] == "2,100"


def test_every_row_has_the_time_of_the_run(store, feed):
    start = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    run(feed)
    end = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    times = {datetime.datetime.fromisoformat(station["updated_at"]) for station in rows(store).values()}
    [updated_at] = times
    assert start <= updated_at <= end


# The replacement


def test_a_station_that_leaves_the_list_is_deleted(store, feed):
    insert_station(store, 9999, 40.0, -3.0)

    run(feed)

    assert 9999 not in rows(store)
    assert index_entries(store, 9999) == []


def test_a_changed_price_replaces_the_stored_one(store, feed):
    run(feed)
    feed["ListaEESSPrecio"][0]["Precio Gasoleo A"] = "1,759"

    run(feed)

    assert json.loads(rows(store)[4375]["prices"])["Precio Gasoleo A"] == "1,759"


@pytest.mark.parametrize("status, body, error", [
    (503, b"", None),
    (204, b"", None),
    (200, b"<html>", None),
    (200, b"[]", None),
    (200, json.dumps({"ResultadoConsulta": "OK", "ListaEESSPrecio": []}).encode(), None),
    (200, json.dumps({"ResultadoConsulta": "Error", "ListaEESSPrecio": []}).encode(), None),
    (200, json.dumps({"ResultadoConsulta": "OK"}).encode(), None),
    (200, None, httpx.ConnectError("refused")),
    (200, None, httpx.ReadTimeout("slow")),
])
def test_a_list_that_cannot_be_read_changes_nothing(store, status, body, error):
    insert_station(store, 9999, 40.0, -3.0)
    before = rows(store)

    exit_status, _ = run(body, status, error)

    assert exit_status != 0
    assert rows(store) == before


def test_a_list_with_no_valid_entry_changes_nothing(store, feed):
    insert_station(store, 9999, 40.0, -3.0)
    feed["ListaEESSPrecio"] = [entry(feed, "11988"), entry(feed, "16268")]

    status, _ = run(feed)

    assert status != 0
    assert list(rows(store)) == [9999]


def store_100_stations(db_path):
    for station_id in range(1001, 1101):
        insert_station(db_path, station_id, 40.0, -3.0)


def list_of(feed, valid, skipped=0):
    valid_entries = [entry(feed, "4375") | {"IDEESS": str(station_id)} for station_id in range(1, valid + 1)]
    skipped_entries = [entry(feed, "11988") | {"IDEESS": str(station_id)} for station_id in range(501, 501 + skipped)]
    feed["ListaEESSPrecio"] = valid_entries + skipped_entries
    return feed


def test_a_truncated_list_changes_nothing(store, feed, caplog):
    store_100_stations(store)
    before = rows(store)

    with caplog.at_level(logging.ERROR):
        status, _ = run(list_of(feed, 89))

    assert status != 0
    assert rows(store) == before
    assert "The list has 89 stations, fewer than 90% of the 100 stored ones; the store is unchanged" in caplog.text


def test_a_list_at_the_limit_replaces_the_store(store, feed):
    store_100_stations(store)

    status, _ = run(list_of(feed, 90))

    assert status == 0
    assert sorted(rows(store)) == list(range(1, 91))


def test_a_list_with_many_skipped_entries_changes_nothing(store, feed):
    store_100_stations(store)
    before = rows(store)

    status, _ = run(list_of(feed, 89, skipped=11))

    assert status != 0
    assert rows(store) == before


def test_the_first_run_fills_an_empty_store(store, feed):
    status, _ = run(feed)

    assert status == 0
    assert sorted(rows(store)) == [4375, 7901]


def test_the_run_logs_the_feed_date_and_the_counts(store, feed, caplog):
    with caplog.at_level(logging.INFO):
        run(feed)

    assert "Feed of 07/11/2026 20:33:08: 4 entries, 2 stored, 2 skipped" in caplog.text


def test_main_exits_with_the_status_of_the_run(monkeypatch):
    async def failed_update():
        return 1

    monkeypatch.setattr(gas_stations, "update", failed_update)

    with pytest.raises(SystemExit) as exit_info:
        gas_stations.main()

    assert exit_info.value.code == 1


# The area query


def area_ids(south, west, north, east):
    return sorted(station.id for station in asyncio.run(gas_stations.stations_in_area(south, west, north, east)))


def test_the_area_holds_only_the_stations_in_the_box(store):
    insert_station(store, 1, 40.42, -3.70)
    insert_station(store, 2, 41.39, 2.17)

    assert area_ids(40.0, -4.0, 41.0, -3.0) == [1]


def test_a_station_on_the_edge_is_in_the_area(store):
    insert_station(store, 1, 40.0, -3.0)

    assert area_ids(40.0, -4.0, 41.0, -3.0) == [1]


def test_a_station_just_outside_the_box_is_not_in_the_area(store):
    insert_station(store, 1, 41.0000001, -3.5)

    assert area_ids(40.0, -4.0, 41.0, -3.0) == []


def test_the_area_query_reads_the_index(store):
    statements = []
    engine = db.Session.kw["bind"].sync_engine
    event.listen(engine, "before_cursor_execute",
                 lambda _connection, _cursor, statement, parameters, *_: statements.append((statement, parameters)))

    asyncio.run(gas_stations.stations_in_area(40.0, -4.0, 41.0, -3.0))

    [(statement, parameters)] = statements
    with sqlite3.connect(store) as connection:
        plan = [detail for (*_, detail) in connection.execute("EXPLAIN QUERY PLAN " + statement, parameters)]
    assert any(detail.startswith("SCAN gas_station_area VIRTUAL TABLE INDEX") for detail in plan)
    assert "SEARCH gas_station USING INTEGER PRIMARY KEY (rowid=?)" in plan


# The triggers keep the index equal to the table, whatever code writes the table.
# These tests write with plain sqlite3 on purpose.


def test_an_inserted_station_is_indexed_at_its_position(store):
    insert_station(store, 4375, 39.211417, -1.539167)

    [(min_latitude, max_latitude, min_longitude, max_longitude)] = index_entries(store, 4375)
    assert min_latitude == pytest.approx(39.211417, abs=1e-5)
    assert max_latitude == pytest.approx(39.211417, abs=1e-5)
    assert min_longitude == pytest.approx(-1.539167, abs=1e-5)
    assert max_longitude == pytest.approx(-1.539167, abs=1e-5)


def test_a_moved_station_is_indexed_at_its_new_position(store):
    insert_station(store, 4375, 39.211417, -1.539167)

    with sqlite3.connect(store) as connection:
        connection.execute("UPDATE gas_station SET latitude = 41.39, longitude = 2.17 WHERE id = 4375")

    [(min_latitude, _, min_longitude, _)] = index_entries(store, 4375)
    assert min_latitude == pytest.approx(41.39, abs=1e-5)
    assert min_longitude == pytest.approx(2.17, abs=1e-5)


def test_a_deleted_station_leaves_the_index(store):
    insert_station(store, 4375, 39.211417, -1.539167)

    with sqlite3.connect(store) as connection:
        connection.execute("DELETE FROM gas_station WHERE id = 4375")

    assert index_entries(store, 4375) == []
