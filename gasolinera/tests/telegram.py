# -*- coding=utf-8 -*-
"""A Telegram that answers from written responses and keeps what it was told.

Copied from `french_tolls/french_tolls/integration/telegram_transport.py` and
`chat.py`. The seam is `telegram.request.BaseRequest`, the one object between
the messaging library and a socket, so `Message`, `CallbackQuery` and every
markup are the library's own.
"""
import itertools
import json

from telegram import Update
from telegram.request import BaseRequest

__all__ = ["CHAT_ID", "USER_ID", "Chat", "Sent", "Telegram"]

TOKEN = "424242:this-token-authenticates-nothing"
USER_ID = 777001
CHAT_ID = 777001

# What the bot calls. A test that reaches anything else should fail rather
# than be quietly answered.
ANSWERED = (
    "getMe",
    "setMyCommands",
    "sendMessage",
    "editMessageText",
    "editMessageReplyMarkup",
    "answerCallbackQuery",
)


class Sent:
    def __init__(self, method, parameters, message_id):
        self.method = method
        self.parameters = parameters
        self.message_id = message_id

    @property
    def text(self):
        return self.parameters.get("text") or ""

    @property
    def markup(self):
        return self.parameters.get("reply_markup")

    def __repr__(self):
        return f"Sent({self.method}, {self.text[:60]!r})"


class Telegram(BaseRequest):
    def __init__(self):
        self.sent = []
        self._message_id = 0

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    @property
    def messages(self):
        """One entry per message, with its final text: an edit replaces what was sent."""
        order, final = [], {}
        for sent in self.sent:
            if sent.method not in ("sendMessage", "editMessageText"):
                continue
            if sent.message_id not in final:
                order.append(sent.message_id)
            final[sent.message_id] = sent
        return [final[message_id] for message_id in order]

    async def do_request(self, url, method, request_data=None, **_timeouts):
        endpoint = url.rsplit("/", 1)[-1]
        parameters = dict(request_data.parameters) if request_data else {}
        if endpoint not in ANSWERED:
            raise AssertionError(f"the bot called {endpoint}, which this transport does not answer")

        self._message_id += 1
        message_id = parameters.get("message_id") or self._message_id
        self.sent.append(Sent(endpoint, parameters, message_id))
        return 200, json.dumps({"ok": True, "result": self._result(endpoint, parameters, message_id)}).encode()

    def _result(self, endpoint, parameters, message_id):
        if endpoint == "getMe":
            return {"id": 424242, "is_bot": True, "first_name": "Gasolinera", "username": "gasolinera_test_bot",
                    "can_join_groups": False, "can_read_all_group_messages": False,
                    "supports_inline_queries": False}

        if endpoint in ("setMyCommands", "answerCallbackQuery"):
            return True

        result = {
            "message_id": message_id,
            "date": 0,
            "chat": {"id": parameters.get("chat_id", CHAT_ID), "type": "private"},
            "from": {"id": 424242, "is_bot": True, "first_name": "Gasolinera"},
            "text": parameters.get("text", ""),
        }
        if parameters.get("reply_markup"):
            result["reply_markup"] = parameters["reply_markup"]
        return result


class Chat:
    """One user, one application, and everything it was sent."""

    def __init__(self, build, **build_options):
        self.telegram = Telegram()
        self.application = build(TOKEN, request=self.telegram, get_updates_request=self.telegram, **build_options)
        self._updates = itertools.count(1)

    async def __aenter__(self):
        await self.application.initialize()
        return self

    async def __aexit__(self, *_exc):
        await self.application.shutdown()
        return False

    async def send_location(self, location):
        longitude, latitude = location
        await self._message({"location": {"longitude": longitude, "latitude": latitude}})

    async def send_text(self, text):
        await self._message({"text": text})

    async def send_command(self, command):
        await self._message({
            "text": f"/{command}",
            "entities": [{"type": "bot_command", "offset": 0, "length": len(command) + 1}],
        })

    async def press(self, data, message_id=None):
        if message_id is None:
            message_id = next(self._updates)
        await self._feed({
            "callback_query": {
                "id": str(next(self._updates)),
                "from": {"id": USER_ID, "is_bot": False, "first_name": "Conductor"},
                "chat_instance": "1",
                "data": data,
                "message": {
                    "message_id": message_id,
                    "date": 0,
                    "chat": {"id": CHAT_ID, "type": "private"},
                    "from": {"id": 424242, "is_bot": True, "first_name": "Gasolinera"},
                    "text": "the message the button was on",
                },
            },
        })

    async def press_labelled(self, label, nth_from_end=0):
        """Press the button with this label on a message, the last one by default."""
        offers = []
        for message in self.telegram.messages:
            for row in (message.markup or {}).get("inline_keyboard", []):
                for button in row:
                    if button["text"] == label:
                        offers.append((button["callback_data"], message.message_id))
        if len(offers) <= nth_from_end:
            raise AssertionError(f"no message offers a button labelled {label!r}")
        data, message_id = offers[-1 - nth_from_end]
        await self.press(data, message_id)

    async def _message(self, body):
        await self._feed({
            "message": {
                "message_id": next(self._updates),
                "date": 0,
                "chat": {"id": CHAT_ID, "type": "private"},
                "from": {"id": USER_ID, "is_bot": False, "first_name": "Conductor"},
                **body,
            },
        })

    async def _feed(self, payload):
        update = Update.de_json({"update_id": next(self._updates), **payload}, self.application.bot)
        await self.application.process_update(update)

    @property
    def sent(self):
        return self.telegram.sent

    def texts(self):
        return [message.text for message in self.telegram.messages]
