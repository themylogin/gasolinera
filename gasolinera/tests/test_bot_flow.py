# -*- coding=utf-8 -*-
"""Whole conversations through the real Application, the fake Telegram, and a fake OSRM."""
import asyncio
import json
import sqlite3

import httpx
import pytest

from .. import bot, car
from ..journey import INFO
from ..osrm import Router
from .telegram import USER_ID, Chat

ORIGIN = (-3.70, 40.42)
DESTINATION = (-3.60, 40.50)
AT_SEA = (-5.0, 36.0)

ASK_TANK = "Escribe el volumen del depósito en litros."
ASK_FUEL = "Elige el tipo de combustible."
ASK_80 = "Escribe el consumo a 80 km/h en litros por 100 km."
ASK_120 = "Escribe el consumo a 120 km/h en litros por 100 km."
ASK_TIME = "¿Cuánto vale tu tiempo? Escríbelo en €/h, por ejemplo 20."
ASK_DESTINATION = "Ahora envíame el destino."
ASK_LITERS = "¿Cuántos litros de combustible te quedan?"
EXPIRED = "Esta pregunta ha caducado. Envía /coche para empezar de nuevo."
SAVED_DIESEL = ("Tu coche está guardado.\n\n"
                "Depósito: 50 L\nCombustible: Diésel\nA 80 km/h: 5,8 L/100 km\nA 120 km/h: 7 L/100 km\n"
                "Tu tiempo: 20 €/h")


class Osrm:
    """Answers /nearest and /route like the osrm service, and can fail on demand."""

    def __init__(self):
        self.planned = "ok"
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if path.startswith("/nearest/"):
            longitude, latitude = (float(value) for value in path.rsplit("/", 1)[-1].split(","))
            distance = 5.0
            if (longitude, latitude) == AT_SEA:
                distance = 5000.0
            return httpx.Response(200, json={"code": "Ok", "waypoints": [{"distance": distance}]})

        if "annotations" in request.url.params:
            if self.planned == "down":
                return httpx.Response(502, content=b"<html>Bad Gateway</html>")
            if self.planned == "no_route":
                return httpx.Response(400, json={"code": "NoRoute", "message": "Impossible route"})
            return httpx.Response(200, json={"code": "Ok", "routes": [{
                "distance": 1000.0, "duration": 40.0,
                "geometry": {"coordinates": [list(ORIGIN), [-3.699, 40.42]]},
                "legs": [{"distance": 1000.0, "duration": 40.0,
                          "annotation": {"distance": [1000.0], "duration": [40.0]}}],
            }]})

        return httpx.Response(200, json={"code": "Ok", "routes": [{
            "distance": 3000.0, "duration": 160.0,
            "legs": [{"distance": 1500.0, "duration": 80.0}, {"distance": 1500.0, "duration": 80.0}],
        }]})


@pytest.fixture
def osrm():
    return Osrm()


def talk(osrm, scenario):
    async def run():
        router = Router("http://osrm:5000", transport=httpx.MockTransport(osrm))
        async with Chat(bot.build, router=router) as chat:
            await scenario(chat)
            return chat

    return asyncio.run(run())


def store_car(db_path, tank_volume=50, fuel_type="diesel"):
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO car VALUES (?, ?, ?, 5.8, 7.0, 20.0)", (USER_ID, tank_volume, fuel_type))


def stored_cars(db_path):
    with sqlite3.connect(db_path) as connection:
        return connection.execute("SELECT * FROM car").fetchall()


def store_station(db_path, hours="L-D: 24H"):
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO gas_station VALUES (1, 40.42, -3.70, 'REPSOL', '', '', '', '', 'MADRID', ?, ?, "
            "'2026-11-07 10:00:00')",
            (hours, json.dumps({"Precio Gasoleo A": "1,689"})),
        )


async def enter_car(chat):
    await chat.send_command("coche")
    await chat.send_text("50")
    await chat.press_labelled("Diésel")
    await chat.send_text("5,8")
    await chat.send_text("7")
    await chat.send_text("20")


# /coche


def test_a_new_car(store, osrm):
    chat = talk(osrm, enter_car)

    assert chat.texts() == [ASK_TANK, "Combustible: Diésel", ASK_80, ASK_120, ASK_TIME, SAVED_DIESEL]
    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0)]


def test_the_fuel_question_has_three_buttons(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")

    chat = talk(osrm, scenario)

    question = chat.telegram.messages[-1]
    assert question.text == ASK_FUEL
    assert [[button["text"] for button in row] for row in question.markup["inline_keyboard"]] == [
        ["Gasolina 95"], ["Gasolina 98"], ["Diésel"]]


def test_text_instead_of_a_fuel_button(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.send_text("diesel")

    assert talk(osrm, scenario).texts()[-1] == "Elige el tipo de combustible con un botón."


def test_coordinates_during_the_consumption_question(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("Diésel")
        await chat.send_text("40.42, -3.70")

    assert talk(osrm, scenario).texts()[-1] == (
        "El consumo debe ser un número mayor que 0 y menor que 30, por ejemplo 6,5. Escríbelo de nuevo.")


def test_a_user_with_a_car_keeps_it(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_command("coche")
        await chat.press_labelled("No")

    chat = talk(osrm, scenario)

    assert chat.texts()[0] == ("Tu coche:\n\n"
                               "Depósito: 50 L\nCombustible: Diésel\nA 80 km/h: 5,8 L/100 km\nA 120 km/h: 7 L/100 km\n"
                               "Tu tiempo: 20 €/h\n\n¿Quieres cambiarlo?")
    assert chat.texts()[-1] == "Tu coche no ha cambiado."
    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0)]


def test_a_user_with_a_car_changes_it(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_command("coche")
        await chat.press_labelled("Sí")
        await chat.send_text("60")
        await chat.press_labelled("Gasolina 95")
        await chat.send_text("6")
        await chat.send_text("8")
        await chat.send_text("15")

    talk(osrm, scenario)

    assert stored_cars(store) == [(USER_ID, 60, "gasoline_95", 6.0, 8.0, 15.0)]


def test_a_dialog_that_stops_changes_no_car(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_command("coche")
        await chat.press_labelled("Sí")
        await chat.send_text("50")
        await chat.press_labelled("Gasolina 98")
        await chat.send_command("reiniciar")

    talk(osrm, scenario)

    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0)]


def test_coche_twice_starts_again(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("Gasolina 95")
        await chat.send_command("coche")

    assert talk(osrm, scenario).texts()[-1] == ASK_TANK


def test_an_old_button_changes_nothing(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("Gasolina 98", nth_from_end=1)
        await chat.send_text("6")

    chat = talk(osrm, scenario)

    assert chat.texts()[-2] == EXPIRED
    assert chat.texts()[-1] == "Elige el tipo de combustible con un botón."
    assert any(sent.method == "editMessageReplyMarkup" for sent in chat.sent)


def test_a_failed_save(store, osrm, monkeypatch):
    async def failing_save(_user_id, _parameters):
        raise RuntimeError("disk full")

    monkeypatch.setattr(car, "save_car", failing_save)

    async def scenario(chat):
        await enter_car(chat)
        await chat.send_text("hola")

    chat = talk(osrm, scenario)

    assert chat.texts()[-2] == "No he podido guardar tu coche. Lo siento mucho 😞"
    assert chat.texts()[-1] == INFO


# The journey


def test_a_complete_journey(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        await chat.send_text("5")

    chat = talk(osrm, scenario)

    assert chat.texts()[:2] == [ASK_DESTINATION, ASK_LITERS]
    answer = chat.sent[-1]
    assert answer.text.startswith("1. <a ")
    assert "\n1,689 €/L · " in answer.text
    assert answer.parameters["parse_mode"] == "HTML"
    assert answer.parameters["link_preview_options"] == {"is_disabled": True}


def test_typed_coordinates_are_a_location(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_text("40.42, -3.70")

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION]


def test_a_location_during_the_car_dialog_goes_to_the_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_command("coche")
        await chat.press_labelled("Sí")
        await chat.send_location(ORIGIN)

    assert talk(osrm, scenario).texts()[-1] == ASK_DESTINATION


def test_the_journey_needs_a_car(store, osrm):
    async def scenario(chat):
        await chat.send_location(ORIGIN)
        store_car(store)
        await chat.send_location(DESTINATION)

    assert talk(osrm, scenario).texts() == ["Primero dime cómo es tu coche con /coche.", ASK_DESTINATION]


def test_a_location_far_from_the_road_is_refused(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(AT_SEA)
        await chat.send_location(DESTINATION)

    assert talk(osrm, scenario).texts() == [
        ASK_DESTINATION,
        "🇪🇸 Esta ubicación no está a menos de 1 km de ninguna carretera de España.",
        ASK_LITERS,
    ]


def test_liters_with_a_decimal_comma(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        await chat.send_text("12,5")

    assert talk(osrm, scenario).texts()[-1] == "No necesitas repostar: llegarás con 12 L."


def test_more_liters_than_the_tank(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        await chat.send_text("60")
        await chat.send_text("12,5")

    assert talk(osrm, scenario).texts()[-2:] == [
        "Los litros deben ser un número de 0 a 50, por ejemplo 12,5. Escríbelo de nuevo.",
        "No necesitas repostar: llegarás con 12 L.",
    ]


def test_a_location_during_the_fuel_question_starts_a_new_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        await chat.send_location(DESTINATION)
        await chat.send_location(ORIGIN)

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION, ASK_LITERS, ASK_DESTINATION, ASK_LITERS]


def test_the_answer_ends_the_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        await chat.send_text("20")
        await chat.send_location(ORIGIN)

    assert talk(osrm, scenario).texts()[-1] == ASK_DESTINATION


def test_reiniciar_resets_the_journey_but_not_the_car(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_command("reiniciar")
        await chat.send_location(DESTINATION)

    chat = talk(osrm, scenario)

    assert chat.texts() == [ASK_DESTINATION, "Envíame tu ubicación actual.", ASK_DESTINATION]
    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0)]


@pytest.mark.parametrize("send", [
    lambda chat: chat.send_text("hola"),
    lambda chat: chat.send_command("start"),
    lambda chat: chat.send_command("info"),
    lambda chat: chat.send_command("ayuda"),
])
def test_the_info_text(store, osrm, send):
    async def scenario(chat):
        await send(chat)

    chat = talk(osrm, scenario)

    assert chat.texts() == [INFO]
    assert chat.sent[-1].parameters["link_preview_options"] == {"is_disabled": True}


def test_info_keeps_the_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_command("info")
        await chat.send_location(DESTINATION)

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION, INFO, ASK_LITERS]


def test_a_router_that_is_down_keeps_the_fuel_question(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        osrm.planned = "down"
        await chat.send_text("10")
        osrm.planned = "ok"
        await chat.send_text("10")

    assert talk(osrm, scenario).texts()[-2:] == [
        "No he podido calcular la ruta. Lo siento mucho 😞",
        "No necesitas repostar: llegarás con 9 L.",
    ]


def test_no_route_between_the_two_points_forgets_the_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        osrm.planned = "no_route"
        await chat.send_text("10")
        await chat.send_location(ORIGIN)

    assert talk(osrm, scenario).texts()[-2:] == [
        "No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.",
        ASK_DESTINATION,
    ]
