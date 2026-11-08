# -*- coding=utf-8 -*-
import dataclasses
import re

from sqlalchemy.dialects.sqlite import insert

from . import db
from .journey import GAUGES
from .models import Car

__all__ = ["FUEL_LABELS", "CarDialog", "CarParameters", "CarReply", "answer_button", "answer_text", "describe",
           "load_car", "number_text", "parse_consumption", "parse_eur_per_hour", "parse_reserve_km", "parse_tank_volume",
           "save_car", "start"]

FUEL_LABELS = {
    "gasoline_95": "Gasolina 95",
    "gasoline_98": "Gasolina 98",
    "diesel": "Diésel",
}


@dataclasses.dataclass(frozen=True)
class CarParameters:
    tank_volume: int
    fuel_type: str
    consume_80: float
    consume_120: float
    eur_per_hour: float
    reserve_km: float
    gauge_steps: int


@dataclasses.dataclass(frozen=True)
class CarDialog:
    token: str
    step: str
    tank_volume: int | None = None
    gauge_steps: int | None = None
    fuel_type: str | None = None
    consume_80: float | None = None
    consume_120: float | None = None
    eur_per_hour: float | None = None


@dataclasses.dataclass(frozen=True)
class CarReply:
    text: str
    dialog: CarDialog | None
    buttons: tuple = ()
    save: CarParameters | None = None
    pressed_text: str | None = None
    # The reply is the gauge picture, with the text as its caption.
    photo: bool = False


def start(token, parameters):
    if parameters is None:
        return _ask_tank_volume(CarDialog(token=token, step="tank_volume"))

    return _ask_whether_to_change(f"Tu coche:\n\n{describe(parameters)}\n\n¿Quieres cambiarlo?",
                                  CarDialog(token=token, step="confirm"))


def answer_text(dialog, text):
    if dialog.step == "confirm":
        return _ask_whether_to_change("¿Quieres cambiarlo?", dialog)

    if dialog.step == "tank_volume":
        volume = parse_tank_volume(text)
        if volume is None:
            return CarReply(text="El volumen del depósito debe ser un número entero de 30 o más. Escríbelo de nuevo.",
                            dialog=dialog)
        return _ask_gauge("¿Cuántas secciones tiene tu indicador de combustible?",
                          dataclasses.replace(dialog, step="gauge", tank_volume=volume))

    if dialog.step == "gauge":
        return _ask_gauge("Elige tu indicador con un botón.", dialog)

    if dialog.step == "fuel_type":
        return _ask_fuel_type("Elige el tipo de combustible con un botón.", dialog)

    if dialog.step == "eur_per_hour":
        eur_per_hour = parse_eur_per_hour(text)
        if eur_per_hour is None:
            return CarReply(text="El valor de tu tiempo debe ser un número de 0 a 1000, por ejemplo 20. "
                                 "Escríbelo de nuevo.",
                            dialog=dialog)
        return CarReply(text="¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50.",
                        dialog=dataclasses.replace(dialog, step="reserve_km", eur_per_hour=eur_per_hour))

    if dialog.step == "reserve_km":
        reserve_km = parse_reserve_km(text)
        if reserve_km is None:
            return CarReply(text="La reserva debe ser un número de 0 a 500 km, por ejemplo 50. Escríbelo de nuevo.",
                            dialog=dialog)
        parameters = CarParameters(tank_volume=dialog.tank_volume, fuel_type=dialog.fuel_type,
                                   consume_80=dialog.consume_80, consume_120=dialog.consume_120,
                                   eur_per_hour=dialog.eur_per_hour, reserve_km=reserve_km,
                                   gauge_steps=dialog.gauge_steps)
        return CarReply(text=f"Tu coche está guardado.\n\n{describe(parameters)}", dialog=None, save=parameters)

    consumption = parse_consumption(text)
    if consumption is None:
        return CarReply(text="El consumo debe ser un número mayor que 0 y menor que 30, por ejemplo 6,5. "
                             "Escríbelo de nuevo.",
                        dialog=dialog)

    if dialog.step == "consume_80":
        return _ask_consumption(120, dataclasses.replace(dialog, step="consume_120", consume_80=consumption))

    if consumption < dialog.consume_80:
        return CarReply(text="El consumo a 120 km/h debe ser igual o mayor que el consumo a 80 km/h, "
                             f"{number_text(dialog.consume_80)} L/100 km. Escríbelo de nuevo.",
                        dialog=dialog)

    return CarReply(text="¿Cuánto vale tu tiempo? Escríbelo en €/h, por ejemplo 20.",
                    dialog=dataclasses.replace(dialog, step="eur_per_hour", consume_120=consumption))


def answer_button(dialog, token, choice):
    if dialog is None or dialog.token != token:
        return _expired(dialog)

    if dialog.step == "gauge" and choice in {str(steps) for steps in GAUGES}:
        reply = _ask_fuel_type("Elige el tipo de combustible.",
                               dataclasses.replace(dialog, step="fuel_type", gauge_steps=int(choice)))
        return dataclasses.replace(reply, pressed_text=f"Indicador: {choice} secciones")

    if dialog.step == "fuel_type" and choice in FUEL_LABELS:
        reply = _ask_consumption(80, dataclasses.replace(dialog, step="consume_80", fuel_type=choice))
        return dataclasses.replace(reply, pressed_text=f"Combustible: {FUEL_LABELS[choice]}")

    if dialog.step == "confirm" and choice == "yes":
        return _ask_tank_volume(dataclasses.replace(dialog, step="tank_volume"))

    if dialog.step == "confirm" and choice == "no":
        return CarReply(text="Tu coche no ha cambiado.", dialog=None)

    return _expired(dialog)


def _expired(dialog):
    return CarReply(text="Esta pregunta ha caducado. Envía /coche para empezar de nuevo.", dialog=dialog)


def _ask_whether_to_change(text, dialog):
    return CarReply(text=text, dialog=dialog, buttons=((("Sí", "yes"), ("No", "no")),))


def _ask_tank_volume(dialog):
    return CarReply(text="Escribe el volumen del depósito en litros.", dialog=dialog)


def _ask_gauge(text, dialog):
    return CarReply(text=text, dialog=dialog, buttons=(tuple((str(steps), str(steps)) for steps in GAUGES),),
                    photo=True)


def _ask_fuel_type(text, dialog):
    return CarReply(text=text, dialog=dialog, buttons=tuple(((label, key),) for key, label in FUEL_LABELS.items()))


def _ask_consumption(speed, dialog):
    return CarReply(text=f"Escribe el consumo a {speed} km/h en litros por 100 km.", dialog=dialog)


def parse_tank_volume(text):
    # Eighteen digits always fit the 64-bit SQLite integer.
    match = re.fullmatch(r"\s*(\d{1,18})\s*", text)
    if match is None:
        return None

    volume = int(match.group(1))
    if volume < 30:
        return None

    return volume


def _decimal(text):
    match = re.fullmatch(r"\s*(\d+)(?:[.,](\d+))?\s*", text)
    if match is None:
        return None

    return float(".".join(filter(None, match.groups())))


def parse_consumption(text):
    consumption = _decimal(text)
    if consumption is None or not 0 < consumption < 30:
        return None

    return consumption


def parse_eur_per_hour(text):
    eur_per_hour = _decimal(text)
    if eur_per_hour is None or not 0 <= eur_per_hour <= 1000:
        return None

    return eur_per_hour


def parse_reserve_km(text):
    reserve_km = _decimal(text)
    if reserve_km is None or not 0 <= reserve_km <= 500:
        return None

    return reserve_km


def describe(parameters):
    return "\n".join([
        f"Depósito: {parameters.tank_volume} L",
        f"Indicador: {parameters.gauge_steps} secciones",
        f"Combustible: {FUEL_LABELS[parameters.fuel_type]}",
        f"A 80 km/h: {number_text(parameters.consume_80)} L/100 km",
        f"A 120 km/h: {number_text(parameters.consume_120)} L/100 km",
        f"Tu tiempo: {number_text(parameters.eur_per_hour)} €/h",
        f"Reserva: {number_text(parameters.reserve_km)} km",
    ])


def number_text(value):
    # `:g` shows 29.99999 as 30, which is outside the limits.
    return f"{value:.6f}".rstrip("0").rstrip(".").replace(".", ",")


async def load_car(telegram_user_id):
    async with db.Session() as session:
        row = await session.get(Car, telegram_user_id)

    if row is None or row.fuel_type not in FUEL_LABELS or row.gauge_steps not in GAUGES:
        return None

    return CarParameters(tank_volume=row.tank_volume, fuel_type=row.fuel_type, consume_80=row.consume_80,
                         consume_120=row.consume_120, eur_per_hour=row.eur_per_hour, reserve_km=row.reserve_km,
                         gauge_steps=row.gauge_steps)


async def save_car(telegram_user_id, parameters):
    values = dataclasses.asdict(parameters)
    async with db.Session() as session:
        await session.execute(
            insert(Car)
            .values(telegram_user_id=telegram_user_id, **values)
            .on_conflict_do_update(index_elements=[Car.telegram_user_id], set_=values))
        await session.commit()
