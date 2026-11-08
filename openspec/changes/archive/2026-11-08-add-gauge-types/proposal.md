# Proposal

## Why

Cars have different fuel gauges. The bot shows one gauge with 16 steps and no `0`, so a driver whose gauge has other marks must translate. Three common gauges cover most cars: one with 12 sections, one with 8, and one with 6. A keyboard with a button on each mark and halfway between two marks lets the driver press what they see.

## What Changes

- `/coche` asks a new second question, after the tank volume. It sends one picture with the three gauges of `gauge/` at one size, with the caption `¿Cuántas secciones tiene tu indicador de combustible?` and the buttons `24`, `16`, `12`.
- The car stores the gauge as its number of steps: 24, 16, or 12. Cars stored before get 16.
- The fuel question shows the keyboard of the gauge of the car:
  - **24 steps:** `[1][.][.][|][.][.][3/4]`, `[3/4][.][.][|][.][.][1/2]`, `[1/2][.][.][|][.][.][1/4]`, `[1/4][.][.][|][.][.][0]`
  - **16 steps:** `[1][.][|][,][3/4]`, `[3/4][.][|][,][1/2]`, `[1/2][.][|][,][1/4]`, `[1/4][.][|][,][0]`
  - **12 steps:** `[1][.][5/6][.][2/3][.][1/2]`, `[1/2][.][1/3][.][1/6][.][0]`
- A press gives the tank volume × step / steps. `0` gives 0 L, so the search point is the origin, as for any tank with 5 L or less.
- `make gauge-image` renders `gasolinera/assets/gauges.png` from the three source images, in a container, so that every gauge has the same size.
- **BREAKING** for the existing 16-step keyboard: it changes from `[1/1][.][.][.][3/4]…` without `0` to the new 16-step layout with `0`.

Out of scope:

- A gauge type other than the three.
- A special search for `0`. The existing search at the origin applies.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `car-parameters`: the gauge question, its illustration, the stored gauge, and the shown format.
- `journey-dialog`: the three keyboards, the press, and the `0` mark.
- `project-tooling`: the command that renders the gauge illustration.

## Impact

- Code: `gasolinera/car.py`, `gasolinera/journey.py`, `gasolinera/bot.py`, `gasolinera/models.py`, and a new script `gauge/render.py`.
- New committed asset: `gasolinera/assets/gauges.png`. The image already copies `gasolinera/`.
- A new Alembic revision adds `car.gauge_steps` with the server default 16.
- New Make target: `gauge-image`. It runs Pillow in a throwaway container, so the app image gets no new dependency.
