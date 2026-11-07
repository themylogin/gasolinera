# -*- coding=utf-8 -*-
from dataclasses import dataclass
import datetime
import itertools
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, filters, MessageHandler

from . import car, refuel
from .config import config
from .journey import INFO, format_answer, liters_error, parse_liters, parse_location
from .osrm import NoRoute, Router, RouterUnavailable

__all__ = ["ChatState", "Journey", "build", "main", "post_init"]

logger = logging.getLogger(__name__)

STATE_KEY = "gasolinera_chat_state"
ROUTER_KEY = "gasolinera_router"


@dataclass(frozen=True)
class Journey:
    origin: tuple[float, float]
    destination: tuple[float, float] | None = None


class ChatState:
    def __init__(self):
        self.journeys = {}
        self.car_dialogs = {}
        self._tokens = itertools.count(1)

    def new_car_token(self):
        return f"c{next(self._tokens)}"


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    state = context.bot_data[STATE_KEY]
    router = context.bot_data[ROUTER_KEY]
    user_id = message.from_user.id

    if message.location is not None:
        await handle_location(message, state, router, (message.location.longitude, message.location.latitude))
        return

    text = message.text or ""
    if user_id in state.car_dialogs:
        await send_car_reply(message, state, user_id, car.answer_text(state.car_dialogs[user_id], text))
        return

    journey = state.journeys.get(user_id)
    if journey is not None and journey.destination is not None:
        await handle_liters(message, state, router, journey, text)
        return

    location = parse_location(text)
    if location is not None:
        await handle_location(message, state, router, location)
        return

    await send_info(message)


async def handle_location(message, state, router, location):
    user_id = message.from_user.id
    try:
        distance = await router.distance_to_road(location)
    except RouterUnavailable as error:
        logger.warning("Cannot measure the distance of %r to the road network: %r", location, error)
        await message.reply_text("No he podido calcular la ruta. Lo siento mucho 😞")
        return

    if distance > 1000:
        await message.reply_text("🇪🇸 Esta ubicación no está a menos de 1 km de ninguna carretera de España.")
        return

    journey = state.journeys.get(user_id)
    if journey is not None and journey.destination is None:
        state.journeys[user_id] = Journey(origin=journey.origin, destination=location)
        await message.reply_text("¿Cuántos litros de combustible te quedan?")
        return

    if await car.load_car(user_id) is None:
        state.journeys.pop(user_id, None)
        await message.reply_text("Primero dime cómo es tu coche con /coche.")
        return

    state.journeys[user_id] = Journey(origin=location)
    await message.reply_text("Ahora envíame el destino.")


async def handle_liters(message, state, router, journey, text):
    user_id = message.from_user.id
    parameters = await car.load_car(user_id)
    if parameters is None:
        state.journeys.pop(user_id, None)
        await message.reply_text("Primero dime cómo es tu coche con /coche.")
        return

    liters = parse_liters(text, parameters.tank_volume)
    if liters is None:
        await message.reply_text(liters_error(parameters.tank_volume))
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        answer = await refuel.search(router, journey.origin, journey.destination, parameters, liters, now)
    except NoRoute:
        state.journeys.pop(user_id, None)
        await message.reply_text("No encuentro una ruta por carretera entre el origen y el destino. "
                                 "Envíame tu ubicación actual.")
        return
    except Exception as error:
        logger.warning("Error searching stations for %r: %r", journey, error, exc_info=True)
        await message.reply_text("No he podido calcular la ruta. Lo siento mucho 😞")
        return

    state.journeys.pop(user_id, None)
    await message.reply_text(format_answer(answer, car.FUEL_LABELS[parameters.fuel_type]),
                             parse_mode=ParseMode.HTML,
                             link_preview_options=LinkPreviewOptions(is_disabled=True))


async def car_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.bot_data[STATE_KEY]
    user_id = update.message.from_user.id
    reply = car.start(state.new_car_token(), await car.load_car(user_id))
    await send_car_reply(update.message, state, user_id, reply)


async def car_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token, _, choice = query.data.removeprefix("car:").partition(":")
    state = context.bot_data[STATE_KEY]
    user_id = query.from_user.id
    reply = car.answer_button(state.car_dialogs.get(user_id), token, choice)
    if reply.pressed_text is None:
        await query.edit_message_reply_markup(reply_markup=None)
    else:
        await query.edit_message_text(reply.pressed_text)

    await send_car_reply(query.message, state, user_id, reply)


async def send_car_reply(message, state, user_id, reply):
    if reply.save is not None:
        try:
            await car.save_car(user_id, reply.save)
        except Exception as error:
            logger.warning("Error saving the car of %r: %r", user_id, error, exc_info=True)
            state.car_dialogs.pop(user_id, None)
            await message.reply_text("No he podido guardar tu coche. Lo siento mucho 😞")
            return

    if reply.dialog is None:
        state.car_dialogs.pop(user_id, None)
    else:
        state.car_dialogs[user_id] = reply.dialog

    markup = None
    if reply.buttons:
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=f"car:{reply.dialog.token}:{choice}") for label, choice in row]
            for row in reply.buttons
        ])
    await message.reply_text(reply.text, reply_markup=markup)


async def restart_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.bot_data[STATE_KEY]
    user_id = update.message.from_user.id
    state.journeys.pop(user_id, None)
    state.car_dialogs.pop(user_id, None)
    await update.message.reply_text("Envíame tu ubicación actual.")


async def info_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_info(update.message)


async def send_info(message):
    await message.reply_text(INFO, link_preview_options=LinkPreviewOptions(is_disabled=True))


async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("coche", "Configurar tu coche"),
        ("reiniciar", "Empezar de nuevo"),
        ("info", "Qué hace este bot"),
    ])


def build(token, *, request=None, get_updates_request=None, router=None):
    builder = Application.builder().token(token).post_init(post_init)
    if request is not None:
        builder = builder.request(request)
    if get_updates_request is not None:
        builder = builder.get_updates_request(get_updates_request)

    application = builder.build()
    application.bot_data[STATE_KEY] = ChatState()
    if router is None:
        router = Router(config.osrm_url)
    application.bot_data[ROUTER_KEY] = router

    application.add_handler(CommandHandler("coche", car_command_handler))
    application.add_handler(CommandHandler("reiniciar", restart_command_handler))
    application.add_handler(CommandHandler(["info", "start"], info_command_handler))
    application.add_handler(MessageHandler(filters.COMMAND, info_command_handler))
    application.add_handler(MessageHandler((filters.TEXT | filters.LOCATION) & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(car_button_handler, pattern=r"^car:"))

    return application


def main():
    if not config.telegram_bot_token:
        raise SystemExit("gasolinera: cannot start: TELEGRAM_BOT_TOKEN is not set")

    build(config.telegram_bot_token).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(level=config.log_level, format="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s")
    # httpx logs every long poll at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    main()
