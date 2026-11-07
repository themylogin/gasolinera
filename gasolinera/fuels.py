# -*- coding=utf-8 -*-
from decimal import Decimal, InvalidOperation

__all__ = ["FUEL_GROUPS", "group_price"]

FUEL_GROUPS = {
    "gasoline_95": (
        "Precio Gasolina 95 E5",
        "Precio Gasolina 95 E10",
        "Precio Gasolina 95 E5 Premium",
        "Precio Gasolina Renovable",
    ),
    "gasoline_98": (
        "Precio Gasolina 98 E5",
        "Precio Gasolina 98 E10",
    ),
    "diesel": (
        "Precio Gasoleo A",
        "Precio Gasoleo Premium",
        "Precio Diésel Renovable",
    ),
}


def group_price(prices, group):
    sold = []
    for field in FUEL_GROUPS[group]:
        if (price := _price(prices.get(field))) is not None:
            sold.append((field, price))

    if not sold:
        return None

    return min(sold, key=lambda field_price: field_price[1])


def _price(text):
    if text is None:
        return None

    try:
        price = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None

    # Decimal accepts "NaN" and "Infinity".
    if not price.is_finite():
        return None

    return price
