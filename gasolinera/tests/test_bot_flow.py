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
ASK_RESERVE = "¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50."
ASK_DESTINATION = "Ahora envíame el destino."
ASK_GAUGE = "¿Cuánto combustible te queda? Elige en el indicador o escribe los kilómetros de autonomía."
EXPIRED_GAUGE = "Esta pregunta ha caducado."
EXPIRED = "Esta pregunta ha caducado. Envía /coche para empezar de nuevo."
SAVED_DIESEL = ("Tu coche está guardado.\n\n"
                "Depósito: 50 L\nIndicador: 16 secciones\nCombustible: Diésel\nA 80 km/h: 5,8 L/100 km\nA 120 km/h: 7 L/100 km\n"
                "Tu tiempo: 20 €/h\nReserva: 50 km")


class Osrm:
    """Answers /nearest and /route like the osrm service, and can fail on demand."""

    def __init__(self):
        self.planned = "ok"
        self.tolls_s = 40.0
        # "same", "down", "no_route", or the duration in seconds of another route.
        self.toll_free = "same"
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
            if "exclude" not in request.url.params or self.toll_free == "same":
                return planned_route([list(ORIGIN), [-3.699, 40.42]], self.tolls_s)
            if self.toll_free == "down":
                return httpx.Response(502, content=b"<html>Bad Gateway</html>")
            if self.toll_free == "no_route":
                return httpx.Response(400, json={"code": "NoRoute", "message": "Impossible route"})
            return planned_route([list(ORIGIN), [-3.698, 40.43]], self.toll_free)

        return httpx.Response(200, json={"code": "Ok", "routes": [{
            "distance": 3000.0, "duration": 160.0,
            "legs": [{"distance": 1500.0, "duration": 80.0}, {"distance": 1500.0, "duration": 80.0}],
        }]})


def planned_route(coordinates, duration):
    return httpx.Response(200, json={"code": "Ok", "routes": [{
        "distance": 1000.0, "duration": duration,
        "geometry": {"coordinates": coordinates},
        "legs": [{"distance": 1000.0, "duration": duration,
                  "annotation": {"distance": [1000.0], "duration": [duration]}}],
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


def store_car(db_path, tank_volume=50, fuel_type="diesel", gauge_steps=16):
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO car VALUES (?, ?, ?, 5.8, 7.0, 20.0, 50.0, ?)",
                           (USER_ID, tank_volume, fuel_type, gauge_steps))


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
    await chat.press_labelled("16")
    await chat.press_labelled("Diésel")
    await chat.send_text("5,8")
    await chat.send_text("7")
    await chat.send_text("20")
    await chat.send_text("50")


# /coche


def test_a_new_car(store, osrm):
    chat = talk(osrm, enter_car)

    assert chat.texts() == [ASK_TANK, "Indicador: 16 secciones", "Combustible: Diésel", ASK_80, ASK_120, ASK_TIME, ASK_RESERVE,
                            SAVED_DIESEL]
    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0, 50.0, 16)]


def test_the_fuel_question_has_three_buttons(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("16")

    chat = talk(osrm, scenario)

    question = chat.telegram.messages[-1]
    assert question.text == ASK_FUEL
    assert [[button["text"] for button in row] for row in question.markup["inline_keyboard"]] == [
        ["Gasolina 95"], ["Gasolina 98"], ["Diésel"]]


def test_text_instead_of_a_fuel_button(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("16")
        await chat.send_text("diesel")

    assert talk(osrm, scenario).texts()[-1] == "Elige el tipo de combustible con un botón."


def test_coordinates_during_the_consumption_question(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("16")
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
                               "Depósito: 50 L\nIndicador: 16 secciones\nCombustible: Diésel\nA 80 km/h: 5,8 L/100 km\nA 120 km/h: 7 L/100 km\n"
                               "Tu tiempo: 20 €/h\nReserva: 50 km\n\n¿Quieres cambiarlo?")
    assert chat.texts()[-1] == "Tu coche no ha cambiado."
    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0, 50.0, 16)]


def test_a_user_with_a_car_changes_it(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_command("coche")
        await chat.press_labelled("Sí")
        await chat.send_text("60")
        await chat.press_labelled("24")
        await chat.press_labelled("Gasolina 95")
        await chat.send_text("6")
        await chat.send_text("8")
        await chat.send_text("15")
        await chat.send_text("70")

    talk(osrm, scenario)

    assert stored_cars(store) == [(USER_ID, 60, "gasoline_95", 6.0, 8.0, 15.0, 70.0, 24)]


def test_a_dialog_that_stops_changes_no_car(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_command("coche")
        await chat.press_labelled("Sí")
        await chat.send_text("50")
        await chat.press_labelled("16")
        await chat.press_labelled("Gasolina 98")
        await chat.send_command("reiniciar")

    talk(osrm, scenario)

    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0, 50.0, 16)]


def test_coche_twice_starts_again(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("24")
        await chat.press_labelled("Gasolina 95")
        await chat.send_command("coche")

    assert talk(osrm, scenario).texts()[-1] == ASK_TANK


def test_an_old_button_changes_nothing(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("12", nth_from_end=1)
        await chat.send_text("6")

    chat = talk(osrm, scenario)

    assert chat.texts()[-2] == EXPIRED
    assert chat.texts()[-1] == "Elige tu indicador con un botón."
    assert any(sent.method == "editMessageReplyMarkup" for sent in chat.sent)


def test_the_gauge_question_is_a_photo(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")

    chat = talk(osrm, scenario)

    question = chat.sent[-1]
    assert question.method == "sendPhoto"
    assert question.text == "¿Cuántas secciones tiene tu indicador de combustible?"
    assert [[button["text"] for button in row] for row in question.markup["inline_keyboard"]] == [["24", "16", "12"]]


def test_a_gauge_press_changes_the_caption(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.press_labelled("24")

    chat = talk(osrm, scenario)

    [edit] = [sent for sent in chat.sent if sent.method == "editMessageCaption"]
    assert edit.text == "Indicador: 24 secciones"
    assert edit.markup is None
    assert chat.texts()[-1] == "Elige el tipo de combustible."


def test_text_instead_of_a_gauge_button(store, osrm):
    async def scenario(chat):
        await chat.send_command("coche")
        await chat.send_text("50")
        await chat.send_text("24")

    chat = talk(osrm, scenario)

    again = chat.sent[-1]
    assert again.method == "sendPhoto"
    assert again.text == "Elige tu indicador con un botón."
    assert [[button["text"] for button in row] for row in again.markup["inline_keyboard"]] == [["24", "16", "12"]]


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


def gauges(chat):
    """Every gauge the bot sent, as it was sent: a press edits the buttons away."""
    return [sent for sent in chat.sent
            if sent.method == "sendMessage" and any(button["callback_data"].startswith("gauge:")
                                                     for row in (sent.markup or {}).get("inline_keyboard", [])
                                                     for button in row)]


async def press_gauge(chat, sixteenths, gauge=-1):
    message = gauges(chat)[gauge]
    for row in message.markup["inline_keyboard"]:
        for button in row:
            if button["callback_data"].endswith(f":{sixteenths}"):
                await chat.press(button["callback_data"], message.message_id)
                return
    raise AssertionError(f"no gauge button for {sixteenths}/16")


def route_requests(osrm):
    return sum(1 for request in osrm.requests if request.url.path.startswith("/route/"))


async def ask_fuel(chat):
    await chat.send_location(ORIGIN)
    await chat.send_location(DESTINATION)


def test_a_complete_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("1/4")

    chat = talk(osrm, scenario)

    assert chat.texts() == [ASK_DESTINATION, "Combustible: 1/4 (12,5 L)", "No necesitas repostar: llegarás con 12 L."]


def test_the_answer_lists_the_stations(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await press_gauge(chat, 1)

    chat = talk(osrm, scenario)

    answer = chat.sent[-1]
    assert answer.text.startswith("1. <a ")
    assert "\n1,689 €/L · " in answer.text
    assert answer.parameters["parse_mode"] == "HTML"
    assert answer.parameters["link_preview_options"] == {"is_disabled": True}


@pytest.mark.parametrize("gauge_steps, rows", [
    (24, [["1", ".", ".", "|", ".", ".", "3/4"], ["3/4", ".", ".", "|", ".", ".", "1/2"],
          ["1/2", ".", ".", "|", ".", ".", "1/4"], ["1/4", ".", ".", "|", ".", ".", "0"]]),
    (16, [["1", ".", "|", ",", "3/4"], ["3/4", ".", "|", ",", "1/2"], ["1/2", ".", "|", ",", "1/4"],
          ["1/4", ".", "|", ",", "0"]]),
    (12, [["1", ".", "5/6", ".", "2/3", ".", "1/2"], ["1/2", ".", "1/3", ".", "1/6", ".", "0"]]),
])
def test_the_gauge_keyboard_of_the_car(store, osrm, gauge_steps, rows):
    store_car(store, gauge_steps=gauge_steps)

    chat = talk(osrm, ask_fuel)

    [gauge] = gauges(chat)
    assert gauge.text == ASK_GAUGE
    assert [[button["text"] for button in row] for row in gauge.markup["inline_keyboard"]] == rows


def test_a_mark_between_two_labels_on_the_24_step_gauge(store, osrm):
    store_car(store, gauge_steps=24)

    async def scenario(chat):
        await ask_fuel(chat)
        await press_gauge(chat, 21)

    assert talk(osrm, scenario).texts()[1] == "Combustible: 7/8 (43,8 L)"


def test_a_full_tank_on_the_12_step_gauge(store, osrm):
    store_car(store, gauge_steps=12)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("1")

    assert talk(osrm, scenario).texts()[1] == "Combustible: 1 (50 L)"


def test_0_searches_near_the_origin(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("0")

    chat = talk(osrm, scenario)

    assert chat.texts()[1] == "Combustible: 0 (0 L)"
    assert chat.sent[-1].text.startswith("1. <a ")


@pytest.mark.parametrize("nth_from_end", [0, 1])
def test_both_3_4_buttons_mean_three_quarters(store, osrm, nth_from_end):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("3/4", nth_from_end=nth_from_end)

    assert talk(osrm, scenario).texts()[1] == "Combustible: 3/4 (37,5 L)"


@pytest.mark.parametrize("sixteenths, pressed", [(8, "Combustible: 1/2 (25 L)"),
                                                 (13, "Combustible: 13/16 (40,6 L)")])
def test_the_pressed_question(store, osrm, sixteenths, pressed):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await press_gauge(chat, sixteenths)

    chat = talk(osrm, scenario)

    assert chat.texts()[1] == pressed
    assert [sent.parameters.get("reply_markup") for sent in chat.sent if sent.method == "editMessageText"] == [None]


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
        ASK_GAUGE,
    ]


def test_a_typed_range(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.send_text("87,5")

    assert talk(osrm, scenario).texts()[-1] == "No necesitas repostar: llegarás con 86 km de autonomía."


def test_text_that_is_not_a_range(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.send_text("mucho")
        await chat.send_text("120")

    assert talk(osrm, scenario).texts()[-2:] == [
        "Elige en el indicador o escribe los kilómetros de autonomía, por ejemplo 120.",
        "No necesitas repostar: llegarás con 119 km de autonomía.",
    ]


def test_a_gauge_from_an_earlier_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("1")
        await ask_fuel(chat)
        await press_gauge(chat, 8, gauge=0)
        await press_gauge(chat, 8, gauge=-1)

    chat = talk(osrm, scenario)

    # The press on the new gauge edits that message in place, so it reads before the expiry notice.
    assert chat.texts()[-3:] == ["Combustible: 1/2 (25 L)", EXPIRED_GAUGE, "No necesitas repostar: llegarás con 24 L."]
    assert any(sent.method == "editMessageReplyMarkup" for sent in chat.sent)


def test_a_gauge_after_reiniciar(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.send_command("reiniciar")
        await press_gauge(chat, 8)

    chat = talk(osrm, scenario)

    assert chat.texts()[-1] == EXPIRED_GAUGE
    assert route_requests(osrm) == 2


def test_a_second_press_on_one_gauge(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await press_gauge(chat, 8)
        await press_gauge(chat, 4)

    chat = talk(osrm, scenario)

    assert chat.texts()[-1] == EXPIRED_GAUGE
    assert route_requests(osrm) == 3


def test_a_location_during_the_fuel_question_starts_a_new_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_location(DESTINATION)
        await chat.send_location(DESTINATION)
        await chat.send_location(ORIGIN)

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION, ASK_GAUGE, ASK_DESTINATION, ASK_GAUGE]


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
    assert stored_cars(store) == [(USER_ID, 50, "diesel", 5.8, 7.0, 20.0, 50.0, 16)]


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

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION, INFO, ASK_GAUGE]


def test_a_router_that_is_down_asks_again_with_a_new_gauge(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        osrm.planned = "down"
        await chat.press_labelled("1/2")
        osrm.planned = "ok"
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert chat.texts()[1:] == [
        "Combustible: 1/2 (25 L)",
        "No he podido calcular la ruta. Lo siento mucho 😞",
        "Combustible: 1/2 (25 L)",
        "No necesitas repostar: llegarás con 24 L.",
    ]
    assert len({gauge.markup["inline_keyboard"][0][0]["callback_data"] for gauge in gauges(chat)}) == 2


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


ASK_TOLLS = "¿Quieres usar autopistas de peaje?"


def toll_questions(chat):
    return [sent for sent in chat.sent
            if sent.method == "sendMessage" and any(button["callback_data"].startswith("tolls:")
                                                     for row in (sent.markup or {}).get("inline_keyboard", [])
                                                     for button in row)]


def search_excludes(osrm):
    """The `exclude` of each route request after the two of the destination."""
    return [request.url.params.get("exclude") for request in osrm.requests
            if request.url.path.startswith("/route/")][2:]


def tolls_save_time(osrm, toll_free_s=10_201.0):
    osrm.tolls_s = 7400.0
    osrm.toll_free = toll_free_s


def test_same_routes_ask_no_toll_question(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert chat.texts()[:2] == [ASK_DESTINATION, "Combustible: 1/2 (25 L)"]
    assert toll_questions(chat) == []
    assert search_excludes(osrm) == [None]


@pytest.mark.parametrize("toll_free_s, label", [
    (10_201.0, "Sí (-44 min)"),
    (12_224.0, "Sí (-75 min)"),
])
def test_the_toll_question(store, osrm, toll_free_s, label):
    store_car(store)
    tolls_save_time(osrm, toll_free_s)

    chat = talk(osrm, ask_fuel)

    assert chat.texts() == [ASK_DESTINATION, "¿Quieres usar autopistas de peaje?"]
    [question] = toll_questions(chat)
    assert [[button["text"] for button in row] for row in question.markup["inline_keyboard"]] == [
        [label, "No"]]


def test_no_toll_question_when_the_tolls_save_no_time(store, osrm):
    store_car(store)
    tolls_save_time(osrm, 7420.0)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert chat.texts()[:2] == [ASK_DESTINATION, "Combustible: 1/2 (25 L)"]
    assert search_excludes(osrm) == ["toll"]


def test_with_tolls(store, osrm):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("Sí (-44 min)")
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert chat.texts()[:3] == [ASK_DESTINATION, "Peajes: Sí (-44 min)", "Combustible: 1/2 (25 L)"]
    assert search_excludes(osrm) == [None]


def test_without_tolls(store, osrm):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("No")
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert chat.texts()[:3] == [ASK_DESTINATION, "Peajes: No", "Combustible: 1/2 (25 L)"]
    assert search_excludes(osrm) == ["toll"]


def test_every_detour_without_tolls(store, osrm):
    store_car(store)
    store_station(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("No")
        await chat.press_labelled("0")

    chat = talk(osrm, scenario)

    assert chat.sent[-1].text.startswith("1. <a ")
    assert search_excludes(osrm) == ["toll", "toll"]


def test_the_toll_choice_survives_a_failed_search(store, osrm):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("No")
        osrm.planned = "down"
        await chat.press_labelled("1/2")
        osrm.planned = "ok"
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert "No he podido calcular la ruta. Lo siento mucho 😞" in chat.texts()
    assert len(gauges(chat)) == 2
    assert search_excludes(osrm) == ["toll", "toll"]


@pytest.mark.parametrize("toll_free", ["down", "no_route"])
def test_a_failed_toll_free_route_asks_no_toll_question(store, osrm, toll_free):
    store_car(store)
    osrm.tolls_s = 7400.0
    osrm.toll_free = toll_free

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert chat.texts()[:2] == [ASK_DESTINATION, "Combustible: 1/2 (25 L)"]
    assert search_excludes(osrm) == [None]


def test_the_router_is_down_at_the_destination(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        osrm.planned = "down"
        await chat.send_location(DESTINATION)
        osrm.planned = "ok"
        await chat.send_location(DESTINATION)

    assert talk(osrm, scenario).texts() == [
        ASK_DESTINATION, "No he podido calcular la ruta. Lo siento mucho 😞", ASK_GAUGE]


def test_no_road_at_the_destination_forgets_the_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        osrm.planned = "no_route"
        await chat.send_location(DESTINATION)
        osrm.planned = "ok"
        await chat.send_location(ORIGIN)

    assert talk(osrm, scenario).texts() == [
        ASK_DESTINATION,
        "No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.",
        ASK_DESTINATION,
    ]


@pytest.mark.parametrize("send", [
    lambda chat: chat.send_location(ORIGIN),
    lambda chat: chat.send_text("40.4168, -3.7038"),
])
def test_a_location_during_the_toll_question_starts_a_new_journey(store, osrm, send):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await send(chat)
        await chat.send_location(DESTINATION)

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION, ASK_TOLLS, ASK_DESTINATION, ASK_TOLLS]


def test_text_during_the_toll_question_gets_the_info_text(store, osrm):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.send_text("hola")
        await chat.press_labelled("No")

    assert talk(osrm, scenario).texts() == [ASK_DESTINATION, "Peajes: No", INFO, ASK_GAUGE]


def test_a_second_press_on_one_toll_question(store, osrm):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        [question] = toll_questions(chat)
        [with_tolls, without_tolls] = question.markup["inline_keyboard"][0]
        await chat.press(without_tolls["callback_data"], question.message_id)
        await chat.press(with_tolls["callback_data"], question.message_id)
        await chat.press_labelled("1/2")

    chat = talk(osrm, scenario)

    assert EXPIRED_GAUGE in chat.texts()
    assert len(gauges(chat)) == 1
    assert search_excludes(osrm) == ["toll"]


def test_a_toll_button_after_reiniciar(store, osrm):
    store_car(store)
    tolls_save_time(osrm)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.send_command("reiniciar")
        await chat.press_labelled("No")

    chat = talk(osrm, scenario)

    assert chat.texts()[-1] == EXPIRED_GAUGE
    assert gauges(chat) == []


def nearby_questions(chat):
    return [sent for sent in chat.sent
            if sent.method == "sendMessage" and any(button["callback_data"].startswith("nearby:")
                                                     for row in (sent.markup or {}).get("inline_keyboard", [])
                                                     for button in row)]


async def press_nearby(chat, question=-1):
    message = nearby_questions(chat)[question]
    await chat.press(message.markup["inline_keyboard"][0][0]["callback_data"], message.message_id)


def test_the_destination_question_offers_the_nearby_stations(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)

    [question] = nearby_questions(talk(osrm, scenario))
    assert question.text == "Ahora envíame el destino."
    assert [[button["text"] for button in row] for row in question.markup["inline_keyboard"]] == [
        ["o mostrar gasolineras cercanas"]]


def test_a_press_lists_the_nearby_stations(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await press_nearby(chat)

    chat = talk(osrm, scenario)

    [question] = nearby_questions(chat)
    [edit] = [sent for sent in chat.sent if sent.method == "editMessageReplyMarkup"]
    assert edit.message_id == question.message_id
    assert not edit.markup
    assert chat.texts()[0] == "Ahora envíame el destino."
    answer = chat.sent[-1]
    assert answer.text.startswith("1. <a ")
    assert answer.text.split("\n")[0].endswith("· 0,0 km")
    assert answer.text.split("\n")[1] == "1,689 €/L"
    assert answer.parameters["parse_mode"] == "HTML"
    assert answer.parameters["link_preview_options"] == {"is_disabled": True}
    assert route_requests(osrm) == 0


def test_the_nearby_list_ends_the_journey(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await press_nearby(chat)
        await chat.send_location(DESTINATION)

    assert talk(osrm, scenario).texts()[-1] == "Ahora envíame el destino."


def test_a_nearby_press_after_the_destination(store, osrm):
    store_car(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await press_nearby(chat)
        await chat.press_labelled("1/4")

    chat = talk(osrm, scenario)

    assert chat.texts() == ["Ahora envíame el destino.", "Combustible: 1/4 (12,5 L)", "Esta pregunta ha caducado.",
                            "No necesitas repostar: llegarás con 12 L."]


def test_a_nearby_press_on_the_first_origin_after_a_new_origin(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await ask_fuel(chat)
        await chat.send_location(ORIGIN)
        await press_nearby(chat, question=0)
        await press_nearby(chat, question=1)

    chat = talk(osrm, scenario)

    assert chat.texts()[-2] == "Esta pregunta ha caducado."
    assert chat.sent[-1].text.startswith("1. <a ")


def test_a_nearby_press_after_reiniciar(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await chat.send_command("reiniciar")
        await press_nearby(chat)

    chat = talk(osrm, scenario)

    assert chat.texts() == ["Ahora envíame el destino.", "Envíame tu ubicación actual.", "Esta pregunta ha caducado."]


def test_a_second_press_on_one_nearby_button(store, osrm):
    store_car(store)
    store_station(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await press_nearby(chat)
        await press_nearby(chat)

    texts = talk(osrm, scenario).texts()

    assert len(texts) == 3
    assert texts[1].startswith("1. <a ")
    assert texts[2] == "Esta pregunta ha caducado."


def test_no_nearby_station(store, osrm):
    store_car(store)

    async def scenario(chat):
        await chat.send_location(ORIGIN)
        await press_nearby(chat)

    assert talk(osrm, scenario).texts()[-1] == "Ninguna gasolinera vende Diésel a menos de 50 km de tu ubicación."
