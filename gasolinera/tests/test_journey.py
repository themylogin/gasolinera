# -*- coding=utf-8 -*-
import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from .. import journey
from ..models import GasStation
from ..opening_hours import OpeningState
from ..refuel import Listed, NoStop, Stops

MADRID = ZoneInfo("Europe/Madrid")


def listed(name="REPSOL", price="1.689", field="Precio Gasoleo A", distance_m=312400.0, detour_s=185.0,
           state=OpeningState("open"), hours="L-D: 24H", arrival=datetime.datetime(2026, 11, 7, 21, 45, tzinfo=MADRID)):
    station = GasStation(id=1, latitude=39.211417, longitude=-1.539167, name=name, opening_hours=hours,
                         province="MADRID")
    return Listed(station=station, field=field, price=Decimal(price), distance_m=distance_m, detour_s=detour_s,
                  arrival=arrival, cost=0.0, state=state)


def station_block(entry):
    return journey.format_answer(Stops(liters=45.0, stations=(entry,)), "Diésel")


@pytest.mark.parametrize("text, location", [
    ("40.4168, -3.7038", (-3.7038, 40.4168)),
    ("-28.1, -15.4", (-15.4, -28.1)),
    ("Estoy en 41.3874,2.1686 ahora", (2.1686, 41.3874)),
])
def test_typed_coordinates(text, location):
    assert journey.parse_location(text) == location


def test_a_decimal_comma_reads_as_coordinates():
    # This is why the bot reads a range first when the fuel question is open.
    assert journey.parse_location("12,5") == (5.0, 12.0)


@pytest.mark.parametrize("text", ["hola", "40.4", "95.0, 3.0", "40.0, 190.0"])
def test_text_that_is_no_location(text):
    assert journey.parse_location(text) is None


def labels(steps):
    return [[label for label, _step in row] for row in journey.GAUGES[steps]]


def steps_of(steps):
    return [[step for _label, step in row] for row in journey.GAUGES[steps]]


def test_the_24_step_gauge():
    assert labels(24) == [
        ["1", ".", ".", "|", ".", ".", "3/4"],
        ["3/4", ".", ".", "|", ".", ".", "1/2"],
        ["1/2", ".", ".", "|", ".", ".", "1/4"],
        ["1/4", ".", ".", "|", ".", ".", "0"],
    ]
    assert steps_of(24) == [
        [24, 23, 22, 21, 20, 19, 18],
        [18, 17, 16, 15, 14, 13, 12],
        [12, 11, 10, 9, 8, 7, 6],
        [6, 5, 4, 3, 2, 1, 0],
    ]


def test_the_16_step_gauge():
    assert labels(16) == [
        ["1", ".", "|", ",", "3/4"],
        ["3/4", ".", "|", ",", "1/2"],
        ["1/2", ".", "|", ",", "1/4"],
        ["1/4", ".", "|", ",", "0"],
    ]
    assert steps_of(16) == [[16, 15, 14, 13, 12], [12, 11, 10, 9, 8], [8, 7, 6, 5, 4], [4, 3, 2, 1, 0]]


def test_the_12_step_gauge():
    assert labels(12) == [
        ["1", ".", "5/6", ".", "2/3", ".", "1/2"],
        ["1/2", ".", "1/3", ".", "1/6", ".", "0"],
    ]
    assert steps_of(12) == [[12, 11, 10, 9, 8, 7, 6], [6, 5, 4, 3, 2, 1, 0]]


@pytest.mark.parametrize("steps", [24, 16, 12])
def test_a_row_repeats_the_end_of_the_row_before(steps):
    rows = journey.GAUGES[steps]

    assert all(row[0] == before[-1] for before, row in zip(rows, rows[1:]))


@pytest.mark.parametrize("step, steps, mark", [(24, 24, "1"), (0, 24, "0"), (21, 24, "7/8"), (10, 12, "5/6"),
                                               (13, 16, "13/16"), (12, 16, "3/4")])
def test_gauge_marks(step, steps, mark):
    assert journey.gauge_mark(step, steps) == mark


@pytest.mark.parametrize("text, range_km", [("120", 120.0), ("87,5", 87.5), ("0", 0.0), ("3000", 3000.0),
                                            (" 7.25 ", 7.25)])
def test_a_range(text, range_km):
    assert journey.parse_range(text) == range_km


@pytest.mark.parametrize("text", ["3001", "-1", "mucho", "", "40.42, -3.70", "1/2"])
def test_text_that_is_not_a_range(text):
    assert journey.parse_range(text) is None


def test_the_info_text():
    assert journey.INFO == (
        "Este bot busca dónde repostar más barato en tu ruta por España.\n"
        "\n"
        "1. Configura tu coche con /coche.\n"
        "2. Envíame tu ubicación actual.\n"
        "3. Envíame el destino.\n"
        "4. Dime cuántos litros te quedan.\n"
        "\n"
        "Te mostraré las 10 paradas más baratas, contando el combustible y el tiempo del desvío, y te avisaré si "
        "una gasolinera estará cerrada o a punto de cerrar cuando llegues.\n"
        "\n"
        "/coche: configurar tu coche\n"
        "/reiniciar: empezar de nuevo\n"
        "/info: esta información\n"
        "\n"
        "Puedes decirme gracias aquí: https://buymeacoffee.com/themylogin o https://paypal.me/themyloginspain"
    )


def test_no_stop_is_needed():
    assert journey.format_answer(NoStop(fuel_left=12.7), "Diésel") == "No necesitas repostar: llegarás con 12 L."


def test_no_stop_is_needed_with_a_range():
    assert journey.format_answer(NoStop(range_left=83.4), "Diésel") == (
        "No necesitas repostar: llegarás con 83 km de autonomía.")


def test_no_station_is_near():
    assert journey.format_answer(Stops(liters=45.0, stations=()), "Diésel") == (
        "Ninguna gasolinera vende Diésel a menos de 50 km del punto donde el depósito llega a 5 L.")


def test_the_stations_start_the_message():
    text = journey.format_answer(Stops(liters=44.6, stations=(listed(),) * 10), "Gasolina 95")

    assert text.startswith("1. <a ")
    assert "\n\n10. <a " in text


def test_one_open_station():
    entry = listed(name="GALP", price="1.499", distance_m=410300.0, detour_s=100.0)

    assert station_block(entry) == (
        '1. <a href="https://www.google.com/maps/search/?api=1&amp;query=39.211417%2C-1.539167">GALP</a>'
        " · 410 km\n"
        "1,499 €/L · +2 min"
    )


def test_a_shorter_route_through_the_station():
    assert station_block(listed(detour_s=-70.0)).endswith(" · -1 min")


def test_a_name_with_html_characters():
    assert ">A&amp;B &lt;24h&gt;</a>" in station_block(listed(name="A&B <24h>"))


def test_no_name():
    assert ">Gasolinera sin nombre</a>" in station_block(listed(name=""))


def test_closed():
    arrival = datetime.datetime(2026, 11, 7, 22, 41, tzinfo=MADRID)

    assert station_block(listed(state=OpeningState("closed"), arrival=arrival)).endswith(
        "\n⚠️ <b>Cerrada</b> a las 22:41")


def test_closing_soon():
    state = OpeningState("closing_soon", datetime.datetime(2026, 11, 7, 22, 0, tzinfo=MADRID))

    assert station_block(listed(state=state)).endswith("\n⚠️ <b>Cierra pronto</b> a las 22:00")


@pytest.mark.parametrize("hours", ["L: 24H", ""])
def test_an_unknown_schedule(hours):
    assert station_block(listed(state=OpeningState("unknown"), hours=hours)).endswith(
        "\n⚠️ <b>Horario desconocido</b>")
