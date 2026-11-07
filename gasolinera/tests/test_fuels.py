# -*- coding=utf-8 -*-
from decimal import Decimal

from ..fuels import FUEL_GROUPS, group_price


def test_three_groups_in_order():
    assert list(FUEL_GROUPS) == ["gasoline_95", "gasoline_98", "diesel"]


def test_gasoline_95_fields():
    assert FUEL_GROUPS["gasoline_95"] == (
        "Precio Gasolina 95 E5",
        "Precio Gasolina 95 E10",
        "Precio Gasolina 95 E5 Premium",
        "Precio Gasolina Renovable",
    )


def test_gasoline_98_fields():
    assert FUEL_GROUPS["gasoline_98"] == ("Precio Gasolina 98 E5", "Precio Gasolina 98 E10")


def test_diesel_fields():
    assert FUEL_GROUPS["diesel"] == ("Precio Gasoleo A", "Precio Gasoleo Premium", "Precio Diésel Renovable")


def test_no_field_in_two_groups():
    fields = [field for group in FUEL_GROUPS.values() for field in group]

    assert len(fields) == len(set(fields))


def test_renewable_gasoline_counts_as_95():
    assert group_price({"Precio Gasolina Renovable": "1,849"}, "gasoline_95") == (
        "Precio Gasolina Renovable", Decimal("1.849"))


def test_e10_counts_as_98():
    assert group_price({"Precio Gasolina 98 E10": "1,859"}, "gasoline_98") == (
        "Precio Gasolina 98 E10", Decimal("1.859"))


def test_renewable_diesel_counts_as_diesel():
    assert group_price({"Precio Diésel Renovable": "2,065"}, "diesel") == (
        "Precio Diésel Renovable", Decimal("2.065"))


def test_agricultural_diesel_is_not_diesel():
    assert group_price({"Precio Gasoleo B": "1,549"}, "diesel") is None


def test_e85_is_not_gasoline():
    assert group_price({"Precio Gasolina 95 E85": "2,009"}, "gasoline_95") is None


def test_cheapest_diesel_field():
    prices = {"Precio Gasoleo A": "1,799", "Precio Gasoleo Premium": "1,899"}

    assert group_price(prices, "diesel") == ("Precio Gasoleo A", Decimal("1.799"))


def test_premium_is_cheaper():
    prices = {"Precio Gasolina 95 E5": "1,699", "Precio Gasolina 95 E5 Premium": "1,659"}

    assert group_price(prices, "gasoline_95") == ("Precio Gasolina 95 E5 Premium", Decimal("1.659"))


def test_equal_prices_give_the_first_field():
    prices = {"Precio Gasolina 98 E10": "1,869", "Precio Gasolina 98 E5": "1,869"}

    assert group_price(prices, "gasoline_98") == ("Precio Gasolina 98 E5", Decimal("1.869"))


def test_no_field_of_the_group():
    assert group_price({"Precio Gasoleo A": "1,799"}, "gasoline_98") is None


def test_exact_value():
    assert group_price({"Precio Gasoleo A": "1,459"}, "diesel")[1] == Decimal("1.459")


def test_text_that_is_not_a_price():
    prices = {"Precio Gasoleo A": "n/d", "Precio Gasoleo Premium": "1,899"}

    assert group_price(prices, "diesel") == ("Precio Gasoleo Premium", Decimal("1.899"))


def test_nan_is_not_a_price():
    prices = {"Precio Gasoleo A": "NaN", "Precio Gasoleo Premium": "1,899"}

    assert group_price(prices, "diesel") == ("Precio Gasoleo Premium", Decimal("1.899"))
