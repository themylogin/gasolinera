# -*- coding=utf-8 -*-
import asyncio
from dataclasses import replace

import pytest

from .. import bot
from .telegram import Chat


def test_the_menu_names_the_three_commands():
    async def run():
        async with Chat(bot.build) as chat:
            await bot.post_init(chat.application)
            return chat

    chat = asyncio.run(run())

    [menu] = [sent for sent in chat.sent if sent.method == "setMyCommands"]
    assert [(command["command"], command["description"]) for command in menu.parameters["commands"]] == [
        ("coche", "Configurar tu coche"),
        ("reiniciar", "Empezar de nuevo"),
        ("info", "Qué hace este bot"),
    ]


def test_the_router_defaults_to_the_osrm_service():
    application = bot.build("123:abc")

    assert application.bot_data[bot.ROUTER_KEY].base_url == "http://osrm:5000"


def test_bot_refuses_to_start_without_a_token(monkeypatch):
    monkeypatch.setattr(bot, "config", replace(bot.config, telegram_bot_token=""))

    with pytest.raises(SystemExit) as exit_info:
        bot.main()

    assert exit_info.value.code == "gasolinera: cannot start: TELEGRAM_BOT_TOKEN is not set"
