# -*- coding=utf-8 -*-
import datetime

import pytest

from ..opening_hours import OpeningState, parse, state_at

# 2026-11-09 is a Monday.
MONDAY = datetime.date(2026, 11, 9)


def at(weekday, hour, minute):
    return datetime.datetime.combine(MONDAY + datetime.timedelta(days=weekday), datetime.time(hour, minute))


def kind(text, weekday, hour, minute):
    return state_at(text, at(weekday, hour, minute)).kind


def test_two_parts():
    text = "L-V: 06:00-22:00; S-D: 07:00-22:00"

    assert kind(text, 4, 6, 30) == "open"
    assert kind(text, 5, 6, 30) == "closed"
    assert kind(text, 6, 7, 30) == "open"


def test_two_ranges_in_one_day():
    text = "L-V: 09:00-14:00 y 15:00-18:00; S: 9:00-13:30"

    assert kind(text, 2, 14, 30) == "closed"
    assert kind(text, 5, 9, 15) == "open"


def test_a_space_before_the_dash():
    assert kind("L-S: 8:00 -21:00", 3, 8, 30) == "open"


def test_a_list_of_days():
    text = "L, X-V: 10:00-20:00"

    assert kind(text, 1, 12, 0) == "closed"
    assert kind(text, 2, 12, 0) == "open"


def test_a_day_that_is_not_named_is_closed():
    assert kind("L-S: 06:00-22:00", 6, 12, 0) == "closed"


def test_open_until_midnight():
    assert kind("L-D: 06:00-00:00", 2, 23, 30) == "open"


def test_open_after_midnight():
    assert kind("V: 06:00-02:00", 5, 1, 0) == "open"


def test_the_same_start_and_end_is_the_whole_day():
    text = "S: 00:00-00:00"

    assert kind(text, 5, 0, 0) == "open"
    assert kind(text, 5, 23, 30) == "open"
    assert kind(text, 4, 23, 59) == "closed"


def test_open_all_week():
    text = "L-D: 00:00-23:59"

    assert parse(text).intervals == ((0, 10080),)
    assert kind(text, 6, 23, 55) == "open"


def test_24h_on_every_day_is_never_closing_soon():
    assert kind("L-D: 24H", 6, 23, 55) == "open"


def test_closing_soon_across_the_end_of_the_week():
    text = "D: 20:00-23:59; L: 00:00-00:10; M: 10:00-12:00"

    state = state_at(text, at(6, 23, 55))

    assert state == OpeningState("closing_soon", at(7, 0, 10))


def test_open_from_sunday_night_into_monday():
    assert kind("D: 20:00-02:00; M: 10:00-12:00", 0, 1, 0) == "open"


def test_19_minutes_before_closing():
    assert state_at("L-D: 06:00-22:00", at(0, 21, 41)) == OpeningState("closing_soon", at(0, 22, 0))


def test_20_minutes_before_closing():
    assert kind("L-D: 06:00-22:00", 0, 21, 40) == "open"


def test_at_the_closing_time():
    assert kind("L-D: 06:00-22:00", 0, 22, 0) == "closed"


def test_before_opening():
    assert kind("L-D: 06:00-22:00", 0, 5, 59) == "closed"


@pytest.mark.parametrize("text", ["Consultar", "", "   ", "L-D: 06:00-25:00", "L-D: 06:60-22:00",
                                  "D-L: 06:00-22:00", "L-D 06:00-22:00", "L-D: 06:00"])
def test_a_schedule_that_cannot_be_read_is_unknown(text):
    assert parse(text) is None
    assert kind(text, 0, 12, 0) == "unknown"


@pytest.mark.parametrize("weekday", range(7))
def test_monday_only_is_unknown_on_every_day(weekday):
    assert kind("L: 24H", weekday, 12, 0) == "unknown"


def test_monday_and_sunday_is_read():
    assert kind("L: 06:00-22:00; D: 06:00-22:00", 1, 12, 0) == "closed"
