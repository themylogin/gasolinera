# Design

## Context

Today the code works like this:
- **`journey.GAUGE`** is one fixed layout of `(label, sixteenths)` with no `0`. `journey.gauge_mark(sixteenths)` names a press.
- **`bot.ask_fuel`** builds the keyboard from `GAUGE` with `gauge:<token>:<sixteenths>`, and `gauge_button_handler` divides by 16.
- **The `/coche` dialog** in `car.py` is pure. `CarReply` carries text, buttons, and `pressed_text`. `bot.send_car_reply` sends text, and `car_button_handler` edits the pressed message with `edit_message_text`.
- **The fake Telegram transport** in `gasolinera/tests/telegram.py` answers a fixed list of Bot API methods and fails on any other.

The images in `gauge/` have different sizes and formats:

| File | Size | Gauge | Label |
| --- | --- | --- | --- |
| `12.png` | 178 × 178 | 12 sections, marks 0, ¼, ½, ¾, 1 | `24` |
| `8.jpg` | 1900 × 1900 | 8 sections, marks 0, ½, 1 | `16` |
| `6.webp` | 611 × 611 | 6 sections, E to F | `12` |

Each label is twice the section count, because the keyboard has a button on each mark and halfway between two marks. The user chose to show the step counts.

## Goals / Non-Goals

**Goals:**

- One data table for each gauge, used both to draw the keyboard and to read a press.
- No image work in the bot process.

**Non-Goals:**

- Telegram file-id caching for the picture. A `/coche` dialog uploads about 100 KB once.
- A custom gauge.

## Decisions

### Gauges as data

`journey.GAUGES` maps the steps to the rows:

```python
GAUGES = {
    24: ((("1", 24), (".", 23), (".", 22), ("|", 21), (".", 20), (".", 19), ("3/4", 18)),
         (("3/4", 18), (".", 17), (".", 16), ("|", 15), (".", 14), (".", 13), ("1/2", 12)),
         (("1/2", 12), (".", 11), (".", 10), ("|", 9), (".", 8), (".", 7), ("1/4", 6)),
         (("1/4", 6), (".", 5), (".", 4), ("|", 3), (".", 2), (".", 1), ("0", 0))),
    16: ((("1", 16), (".", 15), ("|", 14), (",", 13), ("3/4", 12)),
         ...),
    12: ((("1", 12), (".", 11), ("5/6", 10), (".", 9), ("2/3", 8), (".", 7), ("1/2", 6)),
         (("1/2", 6), (".", 5), ("1/3", 4), (".", 3), ("1/6", 2), (".", 1), ("0", 0))),
}
```

`gauge_mark(step, steps)` returns the first label for that step that is not `.`, `,`, or `|`. Otherwise it returns `str(Fraction(step, steps))`, so 21 of 24 is `7/8`. `GAUGE` and the sixteenths names go away.

The callback stays `gauge:<token>:<step>`. `gauge_button_handler` accepts a step only if the car's gauge has it, and computes `tank_volume * step / gauge_steps`.

`0` gives 0 L. `refuel.fuel_walk` already returns the origin for 5 L or less, so the search does not change.

### The car

- `Car.gauge_steps`: Integer, not null, `server_default="16"`. A new revision adds it. Stored cars get 16, which is the closest match to today's 1/16 keyboard.
- `CarParameters.gauge_steps`, the dialog step `gauge` after `tank_volume`, and `describe` with `Indicador: <steps> secciones` as its second line.
- `load_car` returns `None` when `gauge_steps` is not a key of `GAUGES`, the same as for an unknown fuel group.

### A photo in the car dialog

`CarReply` gets `photo: bool = False`. With `photo`, `bot.send_car_reply` calls `reply_photo(photo=<asset bytes>, caption=reply.text, reply_markup=...)` instead of `reply_text`. The asset path is `Path(__file__).parent / "assets" / "gauges.png"`.

`car_button_handler` edits a pressed photo with `edit_message_caption`, and a pressed text with `edit_message_text`. It knows the kind from `query.message.photo`.

The gauge buttons carry `car:<token>:24`, `car:<token>:16`, and `car:<token>:12`. `answer_button` reads them only in the step `gauge`, so they cannot collide with the fuel keys.

### The picture

`gauge/render.py` uses Pillow:

1. It opens each source and converts it to RGB.
2. It fits each source into a 400 × 400 black tile with `ImageOps.contain`, which keeps the proportions, and centers it.
3. It writes `gasolinera/assets/gauges.png`, three tiles wide, in the order of the buttons. It draws no text, so the buttons alone name the gauges.

`make gauge-image` runs the script in `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` with `uv run --no-project --with pillow`. It runs as `$(HOST_USER)` with `UV_CACHE_DIR=/tmp/uv`. The app image gets no Pillow, and the PNG is committed.

Alternative: send three photos as an album. The user rejected this in favour of one picture.

### Tests

- **The fake transport** answers `sendPhoto` and `editMessageCaption`. A `sendPhoto` result carries `photo` and `caption`, so the library builds a photo `Message`.
- **`test_journey.py`** checks the rows of each gauge, the marks (`7/8`, `1`, `0`, `5/6`), and that every row after the first starts with the label that ends the row before it.
- **The bot flow tests** cover the gauge question and the keyboard of each gauge. They also check that a press on `0` searches at the origin.

## Risks / Trade-offs

- [Users of the 16-step keyboard see a new layout] → It has the same resolution and adds `0`. The change is visible, not silent.
- [`12.png` is 178 px and is scaled up to 400 px] → It is a little soft, but readable. A sharper source can replace it, followed by `make gauge-image`.

## Migration Plan

`make bot` runs `migrate`, which adds `gauge_steps` with 16 to every stored car. To roll back, run `alembic downgrade -1` and deploy the previous image.
