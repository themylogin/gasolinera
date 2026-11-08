# -*- coding=utf-8 -*-
from fractions import Fraction
import html
import math
import re

from .refuel import NoStop, station_link

__all__ = ["GAUGES", "INFO", "format_answer", "format_nearby", "gauge_mark", "parse_location", "parse_range"]

INFO = """Este bot busca dónde repostar más barato en tu ruta por España.

1. Configura tu coche con /coche.
2. Envíame tu ubicación actual.
3. Envíame el destino.
4. Dime cuántos litros te quedan.

Te mostraré las 10 paradas más baratas, contando el combustible y el tiempo del desvío, y te avisaré si una gasolinera estará cerrada o a punto de cerrar cuando llegues.

/coche: configurar tu coche
/reiniciar: empezar de nuevo
/info: esta información

Puedes decirme gracias aquí: https://buymeacoffee.com/themylogin o https://paypal.me/themyloginspain
Código abierto: https://github.com/themylogin/gasolinera"""

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


# The keyboards of the three gauges, by their steps. Each button is
# `(label, step)`, from full to empty. A row repeats the label that ends the
# row before it, with the same step.
GAUGES = {
    24: (
        (("1", 24), (".", 23), (".", 22), ("|", 21), (".", 20), (".", 19), ("3/4", 18)),
        (("3/4", 18), (".", 17), (".", 16), ("|", 15), (".", 14), (".", 13), ("1/2", 12)),
        (("1/2", 12), (".", 11), (".", 10), ("|", 9), (".", 8), (".", 7), ("1/4", 6)),
        (("1/4", 6), (".", 5), (".", 4), ("|", 3), (".", 2), (".", 1), ("0", 0)),
    ),
    16: (
        (("1", 16), (".", 15), ("|", 14), (",", 13), ("3/4", 12)),
        (("3/4", 12), (".", 11), ("|", 10), (",", 9), ("1/2", 8)),
        (("1/2", 8), (".", 7), ("|", 6), (",", 5), ("1/4", 4)),
        (("1/4", 4), (".", 3), ("|", 2), (",", 1), ("0", 0)),
    ),
    12: (
        (("1", 12), (".", 11), ("5/6", 10), (".", 9), ("2/3", 8), (".", 7), ("1/2", 6)),
        (("1/2", 6), (".", 5), ("1/3", 4), (".", 3), ("1/6", 2), (".", 1), ("0", 0)),
    ),
}


def gauge_mark(step, steps):
    for row in GAUGES[steps]:
        for label, value in row:
            if value == step and label not in (".", ",", "|"):
                return label
    return str(Fraction(step, steps))


def parse_range(text):
    match = re.fullmatch(r"\s*(\d+)(?:[.,](\d+))?\s*", text)
    if match is None:
        return None

    range_km = float(".".join(filter(None, match.groups())))
    if range_km > 3000:
        return None

    return range_km


def format_answer(answer, fuel_label):
    if isinstance(answer, NoStop) and answer.range_left is not None:
        return f"No necesitas repostar: llegarás con {math.floor(answer.range_left)} km de autonomía."

    if isinstance(answer, NoStop):
        return f"No necesitas repostar: llegarás con {math.floor(answer.fuel_left)} L."

    if not answer.stations:
        return f"Ninguna gasolinera vende {fuel_label} a menos de 50 km del punto donde el depósito llega a 5 L."

    return "\n\n".join("\n".join(_station_lines(number, listed))
                       for number, listed in enumerate(answer.stations, start=1))


def format_nearby(stations, fuel_label):
    if not stations:
        return f"Ninguna gasolinera vende {fuel_label} a menos de 50 km de tu ubicación."

    return "\n\n".join("\n".join(_nearby_lines(number, nearby))
                       for number, nearby in enumerate(stations, start=1))


def _nearby_lines(number, nearby):
    distance = f"{nearby.distance_km:.1f}".replace(".", ",")
    lines = [f"{_station_title(number, nearby.station)} · {distance} km", _price_text(nearby.price)]

    alert = _alert(nearby.state, nearby.local_time)
    if alert is not None:
        lines.append(alert)
    return lines


def _station_lines(number, listed):
    lines = [
        f"{_station_title(number, listed.station)} · {round(listed.distance_m / 1000)} km",
        f"{_price_text(listed.price)} · {_minutes(listed.detour_s)}",
    ]

    alert = _alert(listed.state, listed.arrival)
    if alert is not None:
        lines.append(alert)
    return lines


def _station_title(number, station):
    link = html.escape(station_link(station.latitude, station.longitude))
    name = html.escape(station.name.strip() or "Gasolinera sin nombre")
    return f'{number}. <a href="{link}">{name}</a>'


def _price_text(price):
    return f"{price:.3f} €/L".replace(".", ",")


def _minutes(seconds):
    minutes = round(seconds / 60)
    if minutes >= 0:
        return f"+{minutes} min"
    return f"{minutes} min"


def _alert(state, closed_at):
    if state.kind == "closed":
        return f"⚠️ <b>Cerrada</b> a las {closed_at.strftime('%H:%M')}"
    if state.kind == "closing_soon":
        return f"⚠️ <b>Cierra pronto</b> a las {state.closes_at.strftime('%H:%M')}"
    if state.kind == "unknown":
        return "⚠️ <b>Horario desconocido</b>"
    return None
