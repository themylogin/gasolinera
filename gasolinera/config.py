# -*- coding=utf-8 -*-
from dataclasses import dataclass
import os

__all__ = ["config"]


def getenv(name, default=""):
    return os.environ.get(name, "").strip() or default


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str = getenv("TELEGRAM_BOT_TOKEN")

    osrm_url: str = getenv("OSRM_URL", "http://osrm:5000").rstrip("/")

    # OSRM's travel time is multiplied by this. french_tolls measured 0.9333
    # against Google on French roads.
    time_multiplier: float = float(getenv("TIME_MULTIPLIER", "0.933"))

    log_level: str = getenv("LOG_LEVEL", "INFO")


config = Config()
