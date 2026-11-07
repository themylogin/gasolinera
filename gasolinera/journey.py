# -*- coding=utf-8 -*-
import html
import math
import re

from .refuel import NoStop, station_link

__all__ = ["INFO", "format_answer", "liters_error", "parse_liters", "parse_location"]

INFO = """Este bot busca dónde repostar más barato en tu ruta por España.

1. Configura tu coche con /coche.
2. Envíame tu ubicación actual.
3. Envíame el destino.
4. Dime cuántos litros te quedan.

Te mostraré las 10 paradas más baratas, contando el combustible y el tiempo del desvío, y te avisaré si una gasolinera estará cerrada o a punto de cerrar cuando llegues.

/coche: configurar tu coche
/reiniciar: empezar de nuevo
/info: esta información

Puedes decirme gracias aquí: https://buymeacoffee.com/themylogin o https://paypal.me/themyloginspain"""

# `lat, lon` as a user types it, or pastes it out of Google Maps.
NUMBER = r"(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.])"
COORDINATES = re.compile(rf"{NUMBER}\s*,\s*{NUMBER}")


def parse_location(text):
    """`(longitude, latitude)` from text, or None."""
    match = COORDINATES.search(text)
    if match is None:
        return None

    latitude, longitude = float(match.group(1)), float(match.group(2))
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None

    return longitude, latitude


def parse_liters(text, tank_volume):
    match = re.fullmatch(r"\s*(\d+)(?:[.,](\d+))?\s*", text)
    if match is None:
        return None

    liters = float(".".join(filter(None, match.groups())))
    if liters > tank_volume:
        return None

    return liters


def liters_error(tank_volume):
    return f"Los litros deben ser un número de 0 a {tank_volume}, por ejemplo 12,5. Escríbelo de nuevo."


def format_answer(answer, fuel_label):
    if isinstance(answer, NoStop):
        return f"No necesitas repostar: llegarás con {math.floor(answer.fuel_left)} L."

    if not answer.stations:
        return f"Ninguna gasolinera vende {fuel_label} a menos de 50 km del punto donde el depósito llega a 5 L."

    return "\n\n".join("\n".join(_station_lines(number, listed))
                       for number, listed in enumerate(answer.stations, start=1))


def _station_lines(number, listed):
    station = listed.station
    link = html.escape(station_link(station.latitude, station.longitude))
    name = html.escape(station.name.strip() or "Gasolinera sin nombre")
    price = f"{listed.price:.3f}".replace(".", ",")
    lines = [
        f'{number}. <a href="{link}">{name}</a> · {round(listed.distance_m / 1000)} km',
        f"{price} €/L · {_minutes(listed.detour_s)}",
    ]

    alert = _alert(listed)
    if alert is not None:
        lines.append(alert)
    return lines


def _minutes(seconds):
    minutes = round(seconds / 60)
    if minutes >= 0:
        return f"+{minutes} min"
    return f"{minutes} min"


def _alert(listed):
    state = listed.state
    if state.kind == "closed":
        return f"⚠️ <b>Cerrada</b> a las {listed.arrival.strftime('%H:%M')}"
    if state.kind == "closing_soon":
        return f"⚠️ <b>Cierra pronto</b> a las {state.closes_at.strftime('%H:%M')}"
    if state.kind == "unknown":
        return "⚠️ <b>Horario desconocido</b>"
    return None
