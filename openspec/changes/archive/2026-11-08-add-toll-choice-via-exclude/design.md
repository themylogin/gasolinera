# Design

## Context

Today the journey works like this:

- `bot.handle_location` accepts the destination after the 1 km road check and the car check. It then calls `ask_fuel` at once. No route is requested before the gauge press.
- `bot.run_search` calls `refuel.search(router, …)`. The search requests the planned route with segments, and then one detour per candidate, all from the router it receives.
- `osrm.Router.route(points, segments=True)` returns a `Route` with `coordinates`, so two routes can be compared with no new reader.
- The graph is built with `/opt/car.lua` of `osrm-backend:26.8-debian` and the `mld` algorithm.

That `car.lua` declares `excludable = Sequence { Set {'toll'}, Set {'motorway'}, Set {'ferry'} }`. `osrm-customize` builds a metric for each class, so the running graph already accepts `exclude=toll`.

A check on the running `osrm` service on 2026-11-08 gave:

| Journey | With tolls | `exclude=toll` | Geometry |
| --- | --- | --- | --- |
| Barcelona `2.1734,41.3851` – Lleida `0.6200,41.6176` | 7,336 s, 162.5 km | 7,336 s, 162.5 km | identical, 3,267 points |
| Barcelona – Puigcerdà `1.9280,42.4317` | 7,400 s, 156.7 km | 10,201 s, 171.3 km | different |

With `TIME_MULTIPLIER` 0.933, the Puigcerdà saving is 2,801 s × 0.933 = 2,613 s, so 44 min.

## Goals / Non-Goals

**Goals:**

- One graph and one service serve both route types.
- `refuel.py` does not change.
- When `exclude=toll` fails, the bot behaves as today.

**Non-Goals:**

- Reuse of the destination route in the search. The search requests the planned route again, as today.
- `motorway` or `ferry` exclusion.

## Decisions

### exclude=toll on the existing graph, not a second graph

The bot adds `exclude=toll` to the route requests of the toll-free journey.

- No rebuild, no second service, no new setting, and no extra RAM or disk.
- The two routes come from one graph, so a shared path has the same points in both answers. The Lleida check shows this.
- Alternative: a second graph with a patched `car.lua` and a service `osrm-no-tolls`. This is the change `add-toll-route-choice`. It doubles the graph files and the RAM of routing, and it needs a Lua path workaround. Rejected for this change.

### The exclusion is an option of the Router object

`Router(base_url, transport=None, exclude=None)`. When `exclude` is set, `route` adds `exclude=<value>` to its query. `distance_to_road` does not add it.

- `refuel.search` already takes a router and calls `route` for the planned route and for each detour. A toll-free `Router` object makes every request of one search toll-free, with no change to `refuel.py`.
- Alternative: an `exclude` argument on `route`. `refuel.search` then needs a new argument and must pass it to each call. Rejected.

### The bot keeps two routers from one address

`bot.build` keeps `router` as today. It also stores `Router(router.base_url, router.transport, exclude="toll")` under a second `bot_data` key.

- Both routers use `OSRM_URL`, so no new setting is needed.
- The flow tests pass one router with a mock transport, and the toll-free router reuses that transport. So the fake OSRM sees both request types.
- The road check stays on the router without `exclude`.

### The journey state

`Journey` gets three fields:

- `toll_token: str | None`: the token of the open toll question, as `gauge_token` is for the gauge.
- `toll_minutes: int | None`: the saving. The press rewrites the question to the pressed label without a read of the keyboard from Telegram.
- `avoid_tolls: bool = False`: the router of the search.

### The destination step

A new `choose_route` runs after the car check accepts the destination:

1. Request both routes at once with `asyncio.gather(..., return_exceptions=True)` and `segments=True`.
2. The result with tolls allowed decides first:
   - `NoRoute`: send the no-road text, and forget the journey.
   - Any other error: log a warning, send the sorry text, and keep `Journey(origin=…)`.
3. Any error of the toll-free request: log a warning, then `ask_fuel` with `avoid_tolls=False`.
4. Same `coordinates`: `ask_fuel` with `avoid_tolls=False`.
5. Otherwise, `minutes = round((free.duration - tolls.duration) * config.time_multiplier / 60)`.
   - 0 or less: `ask_fuel` with `avoid_tolls=True`.
   - More than 0: send the toll question.

`NoRoute` is checked before the other errors, because `NoRoute` does not inherit from `RouterUnavailable`.

The comparison uses `coordinates`, because the user asked whether the routes "match". Alternative: compare distance and duration. Two different paths with equal numbers are unlikely, but the points state "the same route" directly. Alternative: `steps=true` and the `toll` class on each step. It does not compare two routes. Rejected.

### The toll buttons

- Callback data: `tolls:<token>:yes` and `tolls:<token>:no`. `ChatState.new_toll_token()` gives `t<n>` from the shared counter.
- Labels: `f"Sí (-{minutes} min)"` and `"No"`, as literals in `bot.py`. The pressed question becomes `Peajes: Sí (-<minutes> min)` or `Peajes: No`, as `Combustible: <mark>` does for the gauge. A bare `Sí` in the chat history does not say what it answers.
- `toll_button_handler` on `^tolls:` follows `gauge_button_handler`. A token mismatch removes the buttons and sends `Esta pregunta ha caducado.` A match clears `toll_token`, sets `avoid_tolls`, edits the question to `Peajes: ` and the pressed label, and calls `ask_fuel`.

### Messages during the toll question

`message_handler` checks the toll question before it reads a range:

- typed coordinates go to `handle_location`;
- other text goes to `send_info`.

A shared location already reaches `handle_location`. A journey with a destination makes it a new origin, so that path needs no change. An old gauge press finds `gauge_token` empty and expires, as today.

### The search takes the router of the journey

`handle_range` and `gauge_button_handler` pick the router from `journey.avoid_tolls` and pass it to `run_search`. A failed search asks the fuel question again with the same `Journey`, so the choice stays.

### Tests

The fake `Osrm` in `test_bot_flow.py` gets two fields:

- `tolls_s`: the duration of the answer with segments and without `exclude`. The default stays 40 s, so the fuel numbers of the existing tests do not change. The toll tests set 7,400 s.
- `toll_free`: the answer with `exclude=toll`.
  - `"same"` (default): the answer without `exclude`. Every existing flow test then runs with no toll question.
  - A number of seconds, for example `10_201.0`: other coordinates and that duration.
  - `"down"` and `"no_route"`.

The existing field `planned` keeps its meaning: `"down"` or `"no_route"` fails every route request with segments, with or without `exclude`. `toll_free` applies only when `planned` is `"ok"`.

Assertions on the route type read `exclude` in the recorded request parameters.

## Risks / Trade-offs

- [The destination now makes two route requests with full geometry] → One request pair per journey. The Puigcerdà answer has 5,358 points, a few hundred kB. The road check already makes one request per location.
- [A destination near a toll road snaps to another road when tolls are excluded] → The routes then differ with no real saving. The minutes rule sends no question when the saving rounds to 0.
- [A new image drops `toll` from `excludable`] → OSRM answers an error for `exclude=toll`. The bot logs a warning and behaves as today. The live check in `tasks.md` catches it after an image update.
- [The open change `add-toll-route-choice` covers the same feature] → Apply only one. The other one must be deleted or archived without a spec sync.

## Migration Plan

1. Deploy the code.
2. Run `make bot`.

The graph and the `osrm` service do not change. Rollback: revert the code and run `make bot`.
