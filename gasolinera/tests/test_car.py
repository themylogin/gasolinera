# -*- coding=utf-8 -*-
import asyncio
import sqlite3

import pytest

from .. import car
from ..car import CarDialog, CarParameters
from ..fuels import FUEL_GROUPS

FUEL_BUTTONS = ((("Gasolina 95", "gasoline_95"),), (("Gasolina 98", "gasoline_98"),), (("Diésel", "diesel"),))
DIESEL = CarParameters(tank_volume=50, fuel_type="diesel", consume_80=5.8, consume_120=7.0, eur_per_hour=20.0,
                       reserve_km=50.0, gauge_steps=16)


def dialog(step, **values):
    return CarDialog(token="c1", step=step, **values)


def test_every_fuel_group_has_a_label():
    assert list(car.FUEL_LABELS) == list(FUEL_GROUPS)


def test_a_user_without_a_car_is_asked_the_tank_volume():
    reply = car.start("c1", None)

    assert reply.text == "Escribe el volumen del depósito en litros."
    assert reply.dialog == dialog("tank_volume")


GAUGE_BUTTONS = ((("24", "24"), ("16", "16"), ("12", "12")),)


def test_the_tank_volume_leads_to_the_gauge_picture():
    reply = car.answer_text(dialog("tank_volume"), "50")

    assert reply.text == "¿Cuántas secciones tiene tu indicador de combustible?"
    assert reply.photo is True
    assert reply.buttons == GAUGE_BUTTONS
    assert reply.dialog == dialog("gauge", tank_volume=50)


@pytest.mark.parametrize("choice", ["24", "16", "12"])
def test_a_gauge_button_leads_to_the_fuel_buttons(choice):
    reply = car.answer_button(dialog("gauge", tank_volume=50), "c1", choice)

    assert reply.pressed_text == f"Indicador: {choice} secciones"
    assert reply.text == "Elige el tipo de combustible."
    assert reply.buttons == FUEL_BUTTONS
    assert reply.photo is False
    assert reply.dialog == dialog("fuel_type", tank_volume=50, gauge_steps=int(choice))


def test_text_instead_of_a_gauge_button():
    reply = car.answer_text(dialog("gauge", tank_volume=50), "24")

    assert reply.text == "Elige tu indicador con un botón."
    assert reply.photo is True
    assert reply.buttons == GAUGE_BUTTONS
    assert reply.dialog == dialog("gauge", tank_volume=50)


def test_a_fuel_key_is_no_gauge():
    assert car.answer_button(dialog("gauge", tank_volume=50), "c1", "diesel").text == (
        "Esta pregunta ha caducado. Envía /coche para empezar de nuevo.")


@pytest.mark.parametrize("text", ["25", "45,5", "cincuenta", "", "1234567890123456789"])
def test_a_wrong_tank_volume_is_asked_again(text):
    reply = car.answer_text(dialog("tank_volume"), text)

    assert reply.text == "El volumen del depósito debe ser un número entero de 30 o más. Escríbelo de nuevo."
    assert reply.dialog == dialog("tank_volume")


def test_a_fuel_button_leads_to_the_consumption_at_80():
    reply = car.answer_button(dialog("fuel_type", tank_volume=50, gauge_steps=16), "c1", "diesel")

    assert reply.pressed_text == "Combustible: Diésel"
    assert reply.text == "Escribe el consumo a 80 km/h en litros por 100 km."
    assert reply.dialog == dialog("consume_80", tank_volume=50, gauge_steps=16, fuel_type="diesel")


def test_text_instead_of_a_fuel_button():
    reply = car.answer_text(dialog("fuel_type", tank_volume=50, gauge_steps=16), "diesel")

    assert reply.text == "Elige el tipo de combustible con un botón."
    assert reply.buttons == FUEL_BUTTONS


def test_a_decimal_comma_consumption():
    reply = car.answer_text(dialog("consume_80", tank_volume=50, gauge_steps=16, fuel_type="diesel"), "5,8")

    assert reply.text == "Escribe el consumo a 120 km/h en litros por 100 km."
    assert reply.dialog.consume_80 == 5.8


@pytest.mark.parametrize("text", ["30", "0", "mucho", "40.42, -3.70"])
def test_a_wrong_consumption_is_asked_again(text):
    reply = car.answer_text(dialog("consume_80", tank_volume=50, gauge_steps=16, fuel_type="diesel"), text)

    assert reply.text == ("El consumo debe ser un número mayor que 0 y menor que 30, por ejemplo 6,5. "
                          "Escríbelo de nuevo.")
    assert reply.dialog.step == "consume_80"


def test_a_lower_consumption_at_120():
    reply = car.answer_text(dialog("consume_120", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=6.0), "5")

    assert reply.text == ("El consumo a 120 km/h debe ser igual o mayor que el consumo a 80 km/h, 6 L/100 km. "
                          "Escríbelo de nuevo.")
    assert reply.dialog.step == "consume_120"


def test_an_equal_consumption_at_120_asks_the_value_of_time():
    reply = car.answer_text(dialog("consume_120", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=6.0), "6")

    assert reply.text == "¿Cuánto vale tu tiempo? Escríbelo en €/h, por ejemplo 20."
    assert reply.save is None
    assert reply.dialog.step == "eur_per_hour"


def test_the_value_of_time_asks_the_reserve():
    open_dialog = dialog("eur_per_hour", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=5.8, consume_120=7.0)

    reply = car.answer_text(open_dialog, "20")

    assert reply.text == "¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50."
    assert reply.save is None
    assert reply.dialog == dialog("reserve_km", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=5.8,
                                  consume_120=7.0, eur_per_hour=20.0)


def reserve_dialog(eur_per_hour=20.0):
    return dialog("reserve_km", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=5.8, consume_120=7.0,
                  eur_per_hour=eur_per_hour)


def test_the_reserve_saves_the_car():
    reply = car.answer_text(reserve_dialog(), "50")

    assert reply.save == DIESEL
    assert reply.dialog is None
    assert reply.text == ("Tu coche está guardado.\n\n"
                          "Depósito: 50 L\nIndicador: 16 secciones\nCombustible: Diésel\nA 80 km/h: 5,8 L/100 km\nA 120 km/h: 7 L/100 km\n"
                          "Tu tiempo: 20 €/h\nReserva: 50 km")


def test_a_reserve_of_60():
    assert car.answer_text(reserve_dialog(), "60").save.reserve_km == 60


def test_time_that_costs_nothing():
    open_dialog = dialog("eur_per_hour", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=5.8, consume_120=7.0)

    reserve = car.answer_text(open_dialog, "0").dialog

    assert car.answer_text(reserve, "50").save.eur_per_hour == 0


@pytest.mark.parametrize("text", ["600", "-5", "cincuenta", ""])
def test_a_wrong_reserve_is_asked_again(text):
    reply = car.answer_text(reserve_dialog(), text)

    assert reply.text == "La reserva debe ser un número de 0 a 500 km, por ejemplo 50. Escríbelo de nuevo."
    assert reply.save is None
    assert reply.dialog == reserve_dialog()


@pytest.mark.parametrize("text", ["1500", "-5", "veinte"])
def test_a_wrong_value_of_time_is_asked_again(text):
    open_dialog = dialog("eur_per_hour", tank_volume=50, gauge_steps=16, fuel_type="diesel", consume_80=5.8, consume_120=7.0)

    reply = car.answer_text(open_dialog, text)

    assert reply.text == "El valor de tu tiempo debe ser un número de 0 a 1000, por ejemplo 20. Escríbelo de nuevo."
    assert reply.save is None


def test_a_user_with_a_car_sees_it():
    reply = car.start("c1", DIESEL)

    assert reply.text == ("Tu coche:\n\n"
                          "Depósito: 50 L\nIndicador: 16 secciones\nCombustible: Diésel\nA 80 km/h: 5,8 L/100 km\nA 120 km/h: 7 L/100 km\n"
                          "Tu tiempo: 20 €/h\nReserva: 50 km\n\n¿Quieres cambiarlo?")
    assert reply.buttons == ((("Sí", "yes"), ("No", "no")),)


def test_yes_asks_the_tank_volume():
    reply = car.answer_button(dialog("confirm"), "c1", "yes")

    assert reply.text == "Escribe el volumen del depósito en litros."


def test_no_keeps_the_car():
    reply = car.answer_button(dialog("confirm"), "c1", "no")

    assert reply.text == "Tu coche no ha cambiado."
    assert reply.dialog is None
    assert reply.save is None


def test_text_during_the_confirmation():
    reply = car.answer_text(dialog("confirm"), "quizá")

    assert reply.text == "¿Quieres cambiarlo?"
    assert reply.buttons == ((("Sí", "yes"), ("No", "no")),)


@pytest.mark.parametrize("open_dialog, token", [(None, "c1"), (CarDialog(token="c2", step="fuel_type"), "c1")])
def test_an_old_button_has_expired(open_dialog, token):
    reply = car.answer_button(open_dialog, token, "gasoline_98")

    assert reply.text == "Esta pregunta ha caducado. Envía /coche para empezar de nuevo."
    assert reply.dialog == open_dialog
    assert reply.save is None


def test_a_value_is_shown_without_trailing_zeros():
    assert car.number_text(29.99999) == "29,99999"
    assert car.number_text(6.5) == "6,5"


def test_a_saved_car_is_loaded(store):
    asyncio.run(car.save_car(777001, DIESEL))

    assert asyncio.run(car.load_car(777001)) == DIESEL


def test_a_second_save_replaces_the_first(store):
    asyncio.run(car.save_car(777001, DIESEL))
    asyncio.run(car.save_car(777001, CarParameters(60, "gasoline_95", 6.0, 8.0, 15.0, 70.0, 24)))

    with sqlite3.connect(store) as connection:
        assert connection.execute("SELECT telegram_user_id, fuel_type FROM car").fetchall() == [(777001, "gasoline_95")]


def test_no_car(store):
    assert asyncio.run(car.load_car(777001)) is None


def test_a_car_of_an_unknown_group_is_no_car(store):
    with sqlite3.connect(store) as connection:
        connection.execute("INSERT INTO car VALUES (777001, 50, 'lpg', 6, 7, 20, 50, 16)")

    assert asyncio.run(car.load_car(777001)) is None


def test_a_car_of_an_unknown_gauge_is_no_car(store):
    with sqlite3.connect(store) as connection:
        connection.execute("INSERT INTO car VALUES (777001, 50, 'diesel', 6, 7, 20, 50, 10)")

    assert asyncio.run(car.load_car(777001)) is None
