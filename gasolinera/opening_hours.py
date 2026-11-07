# -*- coding=utf-8 -*-
from dataclasses import dataclass
import datetime
import re

__all__ = ["OpeningState", "Schedule", "parse", "state_at"]

DAYS = "LMXJVSD"
WEEK = 7 * 1440

PART = re.compile(
    r"^\s*(?P<days>[LMXJVSD](?:\s*-\s*[LMXJVSD])?(?:\s*,\s*[LMXJVSD](?:\s*-\s*[LMXJVSD])?)*)"
    r"\s*:\s*(?P<times>.+?)\s*$"
)
RANGE = re.compile(r"^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$")


@dataclass(frozen=True)
class Schedule:
    # Minutes from Monday 00:00, sorted, merged, none past the end of the week.
    intervals: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class OpeningState:
    kind: str
    closes_at: datetime.datetime | None = None


def parse(text):
    if not text.strip():
        return None

    named_days = set()
    intervals = []
    for part in text.split(";"):
        match = PART.match(part)
        if match is None:
            return None

        days = _days(match.group("days"))
        ranges = _ranges(match.group("times"))
        if days is None or ranges is None:
            return None

        named_days |= days
        for day in days:
            for start, end in ranges:
                intervals.append((day * 1440 + start, day * 1440 + end))

    # Hundreds of stations list Monday only. They do not open one day a week:
    # the source dropped the rest of the schedule.
    if named_days == {0}:
        return None

    return Schedule(intervals=_merge(intervals))


def _days(text):
    days = set()
    for item in text.split(","):
        first, _, last = (letter.strip() for letter in item.partition("-"))
        start = DAYS.index(first)
        end = start
        if last:
            end = DAYS.index(last)
        if end < start:
            return None
        days.update(range(start, end + 1))
    return days


def _ranges(text):
    if text.upper() == "24H":
        return [(0, 1440)]

    ranges = []
    for item in re.split(r"\s+y\s+", text):
        match = RANGE.match(item)
        if match is None:
            return None

        start_hour, start_minute, end_hour, end_minute = (int(group) for group in match.groups())
        if max(start_hour, end_hour) > 23 or max(start_minute, end_minute) > 59:
            return None

        start = start_hour * 60 + start_minute
        end = end_hour * 60 + end_minute
        # 23:59 is how the source writes "until midnight".
        if end == 23 * 60 + 59:
            end = 1440
        if end <= start:
            end += 1440
        ranges.append((start, end))
    return ranges


def _merge(intervals):
    unwrapped = []
    for start, end in intervals:
        if end > WEEK:
            unwrapped += [(start, WEEK), (0, end - WEEK)]
        else:
            unwrapped.append((start, end))

    merged = []
    for start, end in sorted(unwrapped):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def state_at(text, local):
    schedule = parse(text)
    if schedule is None:
        return OpeningState("unknown")

    intervals = schedule.intervals
    if intervals == ((0, WEEK),):
        return OpeningState("open")

    minute = local.weekday() * 1440 + local.hour * 60 + local.minute + local.second / 60
    for start, end in intervals:
        if start <= minute < end:
            if end == WEEK and intervals[0][0] == 0:
                end = WEEK + intervals[0][1]
            left = end - minute
            if left < 20:
                return OpeningState("closing_soon", local + datetime.timedelta(minutes=left))
            return OpeningState("open")

    return OpeningState("closed")
